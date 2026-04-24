"""
Generic web scraper — fetches a URL and returns clean text + metadata.
Used by enrichment agent to scrape company websites.
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional
from utils.helpers import get_logger, extract_emails_from_text, clean_text

log = get_logger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

TECH_SIGNATURES = {
    "React":       ["react", "reactdom", "_next/", "__NEXT_DATA__"],
    "Next.js":     ["_next/", "__NEXT_DATA__", "next/dist"],
    "Vue.js":      ["vue.min.js", "vuejs.org", "__vue__"],
    "Angular":     ["ng-version", "angular/core", "angular.min.js"],
    "Django":      ["csrfmiddlewaretoken", "django", "__django__"],
    "Laravel":     ["laravel_session", "csrf-token", "laravel"],
    "WordPress":   ["wp-content/", "wp-includes/", "wp-json/"],
    "Shopify":     ["cdn.shopify.com", "shopify.com/s/"],
    "Wix":         ["wixsite.com", "wix.com", "wixstatic"],
    "Squarespace": ["squarespace.com", "static1.squarespace"],
    "Node.js":     ["express", "node_modules"],
    "Ruby on Rails": ["rails", "csrf-token"],
    "Flutter":     ["flutter.js", "flt-renderer"],
    "React Native":["react-native"],
    "Stripe":      ["stripe.com/v3", "js.stripe.com"],
    "AWS":         ["amazonaws.com", "cloudfront.net"],
    "Vercel":      ["vercel.app", "_vercel"],
    "Netlify":     ["netlify.com", "netlify"],
}


def fetch_page(url: str, timeout: int = 10) -> Optional[dict]:
    """Fetch URL and return {text, html, emails, tech_stack, title, description}."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = clean_text(soup.get_text(separator=" "))
        html = resp.text.lower()

        title = ""
        if soup.title:
            title = clean_text(soup.title.string or "")

        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            description = clean_text(meta_desc.get("content", ""))

        emails = extract_emails_from_text(text)

        tech_stack = [
            tech for tech, patterns in TECH_SIGNATURES.items()
            if any(p in html for p in patterns)
        ]

        return {
            "text": text[:3000],
            "html": html,
            "emails": emails,
            "tech_stack": tech_stack,
            "title": title,
            "description": description,
        }
    except Exception as e:
        log.debug(f"fetch_page failed for {url}: {e}")
        return None


def scrape_linkedin_profile(username: str) -> Optional[dict]:
    """Scrape public LinkedIn profile for basic info (no auth needed)."""
    url = f"https://www.linkedin.com/in/{username}"
    result = fetch_page(url)
    if not result:
        return None
    return {"text": result["text"][:1000]}


def get_news_snippets(company_name: str, max_results: int = 3) -> list[str]:
    """Search DuckDuckGo for recent news about the company (free, no API key)."""
    try:
        url = "https://html.duckduckgo.com/html/"
        params = {"q": f"{company_name} startup news 2024 2025"}
        resp = requests.post(url, data=params, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        snippets = []
        for result in soup.select(".result__snippet")[:max_results]:
            snippets.append(clean_text(result.get_text()))
        return snippets
    except Exception as e:
        log.debug(f"news search failed for {company_name}: {e}")
        return []
