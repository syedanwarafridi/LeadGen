"""
Y Combinator company directory scraper.
YC companies are the highest-quality leads — seed/Series A funded,
typically non-technical founders, small teams, actively building products.
No API key required. Uses YC's public Algolia search API (same one
that powers ycombinator.com/companies search in the browser).
"""
import requests
from utils.helpers import get_logger, make_id, detect_geo_from_text

log = get_logger(__name__)

# YC's public Algolia credentials (these power the public company directory)
YC_ALGOLIA_APP  = "45BWZJ1SGC"
YC_ALGOLIA_KEY  = "be97643f5ba4d9e84fe3a85c7cf836a5"
YC_ALGOLIA_URL  = f"https://{YC_ALGOLIA_APP}-dsn.algolia.net/1/indexes/*/queries"

# Recent batches to target (most likely to still be building their product)
RECENT_BATCHES  = ["W25", "S24", "W24", "S23", "W23"]

HEADERS = {
    "X-Algolia-Application-Id": YC_ALGOLIA_APP,
    "X-Algolia-API-Key":        YC_ALGOLIA_KEY,
    "Content-Type":             "application/json",
}


def _hit_to_lead(hit: dict) -> dict:
    name       = hit.get("name", "Unknown")
    website    = hit.get("website", "") or ""
    desc       = hit.get("one_liner", "") or hit.get("long_description", "") or ""
    location   = hit.get("location", "") or ""
    batch      = hit.get("batch", "")
    team_size  = hit.get("team_size", 5) or 5
    industries = hit.get("industries", []) or []
    slug       = hit.get("slug", "")

    geo = detect_geo_from_text(location)

    signals = ["yc_funded", "active_startup"]
    if batch in RECENT_BATCHES:
        signals.append("recently_funded")
    if team_size <= 10:
        signals.append("small_team")
    if any(w in " ".join(industries).lower() for w in ["saas", "b2b", "software"]):
        signals.append("saas_product")

    return {
        "id":             make_id(),
        "company_name":   name,
        "website":        website,
        "linkedin_url":   "",
        "location":       location or "Unknown",
        "market":         geo if geo != "Unknown" else "US",  # most YC cos are US
        "team_size":      int(team_size),
        "funding":        {"stage": f"YC {batch}", "amount": 500000, "date": ""},
        "source":         "yc_directory",
        "source_url":     f"https://www.ycombinator.com/companies/{slug}",
        "raw_signals":    signals,
        "description":    desc[:300],
        "founder_name":   None,
        "founder_handle": None,
    }


def fetch_yc_companies(batches: list = None, max_results: int = 30) -> list:
    """
    Fetch YC companies via their public Algolia API.
    Targets recent batches with small teams — highest ICP match.
    """
    batches = batches or RECENT_BATCHES
    leads   = []
    seen    = set()

    for batch in batches:
        if len(leads) >= max_results:
            break
        try:
            payload = {
                "requests": [{
                    "indexName": "YCCompany_production",
                    "params": (
                        f"query=&"
                        f"filters=batch%3A{batch}&"
                        f"hitsPerPage=20&"
                        f"attributesToRetrieve=name,website,one_liner,"
                        f"long_description,location,batch,team_size,"
                        f"industries,slug"
                    ),
                }]
            }
            resp = requests.post(YC_ALGOLIA_URL, json=payload, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                log.warning(f"YC Algolia returned {resp.status_code} for batch {batch}")
                continue

            hits = resp.json().get("results", [{}])[0].get("hits", [])
            for hit in hits:
                name = hit.get("name", "")
                if name in seen:
                    continue
                seen.add(name)
                leads.append(_hit_to_lead(hit))

            log.debug(f"YC batch {batch}: {len(hits)} companies")

        except Exception as e:
            log.warning(f"YC fetch error (batch {batch}): {e}")

    # Fallback: scrape YC website if Algolia fails
    if not leads:
        log.info("YC Algolia failed — trying HTML scrape fallback")
        leads = _scrape_yc_html(max_results)

    log.info(f"YC Directory -> {len(leads)} leads")
    return leads


def _scrape_yc_html(max_results: int = 20) -> list:
    """Fallback: scrape YC public companies page."""
    from bs4 import BeautifulSoup

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    leads   = []
    try:
        resp = requests.get(
            "https://www.ycombinator.com/companies?batch=W25",
            headers=headers, timeout=15
        )
        soup  = BeautifulSoup(resp.text, "lxml")
        items = soup.select("a[href*='/companies/']")[:max_results]

        for item in items:
            name_el = item.select_one("span, h2, h3, strong")
            name    = name_el.get_text(strip=True) if name_el else item.get_text(strip=True)
            href    = item.get("href", "")

            if not name or len(name) < 2:
                continue

            leads.append({
                "id":             make_id(),
                "company_name":   name,
                "website":        "",
                "linkedin_url":   "",
                "location":       "Unknown",
                "market":         "US",
                "team_size":      5,
                "funding":        {"stage": "YC", "amount": 500000, "date": ""},
                "source":         "yc_directory",
                "source_url":     f"https://www.ycombinator.com{href}",
                "raw_signals":    ["yc_funded", "recently_funded", "small_team"],
                "description":    "",
                "founder_name":   None,
                "founder_handle": None,
            })
    except Exception as e:
        log.warning(f"YC HTML scrape error: {e}")

    return leads
