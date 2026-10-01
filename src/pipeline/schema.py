"""
Data Pipeline - Bronze/Silver/Gold schema definitions
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator, HttpUrl
import hashlib
import re


class ArticleSchema(BaseModel):
    """Canonical schema for all crawled articles across sources."""

    article_id: str = Field(default="", description="SHA-256 hash of URL (deterministic)")
    url: str = Field(..., description="Source article URL")
    source: str = Field(..., description="Source name: VNExpress, TuoiTre, etc.")
    title: str = Field(default="", description="Article title")
    description: str = Field(default="", description="Article summary/description")
    content: str = Field(default="", description="Full article body if extracted")
    author: Optional[str] = Field(default=None, description="Author name")
    category: Optional[str] = Field(default=None, description="Category slug")
    published_date: Optional[str] = Field(default=None, description="ISO 8601 publish date")
    crawled_at: datetime = Field(default_factory=lambda: datetime.utcnow(), description="UTC crawl timestamp")
    language: str = Field(default="vi", description="ISO 639-1 language code")
    word_count: int = Field(default=0, description="Body word count")
    has_title: bool = Field(default=False, description="Whether title is non-empty")

    @validator("url")
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL: {v}")
        return v

    @validator("title", "description", "content", pre=True)
    def clean_text(cls, v) -> str:
        if not v:
            return ""
        # Strip whitespace, collapse multiple spaces, remove control chars
        text = re.sub(r"[\x00-\x1f\x7f]", " ", str(v))
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def compute_id(url: str) -> str:
        """Deterministic article ID from URL."""
        return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]

    def derive_fields(self) -> "ArticleSchema":
        """Compute derived fields (id, word_count, has_title)."""
        self.article_id = self.compute_id(self.url)
        body = f"{self.title} {self.description} {self.content}".strip()
        self.word_count = len(body.split()) if body else 0
        self.has_title = bool(self.title and self.title.strip())
        return self


class CrawlBatchSchema(BaseModel):
    """Batch of articles from a single crawl run."""

    source: str
    crawled_at: datetime
    total_articles: int
    valid_articles: int = 0
    invalid_articles: int = 0
    articles: List[ArticleSchema] = Field(default_factory=list)

    def stats(self) -> dict:
        return {
            "source": self.source,
            "total": self.total_articles,
            "valid": self.valid_articles,
            "invalid": self.invalid_articles,
            "with_title": sum(1 for a in self.articles if a.has_title),
            "total_words": sum(a.word_count for a in self.articles),
        }
