"""
Pipeline module - Bronze/Silver/Gold data layers.
"""
from .schema import ArticleSchema, CrawlBatchSchema
from .cleaner import clean_html, is_advertisement, extract_summary, extract_lead_paragraph
from .deduplicator import Deduplicator, FuzzyDeduplicator, normalize_url, content_hash
from .parquet_writer import (
    write_partitioned_parquet,
    convert_raw_json_to_parquet,
    _articles_from_raw_json,
)

__all__ = [
    "ArticleSchema",
    "CrawlBatchSchema",
    "clean_html",
    "is_advertisement",
    "extract_summary",
    "extract_lead_paragraph",
    "Deduplicator",
    "FuzzyDeduplicator",
    "normalize_url",
    "content_hash",
    "write_partitioned_parquet",
    "convert_raw_json_to_parquet",
]
