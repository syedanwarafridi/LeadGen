"""
GitHub discovery tool — finds active small-team startup repos.
Uses GitHub Search API (free; 5000 req/hr with token, 60 without).
"""
import os
import requests
from utils.helpers import get_logger, make_id

log = get_logger(__name__)

GH_API = "https://api.github.com"


def _get_headers() -> dict:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _repo_to_lead(repo: dict, signals: list) -> dict:
    owner = repo.get("owner", {})
    return {
        "id": make_id(),
        "company_name": repo.get("name", "Unknown").replace("-", " ").title(),
        "website": repo.get("homepage", "") or "",
        "linkedin_url": "",
        "location": "Unknown",
        "market": "Unknown",
        "team_size": 1,
        "funding": None,
        "source": "github",
        "source_url": repo.get("html_url", ""),
        "raw_signals": signals,
        "description": (repo.get("description") or "")[:300],
        "founder_name": None,
        "founder_handle": owner.get("login", ""),
    }


def search_github_startups(topics: list, pushed_after: str = "2024-01-01",
                           max_results: int = 20) -> list:
    """Search GitHub for small-team startup repos by topic."""
    headers = _get_headers()
    leads = []
    seen = set()

    for topic in topics:
        try:
            query = (
                f"topic:{topic} pushed:>{pushed_after} "
                f"stars:1..500 fork:false"
            )
            resp = requests.get(
                f"{GH_API}/search/repositories",
                params={"q": query, "sort": "updated", "per_page": max_results},
                headers=headers,
                timeout=15,
            )
            if resp.status_code == 403:
                log.warning("GitHub rate limit hit")
                break
            if resp.status_code != 200:
                continue

            data = resp.json()
            for repo in data.get("items", []):
                repo_id = repo.get("id")
                if repo_id in seen:
                    continue
                seen.add(repo_id)

                signals = ["active_product"]
                if repo.get("stargazers_count", 0) > 10:
                    signals.append("community_traction")
                if not repo.get("fork"):
                    signals.append("original_project")

                leads.append(_repo_to_lead(repo, signals))
        except Exception as e:
            log.warning(f"GitHub search error ({topic}): {e}")

    return leads


def get_repo_owner_info(username: str) -> dict:
    """Get a GitHub user's profile — name, blog, location, company."""
    try:
        resp = requests.get(
            f"{GH_API}/users/{username}",
            headers=_get_headers(),
            timeout=10,
        )
        if resp.status_code != 200:
            return {}
        u = resp.json()
        return {
            "name": u.get("name") or username,
            "blog": u.get("blog", ""),
            "location": u.get("location", ""),
            "company": u.get("company", ""),
            "email": u.get("email", ""),
            "bio": u.get("bio", ""),
            "public_repos": u.get("public_repos", 0),
        }
    except Exception:
        return {}
