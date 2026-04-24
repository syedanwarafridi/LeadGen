"""
Product Hunt discovery tool.
Uses PH's free GraphQL API (requires a free developer token).
Falls back to scraping the public website if no token.
"""
import os
import requests
from datetime import datetime, timedelta
from utils.helpers import get_logger, make_id

log = get_logger(__name__)

PH_GRAPHQL = "https://api.producthunt.com/v2/api/graphql"

QUERY = """
query($daysAgo: DateTime!, $first: Int!) {
  posts(first: $first, postedAfter: $daysAgo, order: NEWEST) {
    nodes {
      id
      name
      tagline
      description
      website
      votesCount
      commentsCount
      createdAt
      makers {
        id
        username
        name
        twitterUsername
        websiteUrl
      }
    }
  }
}
"""


def fetch_producthunt_api(days_back: int = 30, max_results: int = 20) -> list:
    token = os.getenv("PRODUCTHUNT_TOKEN")
    if not token:
        log.info("No PRODUCTHUNT_TOKEN — using scrape fallback")
        return fetch_producthunt_scrape(days_back, max_results)

    since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00Z")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"query": QUERY, "variables": {"daysAgo": since, "first": max_results}}

    try:
        resp = requests.post(PH_GRAPHQL, json=payload, headers=headers, timeout=15)
        data = resp.json()
        nodes = data.get("data", {}).get("posts", {}).get("nodes", [])
        return [_node_to_lead(n) for n in nodes]
    except Exception as e:
        log.warning(f"ProductHunt API error: {e}")
        return fetch_producthunt_scrape(days_back, max_results)


def fetch_producthunt_scrape(days_back: int = 30, max_results: int = 20) -> list:
    """Scrape PH public listing without API key."""
    from bs4 import BeautifulSoup
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    leads = []
    try:
        resp = requests.get("https://www.producthunt.com/", headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")

        for item in soup.select("[data-test='post-item']")[:max_results]:
            name_el = item.select_one("h3")
            tagline_el = item.select_one("p")
            link_el = item.select_one("a[href*='/posts/']")

            name = name_el.get_text(strip=True) if name_el else "Unknown"
            tagline = tagline_el.get_text(strip=True) if tagline_el else ""
            source_url = ""
            if link_el:
                href = link_el.get("href", "")
                source_url = f"https://www.producthunt.com{href}" if href.startswith("/") else href

            leads.append({
                "id": make_id(),
                "company_name": name,
                "website": "",
                "linkedin_url": "",
                "location": "Unknown",
                "market": "Unknown",
                "team_size": 1,
                "funding": None,
                "source": "producthunt",
                "source_url": source_url,
                "raw_signals": ["active_product", "show_hn_launch"],
                "description": tagline[:200],
                "founder_name": None,
                "founder_handle": None,
            })
    except Exception as e:
        log.warning(f"ProductHunt scrape error: {e}")
    return leads


def _node_to_lead(node: dict) -> dict:
    makers = node.get("makers", [])
    founder = makers[0] if makers else {}

    signals = ["active_product"]
    if node.get("votesCount", 0) > 50:
        signals.append("popular_launch")

    return {
        "id": make_id(),
        "company_name": node.get("name", "Unknown"),
        "website": node.get("website", ""),
        "linkedin_url": "",
        "location": "Unknown",
        "market": "Unknown",
        "team_size": max(1, len(makers)),
        "funding": None,
        "source": "producthunt",
        "source_url": f"https://www.producthunt.com/posts/{node.get('id', '')}",
        "raw_signals": signals,
        "description": f"{node.get('tagline', '')} — {node.get('description', '')}".strip("— ")[:300],
        "founder_name": founder.get("name"),
        "founder_handle": founder.get("username"),
    }
