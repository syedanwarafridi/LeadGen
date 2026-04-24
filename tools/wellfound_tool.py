"""
Wellfound (formerly AngelList) discovery tool.
Scrapes public startup job listings — companies hiring engineers
are a perfect ICP signal (they need a dev team but can't afford US rates).
No API key required. Public pages only.
"""
import requests
from bs4 import BeautifulSoup
from utils.helpers import get_logger, make_id, detect_geo_from_text, extract_urls_from_text

log = get_logger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Roles that signal they need a dev team
DEV_ROLES = [
    "software-engineer", "backend-engineer", "frontend-engineer",
    "full-stack-engineer", "mobile-engineer", "react", "node",
]


def _parse_job_card(card) -> dict | None:
    try:
        company_el = card.select_one("[class*='company'], [class*='startup-name'], h2, h3")
        link_el    = card.select_one("a[href*='/company/'], a[href*='/jobs/']")
        role_el    = card.select_one("[class*='role'], [class*='title'], [class*='job-title']")
        loc_el     = card.select_one("[class*='location'], [class*='loc']")

        company_name = company_el.get_text(strip=True) if company_el else ""
        if not company_name:
            return None

        href = link_el.get("href", "") if link_el else ""
        source_url = f"https://wellfound.com{href}" if href.startswith("/") else href

        role    = role_el.get_text(strip=True) if role_el else "Engineer"
        loc_txt = loc_el.get_text(strip=True)  if loc_el  else ""
        geo     = detect_geo_from_text(f"{loc_txt} {company_name}")

        return {
            "id":           make_id(),
            "company_name": company_name,
            "website":      "",
            "linkedin_url": "",
            "location":     loc_txt or "Unknown",
            "market":       geo,
            "team_size":    10,
            "funding":      None,
            "source":       "wellfound",
            "source_url":   source_url,
            "raw_signals":  ["hiring_devs", "active_startup"],
            "description":  f"Hiring: {role}" ,
            "founder_name": None,
            "founder_handle": None,
        }
    except Exception:
        return None


def scrape_wellfound_jobs(max_results: int = 30) -> list:
    """Scrape Wellfound job listings for companies hiring engineers."""
    leads = []
    seen  = set()

    urls = [
        "https://wellfound.com/jobs?role=software-engineer&location=united-states",
        "https://wellfound.com/jobs?role=software-engineer&location=united-kingdom",
        "https://wellfound.com/jobs?role=backend-engineer",
        "https://wellfound.com/jobs?role=full-stack-engineer",
    ]

    for url in urls:
        if len(leads) >= max_results:
            break
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                log.debug(f"Wellfound {url} returned {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Try multiple card selectors (site layout can vary)
            cards = (
                soup.select("[class*='job-listing']") or
                soup.select("[class*='JobListing']")  or
                soup.select("[class*='startup']")     or
                soup.select("li[class*='job']")       or
                soup.select("div[data-test]")
            )

            for card in cards:
                lead = _parse_job_card(card)
                if lead and lead["company_name"] not in seen:
                    seen.add(lead["company_name"])
                    leads.append(lead)
                if len(leads) >= max_results:
                    break

        except Exception as e:
            log.warning(f"Wellfound scrape error ({url}): {e}")

    # Fallback: scrape startup listing page
    if not leads:
        leads = _scrape_startup_listing(max_results)

    log.info(f"Wellfound -> {len(leads)} leads")
    return leads


def _scrape_startup_listing(max_results: int = 20) -> list:
    """Fallback: scrape Wellfound startup directory instead of job listings."""
    leads = []
    seen  = set()
    url   = "https://wellfound.com/startups"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []

        soup  = BeautifulSoup(resp.text, "lxml")
        items = (
            soup.select("[class*='startup-item']") or
            soup.select("[class*='StartupResult']") or
            soup.select("li[class*='startup']") or
            soup.select("div[class*='startup']")
        )

        for item in items[:max_results]:
            name_el = item.select_one("h2, h3, [class*='name'], strong")
            link_el = item.select_one("a[href]")
            desc_el = item.select_one("p, [class*='pitch'], [class*='tagline']")

            name = name_el.get_text(strip=True) if name_el else ""
            if not name or name in seen:
                continue
            seen.add(name)

            href = link_el.get("href", "") if link_el else ""
            src  = f"https://wellfound.com{href}" if href.startswith("/") else href
            desc = desc_el.get_text(strip=True) if desc_el else ""

            leads.append({
                "id":             make_id(),
                "company_name":   name,
                "website":        "",
                "linkedin_url":   "",
                "location":       "Unknown",
                "market":         "Unknown",
                "team_size":      5,
                "funding":        None,
                "source":         "wellfound",
                "source_url":     src,
                "raw_signals":    ["active_startup", "wellfound_listed"],
                "description":    desc[:200],
                "founder_name":   None,
                "founder_handle": None,
            })
    except Exception as e:
        log.warning(f"Wellfound startup listing error: {e}")

    return leads
