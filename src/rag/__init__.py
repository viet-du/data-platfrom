"""Public API cho RAG (Retrieval-Augmented Generation).

Eager: chỉ những import nhẹ, không side-effect.
Lazy: mọi class/function nặng (VectorStore + RAG chain + helpers) qua
      PEP 562 __getattr__ — để tránh:
        1. Circular import khi entry point chỉ cần 1-2 class.
        2. ImportError khi sentence-transformers/chromadb chưa sẵn sàng.
        3. Boot race condition trên worker không deterministic.

Public API:
  Vector store (lazy — depends on sentence-transformers + chromadb):
    VectorStore, build_store_from_parquet, build_store_from_gold,
    DEFAULT_EMBED_MODEL
  QA chain (lazy — depends on google-generativeai):
    GeminiClient, RAGChain
"""
# Constant được định nghĩa sớm (lightweight — chỉ string).
DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_LAZY_EXPORTS = {
    # vector store
    "VectorStore": ("vector_store", "VectorStore"),
    "build_store_from_parquet": ("vector_store", "build_store_from_parquet"),
    "build_store_from_gold": ("vector_store", "build_store_from_gold"),
    # qa chain
    "GeminiClient": ("qa_chain", "GeminiClient"),
    "RAGChain": ("qa_chain", "RAGChain"),
}


def __getattr__(name):
    """PEP 562 lazy attribute access — chỉ load submodule khi cần."""
    if name in _LAZY_EXPORTS:
        mod_name, attr_name = _LAZY_EXPORTS[name]
        from importlib import import_module
        module = import_module(f"{__name__}.{mod_name}")
        value = getattr(module, attr_name)
        globals()[name] = value  # cache
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "VectorStore",
    "build_store_from_parquet",
    "build_store_from_gold",
    "DEFAULT_EMBED_MODEL",
    "GeminiClient",
    "RAGChain",
]