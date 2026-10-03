"""
Pipeline orchestrator — Bronze → Silver → Gold → Parquet (RAG-ready).

Tại sao cần file này:
  Trước đây code có đủ 3 lớp thư mục (raw/, silver/, gold/) và đủ 3 class
  (cleaner, deduplicator, parquet_writer) nhưng không có file nào nối
  chúng thành một flow. Các entry point (crawl, Drive pull, /index) tự
  gọi từng class rời rạc → dễ lệch schema, dễ quên bước dedup hoặc
  quên RAG reindex.

  Module này là single source of truth:

    crawl_batch(articles)                 # ArticleSchema list từ crawler
      → Bronze:  append vào /app/data/raw/raw_crawl_<date>_<ts>.json
      → Silver:  dedup + clean → /app/data/silver/silver_<date>.json
                 (append-only trong ngày, hashset từ silver_<date>_hashes.json)
      → Gold:    RAG-ready record → /app/data/gold/gold_<date>.json
                 (append-only trong ngày, hashset gold_<date>_hashes.json)
      → Parquet: partitioned write → /app/data/parquet/source=X/year=Y/...
      → Index:   (optional) refresh Chroma từ Gold JSON

  Tất cả entry point gọi `Pipeline.process_batch()` thay vì tự xử lý.

Schema rõ ràng:
  Bronze:  {source, crawled_at, total_articles, valid_articles, articles: [ArticleSchema, ...]}
  Silver:  list of {
             source, url, article_id (=sha256(url)[:16]),
             title, description, content (cleaned), author, category,
             published_date, crawled_at, language, word_count,
             bronze_file, processed_at
           }
  Gold:    list of {
             source_name, source_id, article_url, article_hash (=sha256(url|cat)),
             title, description, content (joined text), author, category, tags,
             published_at, crawled_at, processed_at, content_length, word_count
           }
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .schema import ArticleSchema, CrawlBatchSchema
from .cleaner import clean_html, is_advertisement

try:
    from .deduplicator import Deduplicator, normalize_url, content_hash
except ImportError as _e:
    # Không block việc load module — chỉ các hàm dedup mới fail.
    logger.warning("deduplicator import failed: %s — dedup features disabled", _e)
    Deduplicator = None  # type: ignore
    normalize_url = None  # type: ignore
    content_hash = None  # type: ignore

logger = logging.getLogger(__name__)


# ---------- helpers ----------

def _data_root() -> Path:
    return Path(os.environ.get("DATA_DIR", "/app/data"))


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> list:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        logger.warning("read_json(%s) failed: %s", path, e)
        return []


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


# ---------- stats ----------

@dataclass
class LayerStats:
    written: int = 0
    skipped: int = 0
    duplicates: int = 0
    rejected: int = 0
    bytes: int = 0

    def as_dict(self) -> Dict:
        return {
            "written": self.written,
            "skipped": self.skipped,
            "duplicates": self.duplicates,
            "rejected": self.rejected,
            "bytes": self.bytes,
        }


@dataclass
class PipelineResult:
    source: str
    bronze: LayerStats = field(default_factory=LayerStats)
    silver: LayerStats = field(default_factory=LayerStats)
    gold: LayerStats = field(default_factory=LayerStats)
    parquet: LayerStats = field(default_factory=LayerStats)
    indexed: int = 0
    ok: bool = True
    error: Optional[str] = None

    def as_dict(self) -> Dict:
        return {
            "source": self.source,
            "ok": self.ok,
            "error": self.error,
            "bronze": self.bronze.as_dict(),
            "silver": self.silver.as_dict(),
            "gold": self.gold.as_dict(),
            "parquet": self.parquet.as_dict(),
            "indexed": self.indexed,
        }


# ---------- the orchestrator ----------

class Pipeline:
    """
    Bronze/Silver/Gold orchestrator.

    Dùng cùng một dedup set cho Silver + Gold trong ngày để tránh tạo
    bản ghi trùng khi crawler chạy nhiều lần/ngày. Hashset được lưu
    cạnh JSON chính (silver_YYYYMMDD_hashes.json, gold_YYYYMMDD_hashes.json)
    để re-load được qua các process restart.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.root = Path(data_dir) if data_dir else _data_root()
        self.bronze_dir = self.root / "raw"
        self.silver_dir = self.root / "silver"
        self.gold_dir = self.root / "gold"
        self.parquet_dir = self.root / "parquet"
        for d in (self.bronze_dir, self.silver_dir, self.gold_dir, self.parquet_dir):
            d.mkdir(parents=True, exist_ok=True)

    # ----- Bronze: append raw batch -----

    def write_bronze(self, source: str, articles: List[ArticleSchema]) -> Tuple[Path, LayerStats]:
        """Ghi Bronze JSON: lưu trữ schema đầy đủ để replay/debug."""
        stats = LayerStats()
        if not articles:
            return Path(), stats
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = self.bronze_dir / f"raw_crawl_{ts}.json"
        batch = CrawlBatchSchema(
            source=source,
            crawled_at=datetime.now(timezone.utc),
            total_articles=len(articles),
            valid_articles=len(articles),
            invalid_articles=0,
            articles=articles,
        )
        payload = json.loads(batch.json())
        _write_json(out_path, payload)
        stats.written = len(articles)
        stats.bytes = out_path.stat().st_size
        logger.info("Bronze: wrote %d articles to %s", len(articles), out_path.name)
        return out_path, stats

    # ----- Silver: clean + dedup + canonicalize -----

    @staticmethod
    def _to_silver_record(art: ArticleSchema, bronze_file: str) -> Dict:
        """Convert ArticleSchema → Silver dict (canonical names)."""
        return {
            "source": art.source,
            "url": art.url,
            "article_id": ArticleSchema.compute_id(art.url),
            "title": art.title,
            "description": art.description,
            "content": art.content,  # ArticleSchema validator đã clean_text sẵn
            "author": art.author,
            "category": art.category,
            "published_date": art.published_date,
            "crawled_at": art.crawled_at.isoformat() if art.crawled_at else None,
            "language": art.language,
            "word_count": art.word_count,
            "has_title": art.has_title,
            "bronze_file": Path(bronze_file).name if bronze_file else None,
            "processed_at": _now_iso(),
        }

    def write_silver(
        self, articles: List[ArticleSchema], bronze_file: Optional[Path] = None
    ) -> LayerStats:
        """Append Silver records cho ngày hiện tại (dedup theo article_id)."""
        stats = LayerStats()
        if not articles:
            return stats
        today = _today_str()
        silver_path = self.silver_dir / f"silver_{today}.json"
        hash_path = self.silver_dir / f"silver_{today}_hashes.json"

        # Load existing day's records + hash set.
        existing = _read_json(silver_path)
        seen: set = set(_read_json(hash_path))

        dedup = Deduplicator()
        dedup.seen_urls = {normalize_url(r["url"]) for r in existing}
        dedup.seen_fingerprints = {
            content_hash(r["title"], r["description"], r["content"]) for r in existing
        }

        kept: List[Dict] = []
        for art in articles:
            art.derive_fields()
            # Lọc quảng cáo / rác.
            if is_advertisement(art.content, art.title):
                stats.rejected += 1
                continue
            if art.word_count < 5 and not art.has_title:
                stats.rejected += 1
                continue
            is_new, reason = dedup.add(art)
            if not is_new:
                stats.duplicates += 1
                continue
            record = self._to_silver_record(art, str(bronze_file or ""))
            kept.append(record)
            seen.add(record["article_id"])
            stats.written += 1

        if kept:
            existing.extend(kept)
            _write_json(silver_path, existing)
            _write_json(hash_path, sorted(seen))
            stats.bytes = silver_path.stat().st_size
            logger.info(
                "Silver: +%d records, total today=%d (file=%s)",
                stats.written, len(existing), silver_path.name,
            )
        else:
            stats.skipped = len(articles)
        return stats

    # ----- Gold: RAG-ready record -----

    @staticmethod
    def _to_gold_record(silver: Dict) -> Dict:
        """Convert Silver record → Gold (RAG-ready, joined text)."""
        content_joined = " ".join(
            filter(None, [silver.get("title"), silver.get("description"), silver.get("content")])
        ).strip()
        # article_hash dùng để dedup gold và làm id phụ cho RAG.
        url = silver["url"]
        cat = silver.get("category") or ""
        article_hash = hashlib.sha256(f"{url}|{cat}".encode("utf-8")).hexdigest()
        return {
            "source_id": silver["source"].lower().replace(" ", ""),
            "source_name": silver["source"],
            "article_url": silver["url"],
            "article_hash": article_hash,
            "article_id": silver["article_id"],
            "title": silver["title"],
            "description": silver["description"],
            "content": content_joined,
            "author": silver.get("author"),
            "category": silver.get("category"),
            "tags": [],  # reserved cho future tags extraction
            "published_at": silver.get("published_date"),
            "crawled_at": silver.get("crawled_at"),
            "processed_at": silver.get("processed_at"),
            "content_length": len(content_joined),
            "word_count": silver.get("word_count", 0),
        }

    def write_gold(self, silver_day: Optional[str] = None) -> LayerStats:
        """Đọc Silver của ngày `silver_day` (default hôm nay) → append Gold cùng ngày.

        Idempotent: chạy lại với cùng silver_day sẽ không tạo record trùng.
        """
        stats = LayerStats()
        day = silver_day or _today_str()
        silver_path = self.silver_dir / f"silver_{day}.json"
        gold_path = self.gold_dir / f"gold_{day}.json"
        gold_hash_path = self.gold_dir / f"gold_{day}_hashes.json"

        silver_records = _read_json(silver_path)
        if not silver_records:
            logger.info("Gold: silver_%s.json empty, skip", day)
            return stats

        existing = _read_json(gold_path)
        seen_hashes: set = set(_read_json(gold_hash_path))

        kept: List[Dict] = []
        for s in silver_records:
            gold = self._to_gold_record(s)
            if gold["article_hash"] in seen_hashes:
                stats.skipped += 1
                continue
            seen_hashes.add(gold["article_hash"])
            kept.append(gold)
            stats.written += 1

        if kept:
            existing.extend(kept)
            _write_json(gold_path, existing)
            _write_json(gold_hash_path, sorted(seen_hashes))
            stats.bytes = gold_path.stat().st_size
            logger.info(
                "Gold: +%d records, total today=%d (file=%s)",
                stats.written, len(existing), gold_path.name,
            )
        return stats

    # ----- Parquet: RAG-friendly columnar -----

    def write_parquet(self, gold_day: Optional[str] = None) -> LayerStats:
        """Convert Gold ngày `gold_day` → partitioned Parquet (source=X/year=Y/...).

        Dùng cho RAG/analytics downstream. Idempotent theo partition day.
        Trả về LayerStats với written=0 + error nếu pandas không có sẵn
        (cho phép test môi trường không cài pandas).
        """
        stats = LayerStats()
        day = gold_day or _today_str()
        gold_path = self.gold_dir / f"gold_{day}.json"
        gold_records = _read_json(gold_path)
        if not gold_records:
            logger.info("Parquet: gold_%s.json empty, skip", day)
            return stats

        try:
            import pandas as pd
        except ImportError as e:
            logger.warning(
                "Parquet: pandas not available (%s) — skip parquet step. "
                "Bronze/Silver/Gold đã ghi xong, RAG vẫn dùng được từ Gold.",
                e,
            )
            stats.written = 0
            return stats

        df = pd.DataFrame(gold_records)
        if "crawled_at" not in df.columns:
            logger.warning("Parquet: gold records missing crawled_at, skip")
            return stats
        df["crawled_at"] = pd.to_datetime(df["crawled_at"], errors="coerce", utc=True)
        df["year"] = df["crawled_at"].dt.year.astype("Int64").astype(str)
        df["month"] = df["crawled_at"].dt.month.astype("Int64").astype(str).str.zfill(2)
        df["day"] = df["crawled_at"].dt.day.astype("Int64").astype(str).str.zfill(2)

        rows_written = 0
        for (source, year, month, day_part), group in df.groupby(
            ["source_name", "year", "month", "day"], dropna=True
        ):
            partition = self.parquet_dir / f"source={source}" / f"year={year}" / f"month={month}" / f"day={day_part}"
            partition.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            out_file = partition / f"part-{ts}.parquet"
            group.drop(columns=["year", "month", "day"]).to_parquet(
                out_file, engine="pyarrow", index=False
            )
            rows_written += len(group)
            stats.written += len(group)
            stats.bytes += out_file.stat().st_size
        logger.info("Parquet: %d rows written for %s", rows_written, day)
        return stats

    # ----- the public entry point -----

    def process_batch(
        self,
        source: str,
        articles: List[ArticleSchema],
        reindex: bool = False,
    ) -> PipelineResult:
        """
        Single entry point: Bronze → Silver → Gold → Parquet → (optional reindex).

        Args:
            source: tên nguồn (VNExpress, DanTri, ...)
            articles: list ArticleSchema từ crawler
            reindex: True → sau khi write xong, refresh Chroma từ Gold ngày hôm nay

        Returns:
            PipelineResult với stats cho từng layer.
        """
        result = PipelineResult(source=source)
        try:
            bronze_path, result.bronze = self.write_bronze(source, articles)
            result.silver = self.write_silver(articles, bronze_file=bronze_path)
            result.gold = self.write_gold()
            result.parquet = self.write_parquet()

            if reindex:
                result.indexed = self._reindex_chroma()
        except Exception as e:
            logger.exception("process_batch failed for %s", source)
            result.ok = False
            result.error = str(e)
        return result

    # ----- RAG index helper -----

    def _reindex_chroma(self) -> int:
        """Refresh Chroma từ Gold records của ngày hôm nay.

        Thay vì đọc parquet (cần pandas), đọc thẳng gold_YYYYMMDD.json
        cho nhẹ. Dùng ArticleSchema để build embeddings.
        """
        from src.rag import build_store_from_gold

        day = _today_str()
        return build_store_from_gold(self.gold_dir / f"gold_{day}.json")

    # ----- rebuild từ scratch (cho /index command) -----

    def rebuild_index(self) -> Dict:
        """Build lại Chroma từ TẤT CẢ gold_*.json (dùng cho /index)."""
        from src.rag import build_store_from_gold

        total = 0
        for path in sorted(self.gold_dir.glob("gold_*.json")):
            if path.name.endswith("_hashes.json"):
                continue
            n = build_store_from_gold(path)
            total += n
        return {"indexed": total, "files": len(list(self.gold_dir.glob("gold_*.json")))}


# Singleton — tránh recreate nhiều lần.
_pipeline: Optional[Pipeline] = None


def get_pipeline() -> Pipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = Pipeline()
    return _pipeline
