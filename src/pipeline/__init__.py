"""Trang public API cho data pipeline Bronze/Silver/Gold.

Eager: chỉ những import nhẹ, không side-effect (Schema + transform helpers).
Lazy: mọi thứ nặng (Deduplicator/Dedup classes, parquet helpers, Orchestrator
      + Pipeline class) được load qua __getattr__ — để tránh:
        1. Circular import khi các entry point chỉ cần 1-2 class.
        2. ImportError do pandas missing ở môi trường dev/test.
        3. Lazy import thường gặp khi worker boot có thứ tự không deterministic.

Public API:
  Schema:
    ArticleSchema        — canonical article record (Bronze + Silver)
    CrawlBatchSchema     — wrapper cho 1 crawl batch
  Transforms (eager — pure functions, no deps):
    clean_html, is_advertisement, extract_summary, extract_lead_paragraph
    normalize_url, content_hash
  Dedup (lazy — depends on schema):
    Deduplicator, FuzzyDeduplicator
  Orchestrator (lazy — depends on dedup + parquet_writer may need pandas):
    Pipeline, get_pipeline, LayerStats, PipelineResult
  Parquet (lazy — requires pandas):
    write_partitioned_parquet, convert_raw_json_to_parquet
"""
from .schema import ArticleSchema, CrawlBatchSchema
from .cleaner import clean_html, is_advertisement, extract_summary, extract_lead_paragraph
from .deduplicator import normalize_url, content_hash

_LAZY_EXPORTS = {
    # dedup
    "Deduplicator": ("deduplicator", "Deduplicator"),
    "FuzzyDeduplicator": ("deduplicator", "FuzzyDeduplicator"),
    # orchestrator
    "Pipeline": ("orchestrator", "Pipeline"),
    "PipelineResult": ("orchestrator", "PipelineResult"),
    "LayerStats": ("orchestrator", "LayerStats"),
    "get_pipeline": ("orchestrator", "get_pipeline"),
    # parquet (requires pandas — guarded by caller)
    "write_partitioned_parquet": ("parquet_writer", "write_partitioned_parquet"),
    "convert_raw_json_to_parquet": ("parquet_writer", "convert_raw_json_to_parquet"),
    "_articles_from_raw_json": ("parquet_writer", "_articles_from_raw_json"),
}


def __getattr__(name):
    """PEP 562 lazy attribute access.

    Chỉ import submodule khi caller thực sự dùng tới attr đó.
    Nếu submodule thiếu pandas, ImportError sẽ raise TẠI call site
    (không phải import time) — entry point khác không bị ảnh hưởng.
    """
    if name in _LAZY_EXPORTS:
        mod_name, attr_name = _LAZY_EXPORTS[name]
        from importlib import import_module
        module = import_module(f"{__name__}.{mod_name}")
        value = getattr(module, attr_name)
        globals()[name] = value  # cache cho lần sau
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # schema (eager)
    "ArticleSchema",
    "CrawlBatchSchema",
    # cleaner (eager)
    "clean_html",
    "is_advertisement",
    "extract_summary",
    "extract_lead_paragraph",
    # dedup (eager pure functions + lazy classes)
    "normalize_url",
    "content_hash",
    "Deduplicator",
    "FuzzyDeduplicator",
    # parquet (lazy)
    "write_partitioned_parquet",
    "convert_raw_json_to_parquet",
    # orchestrator (lazy)
    "Pipeline",
    "PipelineResult",
    "LayerStats",
    "get_pipeline",
]