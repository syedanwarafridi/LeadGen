"""
Reddit discovery tool — finds founders/solopreneurs looking for developers.
Uses PRAW (free Reddit API). Falls back to public JSON feed if no credentials.
"""
import os
import requests
from typing import Optional
from utils.helpers import get_logger, extract_urls_from_text, detect_geo_from_text, make_id

log = get_logger(__name__)

DEV_KEYWORDS = [
    "looking for developer", "need a developer", "hire developer",
    "build MVP", "technical co-founder", "CTO needed",
    "software developer needed", "need to build an app",
    "want to build", "no-code", "need an engineer",
]


def _get_praw_reddit():
    """Return a PRAW Reddit instance if credentials are configured."""
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    if not (client_id and client_secret):
        return None
    try:
        import praw
        return praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="LeadGenBot/1.0 (by /u/leadgenbot)",
        )
    except Exception as e:
        log.warning(f"PRAW init failed: {e}")
        return None


def _post_to_lead(post_data: dict, source_url: str) -> dict:
    title = post_data.get("title", "")
    body = post_data.get("selftext", "") or post_data.get("body", "")
    full_text = f"{title} {body}"

    urls = extract_urls_from_text(full_text)
    website = next((u for u in urls if "reddit.com" not in u), "")

    return {
        "id": make_id(),
        "company_name": _extract_company_name(title, post_data.get("author", "unknown")),
        "website": website,
        "linkedin_url": next((u for u in urls if "linkedin.com" in u), ""),
        "location": detect_geo_from_text(full_text),
        "market": detect_geo_from_text(full_text),
        "team_size": 1,
        "funding": None,
        "source": "reddit",
        "source_url": source_url,
        "raw_signals": _extract_signals(full_text),
        "description": f"{title[:200]}",
        "founder_name": None,
        "founder_handle": post_data.get("author", ""),
    }


def _extract_company_name(title: str, author: str) -> str:
    import re
    match = re.search(r'"([^"]{3,50})"', title)
    if match:
        return match.group(1)
    for kw in ["my startup", "my app", "my saas", "my project", "my idea", "my product"]:
        if kw in title.lower():
            return f"{author}'s project"
    return f"{author}'s venture"


def _extract_signals(text: str) -> list:
    signals = []
    text_lower = text.lower()
    if any(k in text_lower for k in ["looking for developer", "need developer", "hire developer"]):
        signals.append("looking_for_developer")
    if any(k in text_lower for k in ["mvp", "minimum viable", "prototype"]):
        signals.append("wants_mvp")
    if any(k in text_lower for k in ["funded", "raised", "investment", "investor"]):
        signals.append("has_funding")
    if any(k in text_lower for k in ["non-technical", "non tech", "no coding", "can't code"]):
        signals.append("non_tech_founder")
    if any(k in text_lower for k in ["solo", "solopreneur", "indie", "side project"]):
        signals.append("solo_founder")
    return signals


def search_reddit_praw(subreddits: list, keywords: list, limit: int = 10) -> list:
    reddit = _get_praw_reddit()
    if not reddit:
        log.info("No Reddit credentials — using public RSS fallback")
        return search_reddit_rss(subreddits, keywords, limit)

    leads = []
    seen = set()
    for sub_name in subreddits:
        for keyword in keywords:
            try:
                sub = reddit.subreddit(sub_name)
                for post in sub.search(keyword, limit=limit, time_filter="week"):
                    if post.id in seen or post.is_self is False:
                        continue
                    seen.add(post.id)
                    lead = _post_to_lead(
                        {"title": post.title, "selftext": post.selftext, "author": str(post.author)},
                        f"https://reddit.com{post.permalink}",
                    )
                    leads.append(lead)
            except Exception as e:
                log.warning(f"Reddit search error ({sub_name}/{keyword}): {e}")
    return leads


def search_reddit_rss(subreddits: list, keywords: list, limit: int = 5) -> list:
    """
    Fallback: query Reddit's public JSON search without credentials.
    Rate-limited but works for low volume.
    """
    leads = []
    seen = set()
    headers = {"User-Agent": "LeadGenBot/1.0"}

    for sub in subreddits[:3]:
        for kw in keywords[:3]:
            try:
                url = f"https://www.reddit.com/r/{sub}/search.json"
                params = {"q": kw, "restrict_sr": 1, "sort": "new", "t": "week", "limit": limit}
                resp = requests.get(url, params=params, headers=headers, timeout=10)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                for item in data.get("data", {}).get("children", []):
                    post = item.get("data", {})
                    post_id = post.get("id")
                    if post_id in seen:
                        continue
                    seen.add(post_id)
                    lead = _post_to_lead(
                        post,
                        f"https://reddit.com{post.get('permalink', '')}",
                    )
                    leads.append(lead)
            except Exception as e:
                log.debug(f"Reddit RSS fallback error: {e}")
    return leads
