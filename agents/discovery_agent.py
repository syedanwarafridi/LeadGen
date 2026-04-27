"""
Node 1 — Discovery Agent
Pulls raw leads from multiple FREE sources in parallel.

Sources (all free, no API approval needed):
  - Wellfound      (AngelList) — startups hiring engineers   [web scrape]
  - YC Directory   — funded startups, exact ICP              [public Algolia API]
  - BetaList       — new product launches by solo founders   [web scrape]
  - HackerNews     — Show HN posts + keyword search          [Algolia API — free]
  - Product Hunt   — recent launches with small teams        [free token / scrape]
  - GitHub         — active startup repos                    [free API]
  - IndieHackers   — founders looking for developers         [web scrape]
"""
import concurrent.futures
from datetime import datetime
from utils.helpers import get_logger
from graph.state import PipelineState

log = get_logger(__name__)


def _load_config() -> dict:
    import yaml, os
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config", "icp_config.yaml")
    with open(cfg_path, "r") as f:
        return yaml.safe_load(f)


# ── Source functions ──────────────────────────────────────────────────────────

def _discover_wellfound(cfg: dict) -> list:
    from tools.wellfound_tool import scrape_wellfound_jobs
    try:
        leads = scrape_wellfound_jobs(max_results=25)
        log.info(f"Wellfound -> {len(leads)} leads")
        return leads
    except Exception as e:
        log.warning(f"Wellfound discovery failed: {e}")
        return []


def _discover_yc(cfg: dict) -> list:
    from tools.yc_tool import fetch_yc_companies
    try:
        leads = fetch_yc_companies(max_results=30)
        log.info(f"YC Directory -> {len(leads)} leads")
        return leads
    except Exception as e:
        log.warning(f"YC discovery failed: {e}")
        return []


def _discover_betalist(cfg: dict) -> list:
    from tools.betalist_tool import scrape_betalist
    try:
        leads = scrape_betalist(max_results=20)
        log.info(f"BetaList -> {len(leads)} leads")
        return leads
    except Exception as e:
        log.warning(f"BetaList discovery failed: {e}")
        return []


def _discover_hackernews(cfg: dict) -> list:
    from tools.hackernews_tool import search_hackernews, fetch_show_hn_posts
    hn_cfg = cfg.get("discovery", {}).get("hackernews", {})
    try:
        leads = search_hackernews(
            queries=hn_cfg.get("queries", ["looking for developer", "hiring engineer"]),
            per_query=hn_cfg.get("results_per_query", 10),
        )
        leads += fetch_show_hn_posts(days_back=30, limit=15)
        log.info(f"HackerNews -> {len(leads)} leads")
        return leads
    except Exception as e:
        log.warning(f"HackerNews discovery failed: {e}")
        return []


def _discover_producthunt(cfg: dict) -> list:
    from tools.producthunt_tool import fetch_producthunt_api
    ph_cfg = cfg.get("discovery", {}).get("product_hunt", {})
    try:
        leads = fetch_producthunt_api(
            days_back=ph_cfg.get("days_back", 30),
            max_results=ph_cfg.get("max_results", 20),
        )
        log.info(f"ProductHunt -> {len(leads)} leads")
        return leads
    except Exception as e:
        log.warning(f"ProductHunt discovery failed: {e}")
        return []


def _discover_github(cfg: dict) -> list:
    from tools.github_tool import search_github_startups
    gh_cfg = cfg.get("discovery", {}).get("github", {})
    try:
        leads = search_github_startups(
            topics=gh_cfg.get("topics", ["startup", "saas", "mvp"]),
            pushed_after=gh_cfg.get("pushed_after", "2024-01-01"),
            max_results=gh_cfg.get("max_results", 20),
        )
        log.info(f"GitHub -> {len(leads)} leads")
        return leads
    except Exception as e:
        log.warning(f"GitHub discovery failed: {e}")
        return []


def _discover_indiehackers(cfg: dict) -> list:
    """Scrape IndieHackers forum for 'looking for developer' posts."""
    import requests
    from bs4 import BeautifulSoup
    from utils.helpers import make_id

    leads = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        urls_to_try = [
            "https://www.indiehackers.com/forum/looking-for-a-technical-co-founder",
            "https://www.indiehackers.com/forum",
        ]
        for url in urls_to_try:
            resp = requests.get(url, headers=headers, timeout=12)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")

            for post in soup.select(".feed__story, .story, article")[:15]:
                title_el = post.select_one("h2, h3, .story__title, .feed__story-title")
                link_el  = post.select_one("a[href]")
                if not title_el:
                    continue

                title      = title_el.get_text(strip=True)
                href       = link_el.get("href", "") if link_el else ""
                source_url = f"https://www.indiehackers.com{href}" if href.startswith("/") else href

                if not any(k in title.lower() for k in
                           ["developer", "technical", "build", "mvp", "cto", "co-founder"]):
                    continue

                leads.append({
                    "id":             make_id(),
                    "company_name":   f"IH: {title[:60]}",
                    "website":        "",
                    "linkedin_url":   "",
                    "location":       "Unknown",
                    "market":         "Unknown",
                    "team_size":      1,
                    "funding":        None,
                    "source":         "indiehackers",
                    "source_url":     source_url,
                    "raw_signals":    ["looking_for_developer", "indie_hacker"],
                    "description":    title[:300],
                    "founder_name":   None,
                    "founder_handle": None,
                })
            if leads:
                break
    except Exception as e:
        log.warning(f"IndieHackers scrape failed: {e}")

    log.info(f"IndieHackers -> {len(leads)} leads")
    return leads


# ── Deduplication ─────────────────────────────────────────────────────────────

def _deduplicate(leads: list) -> list:
    """Remove duplicates within this run AND leads already seen in previous runs."""
    from utils.helpers import extract_domain
    from utils.local_db import is_lead_seen, init_db

    init_db()

    seen_domains  = set()
    seen_names    = set()
    unique        = []
    skipped_prev  = 0

    for lead in leads:
        domain   = extract_domain(lead.get("website") or "")
        name_key = (lead.get("company_name") or "").lower().strip()[:30]

        # Skip duplicates within this run
        if domain and domain in seen_domains:
            continue
        if name_key and name_key in seen_names:
            continue

        # Skip leads already processed in a previous run
        if is_lead_seen(domain or "", lead.get("company_name") or ""):
            skipped_prev += 1
            continue

        if domain:
            seen_domains.add(domain)
        if name_key:
            seen_names.add(name_key)
        unique.append(lead)

    if skipped_prev:
        log.info(f"Skipped {skipped_prev} already-processed leads from previous runs")

    return unique


# ── LangGraph Node ────────────────────────────────────────────────────────────

def run_discovery(state: PipelineState) -> PipelineState:
    """LangGraph Node 1 — discover raw leads from all free sources in parallel."""
    log.info("=== Node 1: Discovery ===")
    cfg = _load_config()

    tasks = [
        _discover_wellfound,
        _discover_yc,
        _discover_betalist,
        _discover_hackernews,
        _discover_producthunt,
        _discover_github,
        _discover_indiehackers,
    ]

    all_leads = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
        futures = {pool.submit(fn, cfg): fn.__name__ for fn in tasks}
        for future in concurrent.futures.as_completed(futures):
            try:
                all_leads.extend(future.result())
            except Exception as e:
                log.error(f"Discovery task error: {e}")

    unique_leads = _deduplicate(all_leads)
    log.info(f"Discovery complete: {len(all_leads)} raw -> {len(unique_leads)} unique")

    return {
        **state,
        "leads":    unique_leads,
        "run_date": datetime.utcnow().isoformat(),
        "errors":   state.get("errors", []),
    }
