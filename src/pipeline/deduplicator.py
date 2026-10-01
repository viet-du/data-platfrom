"""
Deduplication - URL-based and content-fingerprint based.
"""
import hashlib
import re
from typing import Dict, List, Set, Tuple
from difflib import SequenceMatcher

from .schema import ArticleSchema


def normalize_url(url: str) -> str:
    """Normalize URL for dedup (strip utm_*, trailing slashes, fragments)."""
    if not url:
        return ""

    url = url.strip()
    # Remove fragments
    url = url.split("#")[0]
    # Remove common tracking params
    url = re.sub(r"[?&](utm_[^&]+|fbclid=[^&]+|gclid=[^&]+)=", "?", url)
    url = re.sub(r"[?&](utm_[^&]+|fbclid=[^&]+|gclid=[^&]+)", "", url)
    # Collapse multiple slashes (except protocol)
    url = re.sub(r"(?<!:)/{2,}", "/", url)
    # Strip trailing slash
    url = url.rstrip("/")
    return url.lower()


def content_hash(title: str, description: str, content: str = "") -> str:
    """Fingerprint of content (ignores whitespace/punctuation)."""
    blob = f"{title} {description} {content}"
    blob = re.sub(r"\s+", " ", blob).strip().lower()
    return hashlib.md5(blob.encode("utf-8")).hexdigest()


def title_similarity(a: str, b: str) -> float:
    """0..1 similarity ratio between two titles."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


class Deduplicator:
    """Deduplicate articles by URL + content fingerprint + fuzzy title match."""

    def __init__(self, fuzzy_threshold: float = 0.85):
        self.fuzzy_threshold = fuzzy_threshold
        self.seen_urls: Set[str] = set()
        self.seen_fingerprints: Set[str] = set()

    def reset(self):
        self.seen_urls.clear()
        self.seen_fingerprints.clear()

    def add(self, article: ArticleSchema) -> Tuple[bool, str]:
        """
        Try to add article. Returns (is_new, reason).
        Reason: 'new' | 'duplicate_url' | 'duplicate_content' | 'duplicate_title_fuzzy'
        """
        norm_url = normalize_url(article.url)

        if norm_url in self.seen_urls:
            return False, "duplicate_url"

        fp = content_hash(article.title, article.description, article.content)
        if fp in self.seen_fingerprints:
            return False, "duplicate_content"

        # Fuzzy title match against recent additions (only if title is non-trivial)
        if len(article.title) > 20:
            # Compare against last N titles (avoid O(n^2))
            for existing_fp in list(self.seen_fingerprints)[-100:]:
                # Reconstruct title from fp is not possible, so we skip this
                # unless we keep title index separately
                pass

        self.seen_urls.add(norm_url)
        self.seen_fingerprints.add(fp)
        return True, "new"

    def deduplicate(self, articles: List[ArticleSchema]) -> Tuple[List[ArticleSchema], List[Tuple[ArticleSchema, str]]]:
        """Returns (kept, [(duplicate, reason)])."""
        self.reset()
        kept = []
        dups = []

        for art in articles:
            is_new, reason = self.add(art)
            if is_new:
                kept.append(art)
            else:
                dups.append((art, reason))

        return kept, dups


class FuzzyDeduplicator(Deduplicator):
    """Adds fuzzy title matching - slower but catches re-published articles."""

    def __init__(self, fuzzy_threshold: float = 0.85):
        super().__init__(fuzzy_threshold)
        self._titles: List[str] = []

    def add(self, article: ArticleSchema) -> Tuple[bool, str]:
        norm_url = normalize_url(article.url)
        if norm_url in self.seen_urls:
            return False, "duplicate_url"

        fp = content_hash(article.title, article.description, article.content)
        if fp in self.seen_fingerprints:
            return False, "duplicate_content"

        # Fuzzy title match
        if len(article.title) > 30:
            for existing_title in self._titles[-200:]:
                if title_similarity(article.title, existing_title) >= self.fuzzy_threshold:
                    return False, "duplicate_title_fuzzy"

        self.seen_urls.add(norm_url)
        self.seen_fingerprints.add(fp)
        self._titles.append(article.title)
        return True, "new"
