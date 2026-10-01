"""
HTML Cleaner - Strip tags, normalize whitespace, remove boilerplate.
"""
import re
from typing import Optional
from bs4 import BeautifulSoup


# Common boilerplate patterns in Vietnamese news sites
BOILERPLATE_PATTERNS = [
    r"(?i)(đăng ký|liên hệ|quảng cáo|theo dõi).{0,100}(facebook|youtube|tiktok)",
    r"(?i)tags?:\s*[^\n]+",
    r"(?i)tin liên quan:.*",
    r"(?i)\(video[^\)]*\)",
    r"(?i)xem thêm:.*",
    r"\s*\*\s*$",
]

AD_KEYWORDS = [
    "quảng cáo", "quang cao", "advertisement",
    "mua ngay", "đặt hàng", "dat hang",
    "liên hệ quảng cáo", "lien he quang cao",
]


def clean_html(html: str) -> str:
    """Convert HTML to plain text, removing scripts/styles/nav."""
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # Remove non-content tags
    for tag in soup(["script", "style", "noscript", "iframe", "nav",
                     "header", "footer", "aside", "form", "button"]):
        tag.decompose()

    # Get text
    text = soup.get_text(separator="\n")

    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = text.strip()

    # Remove boilerplate
    for pattern in BOILERPLATE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.DOTALL)

    return text.strip()


def is_advertisement(text: str, title: str = "") -> bool:
    """Heuristic: detect ad/native content blocks."""
    blob = f"{title} {text}".lower()
    return any(kw in blob for kw in AD_KEYWORDS)


def extract_summary(text: str, max_words: int = 50) -> str:
    """Extract first N words as summary."""
    if not text:
        return ""
    words = text.split()
    return " ".join(words[:max_words])


def extract_lead_paragraph(html: str, min_len: int = 50) -> Optional[str]:
    """Extract the lead paragraph (usually the news summary)."""
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Common Vietnamese news lead selectors
    for selector in [".description", ".lead", ".intro", "article p:first-of-type",
                     "h2 + p", ".article-summary"]:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(strip=True)
            if len(text) >= min_len:
                return text

    # Fallback: first <p> with substantial content
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) >= min_len:
            return text

    return None
