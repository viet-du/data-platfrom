"""
Vector Store - ChromaDB-backed embeddings index for RAG.

Uses sentence-transformers multilingual MiniLM (384 dim) for Vietnamese.
"""
import os
import gc
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.pipeline.schema import ArticleSchema


# Lightweight embedder for 512 MB environments: MiniLM-L6 (22 MB on disk,
# ~80 MB resident) instead of multilingual L12 (~470 MB resident).
DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_COLLECTION = "vietnamese_news"


class VectorStore:
    """ChromaDB wrapper with multilingual embeddings."""

    def __init__(
        self,
        persist_dir: str = None,
        collection_name: str = DEFAULT_COLLECTION,
        embedding_model: str = DEFAULT_EMBED_MODEL,
    ):
        import os
        if persist_dir is None:
            base = Path(os.environ.get("DATA_DIR", "/app/data"))
            persist_dir = str(base / "chroma")
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
        self._embedder = SentenceTransformer(self.embedding_model_name, device="cpu")

        # NOTE: do NOT pass `embedding_function` to get_or_create_collection.
        # chromadb 0.5.x validates it against the EmbeddingFunction protocol
        # (must have name(), is_legacy(), __call__(input)). Passing
        # `self._embed_texts` raises:
        #   ValueError: Embedding function must implement __call__ method
        # We compute embeddings ourselves and pass `embeddings=` to add().
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        self._ensure_loaded()
        vecs = self._embedder.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=16,  # small batch to keep RAM under 512 MB
        )
        result = [v.tolist() for v in vecs]
        # Free intermediate tensors so we don't accumulate in 512 MB envs.
        del vecs
        gc.collect()
        return result

    @property
    def count(self) -> int:
        self._ensure_loaded()
        return self._collection.count()

    def _doc_text(self, article: ArticleSchema) -> str:
        parts = [article.title.strip(), article.description.strip(), article.content.strip()]
        return " | ".join(p for p in parts if p)[:3000]

    def add_articles(self, articles: List[ArticleSchema], batch_size: int = 16) -> Dict[str, int]:
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
                # Pre-compute embeddings since collection has no embedding_function.
                new_embeddings = self._embed_texts(new_texts)
                self._collection.add(
                    ids=new_ids,
                    documents=new_texts,
                    metadatas=new_metas,
                    embeddings=new_embeddings,
                )
                added += len(new_ids)
            # Aggressively free memory after every batch so we stay under
            # 512 MB during long indexing runs.
            gc.collect()

        return {"added": added, "skipped": skipped}

    def query(self, question: str, top_k: int = 5, source_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return top-k relevant articles for a question."""
        self._ensure_loaded()

        where = {"source": source_filter} if source_filter else None

        # Pre-compute query embedding; pass via query_embeddings= (not query_texts=)
        # because the collection has no embedding_function.
        query_embedding = self._embed_texts([question])

        result = self._collection.query(
            query_embeddings=query_embedding,
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
        # No embedding_function here either; we embed at call time.
        self._collection = self._client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )


def build_store_from_parquet(parquet_root: str = None) -> VectorStore:
    """Load all partitioned parquet into a new VectorStore.

    NOTE: kept for backward-compat with /index. New code should prefer
    `build_store_from_gold()` because the Gold layer is the single
    source of truth (Silver + dedup + content-fingerprint hash).
    """
    import os
    import glob
    import pandas as pd
    from datetime import datetime

    if parquet_root is None:
        base = Path(os.environ.get("DATA_DIR", "/app/data"))
        parquet_root = str(base / "parquet")

    store = VectorStore()
    files = sorted(glob.glob(os.path.join(parquet_root, "**", "*.parquet"), recursive=True))
    if not files:
        # Return the same (store, stats) tuple shape callers expect, even
        # when there's nothing to index — otherwise downstream
        # `store, stats = build_store_from_parquet()` fails with
        # "cannot unpack non-iterable VectorStore object".
        return store, {"added": 0, "skipped": 0}

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


def build_store_from_gold(gold_path) -> int:
    """Load Gold records from a single gold_YYYYMMDD.json file into Chroma.

    Returns number of vectors added.

    Gold is the canonical RAG-ready layer — title+description+content already
    joined, dedup'd by article_hash, and 1 record per article (vs Silver which
    can have multiple revisions per day). Reading from Gold here means the
    RAG index is always consistent with what `process_batch()` wrote.

    Why not call add_articles(): Gold records are flat dicts (not ArticleSchema)
    and we want the same `metadata` schema that downstream RAG query code
    already reads.
    """
    from pathlib import Path
    import json

    gold_path = Path(gold_path)
    if not gold_path.exists():
        logger.info("build_store_from_gold: %s not found", gold_path)
        return 0
    try:
        records = json.loads(gold_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        logger.error("build_store_from_gold: read %s failed: %s", gold_path, e)
        return 0

    if not records:
        return 0

    store = VectorStore()
    store._ensure_loaded()

    # Idempotency: skip ids already in the collection.
    wanted_ids = [r["article_id"] for r in records if r.get("article_id")]
    already = set()
    if wanted_ids:
        try:
            got = store._collection.get(ids=wanted_ids)
            already = set(got.get("ids", []))
        except Exception:
            already = set()

    new_ids: List[str] = []
    new_texts: List[str] = []
    new_metas: List[Dict] = []
    for r in records:
        rid = r.get("article_id")
        if not rid or rid in already:
            continue
        text = r.get("content") or ""
        if not text.strip():
            continue
        new_ids.append(rid)
        new_texts.append(text[:3000])
        new_metas.append({
            "url": r.get("article_url", ""),
            "source": r.get("source_name", ""),
            "title": (r.get("title") or "")[:200],
            "category": r.get("category") or "",
            "crawled_at": r.get("crawled_at") or "",
            "word_count": r.get("word_count", 0),
        })

    if not new_ids:
        return 0

    # Embed in small batches (sentence-transformers + 512 MB container).
    BATCH = 16
    added = 0
    for i in range(0, len(new_ids), BATCH):
        batch_ids = new_ids[i:i + BATCH]
        batch_texts = new_texts[i:i + BATCH]
        batch_metas = new_metas[i:i + BATCH]
        try:
            vecs = store._embed_texts(batch_texts)
        except Exception as e:
            logger.error("build_store_from_gold: embed batch %d failed: %s", i, e)
            continue
        store._collection.add(
            ids=batch_ids,
            documents=batch_texts,
            metadatas=batch_metas,
            embeddings=vecs,
        )
        added += len(batch_ids)
        import gc
        gc.collect()
    logger.info(
        "build_store_from_gold: %s → +%d vectors (total in store: %d)",
        gold_path.name, added, store.count,
    )
    return added


if __name__ == "__main__":
    import json as json_mod

    store, stats = build_store_from_parquet()
    print(json_mod.dumps({"indexed": stats, "total_in_store": store.count}, indent=2, default=str))
