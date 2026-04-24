"""
Free email finder — no paid API required.

Strategy (in priority order):
1. Hunter.io free tier (25 lookups/month) — if HUNTER_API_KEY set
2. Email permutation + SMTP verification (completely free, unlimited)
3. Scrape company website for mailto: links
"""
import os
import re
import socket
import smtplib
import requests
from typing import Optional
from utils.helpers import get_logger, extract_domain

log = get_logger(__name__)

# Common email patterns ordered by likelihood
EMAIL_PATTERNS = [
    "{first}@{domain}",
    "{first}.{last}@{domain}",
    "{f}{last}@{domain}",
    "{first}{last}@{domain}",
    "{first}_{last}@{domain}",
    "{last}@{domain}",
    "{f}.{last}@{domain}",
    "{first}{l}@{domain}",
    "{first}-{last}@{domain}",
    "contact@{domain}",
    "hello@{domain}",
    "info@{domain}",
    "founder@{domain}",
    "ceo@{domain}",
]

SMTP_FROM = "verify@gmail.com"


# ── Hunter.io (free 25/month) ────────────────────────────────────────────────

def find_email_hunter(first_name: str, last_name: str, domain: str) -> Optional[str]:
    api_key = os.getenv("HUNTER_API_KEY")
    if not api_key:
        return None
    try:
        resp = requests.get(
            "https://api.hunter.io/v2/email-finder",
            params={
                "domain": domain,
                "first_name": first_name,
                "last_name": last_name,
                "api_key": api_key,
            },
            timeout=10,
        )
        data = resp.json()
        email = data.get("data", {}).get("email")
        if email:
            log.info(f"Hunter found: {email}")
        return email
    except Exception as e:
        log.debug(f"Hunter.io error: {e}")
        return None


# ── SMTP Verification ────────────────────────────────────────────────────────

def _get_mx_host(domain: str) -> Optional[str]:
    try:
        import dns.resolver
        records = dns.resolver.resolve(domain, "MX")
        return sorted(records, key=lambda r: r.preference)[0].exchange.to_text().rstrip(".")
    except Exception:
        return None


def verify_email_smtp(email: str) -> bool:
    """
    Verify an email address by connecting to the MX server.
    Returns True if the server accepts the address.
    Note: Some servers return 250 for all addresses (catch-all).
    """
    domain = email.split("@")[1]
    mx = _get_mx_host(domain)
    if not mx:
        return False
    try:
        with smtplib.SMTP(timeout=8) as s:
            s.connect(mx, 25)
            s.ehlo("verify.local")
            s.mail(SMTP_FROM)
            code, _ = s.rcpt(email)
            s.quit()
            return code == 250
    except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected,
            socket.timeout, ConnectionRefusedError):
        return False
    except Exception:
        return False


def _is_catchall(domain: str) -> bool:
    """Check if the domain accepts all addresses (catch-all)."""
    test_email = f"xyzrandom99999@{domain}"
    return verify_email_smtp(test_email)


# ── Website Scraping ─────────────────────────────────────────────────────────

def scrape_emails_from_website(website: str) -> list[str]:
    if not website:
        return []
    try:
        from tools.scraper_tool import fetch_page
        result = fetch_page(website, timeout=8)
        if result:
            return result.get("emails", [])
        return []
    except Exception:
        return []


# ── Main Finder ──────────────────────────────────────────────────────────────

def generate_permutations(first: str, last: str, domain: str) -> list[str]:
    first = (first or "").lower().strip()
    last = (last or "").lower().strip()
    f = first[0] if first else ""
    l = last[0] if last else ""

    emails = []
    for pattern in EMAIL_PATTERNS:
        try:
            email = pattern.format(
                first=first, last=last, f=f, l=l, domain=domain
            )
            if "@" in email and email not in emails:
                emails.append(email)
        except KeyError:
            continue
    return emails


def find_email(
    first_name: str,
    last_name: str,
    domain: str,
    website: str = "",
) -> Optional[str]:
    """
    Find a valid email for a person at a domain.
    Tries Hunter.io free tier first, then SMTP verification of permutations.
    """
    if not domain:
        return None

    # 1. Hunter.io (free 25/month)
    email = find_email_hunter(first_name, last_name, domain)
    if email:
        return email

    # 2. Scrape website for mailto links
    website_emails = scrape_emails_from_website(website or f"https://{domain}")
    personal_emails = [
        e for e in website_emails
        if not any(g in e for g in ["noreply", "support", "sales", "newsletter", "help"])
    ]
    if personal_emails:
        return personal_emails[0]

    # 3. Email permutation + SMTP verify
    # Skip if domain is a catch-all (would validate everything as true)
    if _is_catchall(domain):
        log.debug(f"{domain} is catch-all — skipping SMTP verify")
        candidates = generate_permutations(first_name, last_name, domain)
        return candidates[0] if candidates else None

    for email in generate_permutations(first_name, last_name, domain):
        if verify_email_smtp(email):
            log.info(f"SMTP verified: {email}")
            return email

    return None


def find_email_for_lead(lead: dict) -> Optional[str]:
    """Convenience wrapper — takes a LeadState dict."""
    contact = lead.get("contact") or {}
    name = contact.get("name") or lead.get("founder_name") or ""
    parts = name.strip().split()
    first = parts[0] if parts else ""
    last = parts[-1] if len(parts) > 1 else ""

    domain = extract_domain(lead.get("website") or "")
    if not domain:
        return None

    return find_email(first, last, domain, lead.get("website", ""))
