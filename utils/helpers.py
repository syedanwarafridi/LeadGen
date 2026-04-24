import re
import uuid
import logging
from urllib.parse import urlparse
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def make_id() -> str:
    return str(uuid.uuid4())[:8]


def extract_domain(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        domain = parsed.netloc or parsed.path
        return domain.lstrip("www.").split("/")[0].lower()
    except Exception:
        return None


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


def extract_emails_from_text(text: str) -> list[str]:
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    return list(set(re.findall(pattern, text)))


def extract_urls_from_text(text: str) -> list[str]:
    pattern = r"https?://[^\s\"'>]+"
    return list(set(re.findall(pattern, text)))


def detect_geo_from_text(text: str) -> str:
    text_lower = (text or "").lower()
    us_signals = ["united states", " usa", " us ", "new york", "san francisco",
                  "california", "texas", "silicon valley", "boston", "seattle"]
    uk_signals = ["united kingdom", " uk ", "london", "manchester", "edinburgh",
                  "birmingham", " england", " scotland", " wales"]
    uae_signals = ["dubai", "abu dhabi", "uae", "united arab emirates", "sharjah"]

    for s in us_signals:
        if s in text_lower:
            return "US"
    for s in uk_signals:
        if s in text_lower:
            return "UK"
    for s in uae_signals:
        if s in text_lower:
            return "UAE"
    return "Unknown"


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")
