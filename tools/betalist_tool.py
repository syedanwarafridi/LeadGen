"""
BetaList discovery tool — scrapes new startup launches.
BetaList features early-stage products by solo founders and tiny teams.
No API key or registration needed. Fully public.
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

PAGES_TO_SCRAPE = [
    "https://betalist.com/",
    "https://betalist.com/startups",
]


def _parse_startup_card(card) -> dict | None:
    try:
        name_el  = card.select_one("h2, h3, [class*='title'], [class*='name']")
        desc_el  = card.select_one("p, [class*='tagline'], [class*='description'], [class*='pitch']")
        link_el  = card.select_one("a[href]")
        tag_els  = card.select("[class*='tag'], [class*='badge'], [class*='category']")

        name = name_el.get_text(strip=True) if name_el else ""
        if not name:
            return None

        desc = desc_el.get_text(strip=True) if desc_el else ""
        href = link_el.get("href", "") if link_el else ""
        tags = [t.get_text(strip=True) for t in tag_els if t.get_text(strip=True)]

        source_url = ""
        if href.startswith("/"):
            source_url = f"https://betalist.com{href}"
        elif href.startswith("http"):
            source_url = href

        # Detect website from description or card links
        all_links = card.select("a[href]")
        website = next(
            (a.get("href", "") for a in all_links
             if a.get("href", "").startswith("http")
             and "betalist.com" not in a.get("href", "")),
            ""
        )

        geo = detect_geo_from_text(f"{name} {desc}")

        signals = ["active_product", "betalist_launch", "solo_founder"]
        if any(t in " ".join(tags).lower() for t in ["saas", "b2b", "api", "developer"]):
            signals.append("saas_product")

        return {
            "id":             make_id(),
            "company_name":   name,
            "website":        website,
            "linkedin_url":   "",
            "location":       "Unknown",
            "market":         geo if geo != "Unknown" else "Unknown",
            "team_size":      1,
            "funding":        None,
            "source":         "betalist",
            "source_url":     source_url,
            "raw_signals":    signals,
            "description":    desc[:300],
            "founder_name":   None,
            "founder_handle": None,
        }
    except Exception:
        return None


def scrape_betalist(max_results: int = 20) -> list:
    """Scrape BetaList for recent startup launches."""
    leads = []
    seen  = set()

    for url in PAGES_TO_SCRAPE:
        if len(leads) >= max_results:
            break
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                log.debug(f"BetaList {url} returned {resp.status_code}")
                continue

            soup  = BeautifulSoup(resp.text, "lxml")

            # Try multiple card selectors
            cards = (
                soup.select("[class*='startup']")  or
                soup.select("[class*='product']")  or
                soup.select("article")             or
                soup.select("li[class]")
            )

            for card in cards:
                # Skip nav/footer/misc elements
                if len(card.get_text(strip=True)) < 10:
                    continue

                lead = _parse_startup_card(card)
                if not lead:
                    continue
                if lead["company_name"] in seen:
                    continue
                seen.add(lead["company_name"])
                leads.append(lead)

                if len(leads) >= max_results:
                    break

        except Exception as e:
            log.warning(f"BetaList scrape error ({url}): {e}")

    log.info(f"BetaList -> {len(leads)} leads")
    return leads
