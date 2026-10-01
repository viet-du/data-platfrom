"""
Vector Store - ChromaDB-backed embeddings index for RAG.

Uses sentence-transformers multilingual MiniLM (384 dim) for Vietnamese.
"""
import os
from typing import List, Optional, Dict, Any

from src.pipeline.schema import ArticleSchema


DEFAULT_EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_COLLECTION = "vietnamese_news"


class VectorStore:
    """ChromaDB wrapper with multilingual embeddings."""

    def __init__(
        self,
        persist_dir: str = "data/chroma",
        collection_name: str = DEFAULT_COLLECTION,
        embedding_model: str = DEFAULT_EMBED_MODEL,
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        self._client = None
        self._collection = None
        self._embedder = None

    def _ensure_loaded(self):
        if self._client is not None:
            return
        os.makedirs(self.persist_dir, exist_ok=True)

        # Disable chromadb telemetry (requires opentelemetry with newer protobuf)
        os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

        import chromadb
        from chromadb.config import Settings

        self._client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # Load embedder (lazy to avoid heavy import at startup)
        from sentence_transformers import SentenceTransformer
        self._embedder = SentenceTransformer(self.embedding_model_name)

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self._embed_texts,
            metadata={"hnsw:space": "cosine"},
        )

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        self._ensure_loaded()
        vecs = self._embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [v.tolist() for v in vecs]

    @property
    def count(self) -> int:
        self._ensure_loaded()
        return self._collection.count()

    def _doc_text(self, article: ArticleSchema) -> str:
        parts = [article.title.strip(), article.description.strip(), article.content.strip()]
        return " | ".join(p for p in parts if p)[:3000]

    def add_articles(self, articles: List[ArticleSchema], batch_size: int = 64) -> Dict[str, int]:
        """Add articles to the index. Returns {added, skipped}."""
        self._ensure_loaded()

        if not articles:
            return {"added": 0, "skipped": 0}

        added = 0
        skipped = 0

        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            ids = [a.article_id for a in batch]
            texts = [self._doc_text(a) for a in batch]

            existing = set()
            try:
                got = self._collection.get(ids=ids)
                existing = set(got.get("ids", []))
            except Exception:
                pass

            new_ids, new_texts, new_metas = [], [], []
            for a, t in zip(batch, texts):
                if a.article_id in existing or not t.strip():
                    skipped += 1
                    continue
                new_ids.append(a.article_id)
                new_texts.append(t)
                new_metas.append({
                    "url": a.url,
                    "source": a.source,
                    "title": a.title[:200],
                    "category": a.category or "",
                    "crawled_at": a.crawled_at.isoformat() if a.crawled_at else "",
                    "word_count": a.word_count,
                })

            if new_ids:
                self._collection.add(ids=new_ids, documents=new_texts, metadatas=new_metas)
                added += len(new_ids)

        return {"added": added, "skipped": skipped}

    def query(self, question: str, top_k: int = 5, source_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return top-k relevant articles for a question."""
        self._ensure_loaded()

        where = {"source": source_filter} if source_filter else None

        result = self._collection.query(
            query_texts=[question],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        for i, doc_id in enumerate(result.get("ids", [[]])[0]):
            meta = result.get("metadatas", [[]])[0][i]
            dist = result.get("distances", [[]])[0][i]
            doc = result.get("documents", [[]])[0][i]
            hits.append({
                "id": doc_id,
                "score": 1.0 - dist,  # cosine: 0 = identical
                "metadata": meta,
                "text": doc,
            })
        return hits

    def reset(self):
        self._ensure_loaded()
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.create_collection(
            name=self.collection_name,
            embedding_function=self._embed_texts,
            metadata={"hnsw:space": "cosine"},
        )


def build_store_from_parquet(parquet_root: str = "data/parquet") -> VectorStore:
    """Load all partitioned parquet into a new VectorStore."""
    import glob
    import pandas as pd
    from datetime import datetime

    store = VectorStore()
    files = sorted(glob.glob(os.path.join(parquet_root, "**", "*.parquet"), recursive=True))
    if not files:
        return store

    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)

    articles = []
    for _, row in df.iterrows():
        try:
            crawled_at = row.get("crawled_at")
            if hasattr(crawled_at, "to_pydatetime"):
                crawled_at = crawled_at.to_pydatetime()
            elif isinstance(crawled_at, str):
                crawled_at = datetime.fromisoformat(crawled_at.replace("Z", "+00:00"))

            art = ArticleSchema(
                url=row["url"],
                source=row["source"],
                title=str(row.get("title", "") or ""),
                description=str(row.get("description", "") or ""),
                content=str(row.get("content", "") or ""),
                author=row.get("author") if not pd.isna(row.get("author")) else None,
                category=row.get("category") if not pd.isna(row.get("category")) else None,
                crawled_at=crawled_at if crawled_at else datetime.utcnow(),
            ).derive_fields()
            articles.append(art)
        except Exception:
            continue

    stats = store.add_articles(articles)
    return store, stats


if __name__ == "__main__":
    import json as json_mod

    store, stats = build_store_from_parquet()
    print(json_mod.dumps({"indexed": stats, "total_in_store": store.count}, indent=2, default=str))
