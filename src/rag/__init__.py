"""
RAG module - Retrieval-Augmented Generation over crawled news.
"""
from .vector_store import VectorStore, build_store_from_parquet, DEFAULT_EMBED_MODEL
from .qa_chain import GeminiClient, RAGChain

__all__ = [
    "VectorStore",
    "build_store_from_parquet",
    "DEFAULT_EMBED_MODEL",
    "GeminiClient",
    "RAGChain",
]
