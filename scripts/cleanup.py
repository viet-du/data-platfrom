"""
Data cleanup — auto-delete data older than N days across all storage layers.

Why this exists:
  Crawling is append-only by default. Within a week the project accumulates
  hundreds of MBs of parquet + raw JSON + vector embeddings from articles
  that are no longer relevant. For a Telegram-bot demo we don't need that
  history — we only ever query "last 48h" for the news digest. So the
  natural TTL is 7 days: keep a buffer for natural drops, never balloon.

Storage layers we clean:

  Layer 1 - Cold blob storage on disk
    - data/raw/*.json            raw crawls (oldest, biggest)
    - data/silver/*.json         cleaned + deduped
    - data/gold/*.json           final news-summaryed
    - data/logs/*.log            crawl log files
    - data/parquet/source=*/*    partitioned parquet
    - data/backups/*.tgz         compressed snapshots

  Layer 2 - Vector store (Chroma)
    - Query for chunks with crawled_at older than cutoff, then delete
      by id. Safer than reset() because it preserves the model state.

  Layer 3 - Drive snapshots (handled separately)
    - Drive has its own per-file TTL via the existing scheduler,
      or a separate /prune/Day command. We don't touch Drive here.

Safety:
  - Never deletes anything younger than max_age_days (default 7).
  - Logs every deletion to logger + returns counts for Telegram.
  - Continues on error per-layer; one failing layer doesn't block others.
  - Logs "would delete X bytes" if DRY_RUN=1, doesn't actually delete.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


# A date appears in many of our filenames. Recognise as many formats as
# possible so the cleanup is robust to slight differences between
# crawlers (some emit "_20260915_", others "2026-09-15").
_DATE_PATTERNS = [
    re.compile(r"(\d{4})(\d{2})(\d{2})"),       # 20260915
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),      # 2026-09-15
    re.compile(r"(\d{4})_(\d{2})_(\d{2})"),      # 2026_09_15
]


def _file_age_days(path: Path) -> int | None:
    """Best-effort age extraction:
      1. Try the date baked into the filename (preferred — survives
         accidentally restored files where mtime is now).
      2. Fall back to filesystem mtime.
    """
    for pat in _DATE_PATTERNS:
        m = pat.search(path.name)
        if m:
            try:
                d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                             tzinfo=timezone.utc)
                return (datetime.now(timezone.utc) - d).days
            except ValueError:
                continue
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return (datetime.now(timezone.utc) - mtime).days
    except OSError:
        return None


def _delete_older_than(root: Path, max_age_days: int, pattern: str = "*") -> Dict[str, int]:
    """Delete files under `root` whose date / mtime exceeds max_age_days.
    Returns {deleted_count, bytes_freed}.
    """
    deleted = 0
    bytes_freed = 0
    if not root.exists():
        return {"deleted": 0, "bytes": 0}
    dry_run = os.environ.get("CLEANUP_DRY_RUN") == "1"

    for path in root.rglob(pattern):
        if not path.is_file():
            continue
        age = _file_age_days(path)
        if age is None:
            continue
        if age < max_age_days:
            continue
        try:
            size = path.stat().st_size
            if dry_run:
                logger.info("[DRY_RUN] would delete %s (%d days old, %.1f KB)",
                            path, age, size / 1024)
            else:
                path.unlink()
                logger.info("Cleanup: deleted %s (%d days old, %.1f KB)",
                            path, age, size / 1024)
            deleted += 1
            bytes_freed += size
        except OSError as e:
            logger.warning("Cleanup: failed to delete %s: %s", path, e)

    return {"deleted": deleted, "bytes": bytes_freed}


def cleanup_old_parquet(data_dir: Path, max_age_days: int) -> Dict[str, int]:
    """Delete parquet partition files older than max_age_days.

    We delete whole partition dirs when ALL files inside are older
    than cutoff — that way we don't leave a half-empty
    source=VNExpress/year=2026/month=10/day=02 directory.
    """
    parquet_root = data_dir / "parquet"
    if not parquet_root.exists():
        return {"deleted": 0, "bytes": 0}
    deleted = 0
    bytes_freed = 0
    dry_run = os.environ.get("CLEANUP_DRY_RUN") == "1"

    # Walk leaf-most files and decide per-leaf whether the whole
    # partition day is old.
    for leaf in parquet_root.rglob("*.parquet"):
        if not leaf.is_file():
            continue
        age = _file_age_days(leaf)
        if age is None or age < max_age_days:
            continue
        # Treat the leaf directory (e.g. .../day=15) as the unit to drop.
        day_dir = leaf.parent
        # Make sure every parquet file in that day-dir is also old.
        siblings = list(day_dir.glob("*.parquet"))
        all_old = all(
            (_file_age_days(p) or 0) >= max_age_days for p in siblings
        )
        if not all_old:
            continue
        for p in siblings:
            try:
                size = p.stat().st_size
                if dry_run:
                    logger.info("[DRY_RUN] would delete %s", p)
                else:
                    p.unlink()
                deleted += 1
                bytes_freed += size
            except OSError as e:
                logger.warning("Cleanup: failed to delete %s: %s", p, e)
        # Best-effort: prune the day=* dir if it's now empty.
        try:
            if not dry_run and not any(day_dir.iterdir()):
                day_dir.rmdir()
        except OSError:
            pass

    return {"deleted": deleted, "bytes": bytes_freed}


def cleanup_rag_store(max_age_days: int) -> Dict[str, int]:
    """Delete RAG chunks whose crawled_at is older than max_age_days.

    Uses the metadata we store at insert time (crawled_at ISO string).
    Chroma doesn't support range-delete by metadata, so we collect IDs
    first via get(), then delete in one batch.
    """
    deleted = 0
    try:
        from src.rag.persistent_store import get_persistent_store
        store = get_persistent_store()
        store._ensure_loaded()
        coll = store._collection

        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
        all_ids = coll.get(include=["metadatas"]).get("ids", [])
        old_ids = [
            _id for _id, meta in zip(
                all_ids,
                coll.get(ids=all_ids, include=["metadatas"]).get("metadatas", []),
            )
            if (meta or {}).get("crawled_at", "") < cutoff
        ]
        if not old_ids:
            return {"deleted": 0, "bytes": 0}
        if os.environ.get("CLEANUP_DRY_RUN") == "1":
            logger.info("[DRY_RUN] would delete %d RAG chunks", len(old_ids))
        else:
            coll.delete(ids=old_ids)
        deleted = len(old_ids)
        logger.info("Cleanup: pruned %d RAG chunks older than %s days", deleted, max_age_days)
    except Exception as e:
        logger.warning("Cleanup: RAG pruning failed: %s", e)

    return {"deleted": deleted, "bytes": 0}


def cleanup_old_data(data_dir: Path = None, max_age_days: int = 7) -> Dict[str, int]:
    """Sweep all data layers. Returns {layer: {deleted, bytes}}."""
    if data_dir is None:
        try:
            from src.utils import DATA_DIR  # type: ignore
            data_dir = DATA_DIR  # noqa: F821
        except Exception:
            # Default to /app/data on Railway, ./data locally.
            data_dir = Path(os.environ.get("DATA_DIR", "/app/data"))
    data_dir = Path(data_dir)

    layers: Dict[str, Dict[str, int]] = {}

    # Layer 1: cold blob storage on disk.
    for sub_name, pattern in [
        ("raw", "*.json"),
        ("silver", "*.json"),
        ("gold", "*.json"),
        ("logs", "*.log"),
        ("summary", "*.json"),
        ("backups", "*.tgz"),
    ]:
        layers[sub_name] = _delete_older_than(data_dir / sub_name, max_age_days, pattern)

    # Layer 1b: parquet partitions (special: deletes whole day= dirs).
    layers["parquet"] = cleanup_old_parquet(data_dir, max_age_days)

    # Layer 2: vector store.
    layers["rag_store"] = cleanup_rag_store(max_age_days)

    total_deleted = sum(l["deleted"] for l in layers.values())
    total_bytes = sum(l["bytes"] for l in layers.values())

    logger.info(
        "Cleanup summary (max_age=%d days, dry_run=%s): %d files, %.1f KB freed",
        max_age_days,
        os.environ.get("CLEANUP_DRY_RUN") == "1",
        total_deleted,
        total_bytes / 1024,
    )
    logger.info("Per-layer: %s", {k: v["deleted"] for k, v in layers.items()})

    return {
        "total_deleted": total_deleted,
        "total_bytes": total_bytes,
        "layers": layers,
        "max_age_days": max_age_days,
    }


def format_cleanup_summary(result: Dict) -> str:
    """Pretty Telegram-friendly summary of a cleanup run."""
    lines = [f"🗑️ <b>Cleanup done</b> (max_age={result['max_age_days']}d)\n"]
    for layer, stats in result["layers"].items():
        if stats["deleted"]:
            lines.append(f"  • {layer}: {stats['deleted']} files ({stats['bytes'] / 1024:.1f} KB)")
    if result["total_deleted"] == 0:
        lines.append("  (nothing to delete)")
    else:
        lines.append(
            f"\n<b>Total:</b> {result['total_deleted']} files, "
            f"{result['total_bytes'] / 1024 / 1024:.2f} MB freed"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    summary = cleanup_old_data(max_age_days=days)
    print(format_cleanup_summary(summary))