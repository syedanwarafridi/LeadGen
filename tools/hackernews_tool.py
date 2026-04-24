"""
HackerNews discovery tool — uses Algolia's free HN search API.
Targets: Show HN posts (product launches), hiring posts, founders looking for devs.
"""
import requests
from datetime import datetime, timedelta
from utils.helpers import get_logger, extract_urls_from_text, detect_geo_from_text, make_id

log = get_logger(__name__)

ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"


def _hit_to_lead(hit: dict) -> dict:
    title = hit.get("title", "") or hit.get("story_title", "") or ""
    text = hit.get("story_text", "") or hit.get("comment_text", "") or ""
    full_text = f"{title} {text}"
    author = hit.get("author", "unknown")
    url = hit.get("url", "")
    object_id = hit.get("objectID", "")

    urls = extract_urls_from_text(full_text)
    website = url if url else next((u for u in urls if "news.ycombinator.com" not in u), "")

    signals = []
    lower = full_text.lower()
    if "show hn" in lower:
        signals.append("show_hn_launch")
    if any(k in lower for k in ["hiring", "developer", "engineer needed"]):
        signals.append("hiring_devs")
    if any(k in lower for k in ["launched", "built", "just shipped"]):
        signals.append("active_product")
    if any(k in lower for k in ["founder", "co-founder", "ceo", "cto"]):
        signals.append("founder_post")

    company = _extract_company_name_hn(title, author)
    return {
        "id": make_id(),
        "company_name": company,
        "website": website,
        "linkedin_url": "",
        "location": detect_geo_from_text(full_text),
        "market": detect_geo_from_text(full_text),
        "team_size": 1,
        "funding": None,
        "source": "hackernews",
        "source_url": f"https://news.ycombinator.com/item?id={object_id}",
        "raw_signals": signals,
        "description": title[:200],
        "founder_name": None,
        "founder_handle": author,
    }


def _extract_company_name_hn(title: str, author: str) -> str:
    import re
    # "Show HN: CompanyName — tagline"
    show_hn = re.match(r"Show HN:\s*(.+?)[\s\-–—|]", title, re.IGNORECASE)
    if show_hn:
        return show_hn.group(1).strip()
    # "Ask HN: Looking for CTO at CompanyName"
    return f"{author}'s project"


def search_hackernews(queries: list, days_back: int = 30, per_query: int = 10) -> list:
    """Search HN via Algolia's free API for relevant posts."""
    since_ts = int((datetime.utcnow() - timedelta(days=days_back)).timestamp())
    leads = []
    seen = set()

    for query in queries:
        try:
            params = {
                "query": query,
                "tags": "(story,comment)",
                "numericFilters": f"created_at_i>{since_ts}",
                "hitsPerPage": per_query,
            }
            resp = requests.get(ALGOLIA_URL, params=params, timeout=10)
            if resp.status_code != 200:
                continue
            data = resp.json()
            for hit in data.get("hits", []):
                oid = hit.get("objectID")
                if oid in seen:
                    continue
                seen.add(oid)
                leads.append(_hit_to_lead(hit))
        except Exception as e:
            log.warning(f"HN search error ('{query}'): {e}")

    return leads


def fetch_show_hn_posts(days_back: int = 30, limit: int = 20) -> list:
    """Fetch recent Show HN posts — these are product launches by small teams."""
    since_ts = int((datetime.utcnow() - timedelta(days=days_back)).timestamp())
    try:
        params = {
            "tags": "show_hn",
            "numericFilters": f"created_at_i>{since_ts}",
            "hitsPerPage": limit,
        }
        resp = requests.get(ALGOLIA_URL, params=params, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return [_hit_to_lead(h) for h in data.get("hits", [])]
    except Exception as e:
        log.warning(f"Show HN fetch error: {e}")
        return []
