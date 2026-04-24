"""
Node 3 — Enrichment Agent
Finds contact email, tech stack, recent news, and a personalization hook
for each qualified lead. Uses only free methods.

Free enrichment methods:
  1. Scrape company website (contact emails, tech stack)
  2. Email permutation + SMTP verify (free, unlimited)
  3. Hunter.io free tier (25/month — optional)
  4. GitHub API (free) for repos associated with the company
  5. DuckDuckGo news search (free)
"""
import os
from utils.helpers import get_logger, extract_domain
from graph.state import PipelineState

log = get_logger(__name__)


def _enrich_single(lead: dict) -> dict:
    website = lead.get("website") or ""
    founder_name = lead.get("founder_name") or ""
    company = lead.get("company_name", "")
    domain = extract_domain(website)

    contact = {}
    tech_stack = []
    hook = ""

    # ── Step 1: Scrape website ───────────────────────────────
    if website:
        try:
            from tools.scraper_tool import fetch_page
            page = fetch_page(website, timeout=10)
            if page:
                tech_stack = page.get("tech_stack", [])
                website_emails = page.get("emails", [])
                # Pick the most likely founder/contact email
                filtered = [
                    e for e in website_emails
                    if not any(x in e for x in ["noreply", "support", "newsletter", "help", "abuse"])
                ]
                if filtered and not contact.get("email"):
                    contact["email"] = filtered[0]
                if page.get("description") and not hook:
                    hook = f"Website: {page['description'][:120]}"
        except Exception as e:
            log.debug(f"Website scrape failed for {company}: {e}")

    # ── Step 2: Find email via permutation/Hunter.io ─────────
    if not contact.get("email") and founder_name and domain:
        try:
            from tools.email_finder_tool import find_email_for_lead
            email = find_email_for_lead({**lead, "contact": contact})
            if email:
                contact["email"] = email
        except Exception as e:
            log.debug(f"Email finder failed for {company}: {e}")

    # ── Step 3: GitHub profile enrichment ───────────────────
    handle = lead.get("founder_handle") or ""
    if handle and lead.get("source") == "github":
        try:
            from tools.github_tool import get_repo_owner_info
            gh_info = get_repo_owner_info(handle)
            if gh_info:
                if not contact.get("name") and gh_info.get("name"):
                    contact["name"] = gh_info["name"]
                if not contact.get("email") and gh_info.get("email"):
                    contact["email"] = gh_info["email"]
                if gh_info.get("blog"):
                    contact["website"] = gh_info["blog"]
                if gh_info.get("location") and lead.get("location") == "Unknown":
                    lead = {**lead, "location": gh_info["location"]}
                if gh_info.get("bio") and not hook:
                    hook = f"GitHub bio: {gh_info['bio'][:120]}"
        except Exception as e:
            log.debug(f"GitHub enrichment failed for {company}: {e}")

    # ── Step 4: News / context snippets ─────────────────────
    if company and not hook:
        try:
            from tools.scraper_tool import get_news_snippets
            snippets = get_news_snippets(company, max_results=2)
            if snippets:
                hook = snippets[0][:150]
        except Exception as e:
            log.debug(f"News search failed for {company}: {e}")

    # ── Step 5: Build hook from raw signals ─────────────────
    if not hook:
        signals = lead.get("hot_signals") or lead.get("raw_signals") or []
        if signals:
            hook = f"Signals: {', '.join(signals[:3])}"
        elif lead.get("description"):
            hook = lead["description"][:120]

    # ── Fallback contact name ───────────────────────────────
    if not contact.get("name"):
        contact["name"] = founder_name or ""
    if not contact.get("role"):
        contact["role"] = "Founder"

    return {
        **lead,
        "contact": contact,
        "tech_stack": list(set(tech_stack)),
        "hook": hook,
    }


def run_enrichment(state: PipelineState) -> PipelineState:
    """LangGraph Node 3 — enrich each qualified lead with contact + context."""
    log.info("=== Node 3: Enrichment ===")
    qualified = state.get("qualified", [])
    errors = list(state.get("errors", []))

    enriched = []
    for lead in qualified:
        try:
            result = _enrich_single(lead)
            has_email = bool((result.get("contact") or {}).get("email"))
            log.info(
                f"  Enriched: {lead.get('company_name')} | "
                f"email={'✓' if has_email else '✗'} | "
                f"tech={result.get('tech_stack', [])[:3]}"
            )
            enriched.append(result)
        except Exception as e:
            log.error(f"Enrichment failed for {lead.get('company_name')}: {e}")
            errors.append(f"enrichment:{lead.get('company_name')}:{e}")
            enriched.append(lead)  # Keep unenriched lead in pipeline

    log.info(f"Enrichment complete: {len(enriched)} leads processed")
    return {**state, "qualified": enriched, "errors": errors}
