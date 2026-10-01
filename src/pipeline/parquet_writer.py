"""
Parquet writer - Converts raw JSON to partitioned Parquet (Hive-style layout).

Output layout:
  data/parquet/source=VNExpress/year=2026/month=09/day=15/part-*.parquet
"""
import json
import os
import glob
from datetime import datetime
from typing import List, Optional

import pandas as pd

from .schema import ArticleSchema


def _articles_from_raw_json(path: str) -> List[ArticleSchema]:
    """Load a raw JSON crawl file and normalize to ArticleSchema list."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_articles = data.get("articles", [])
    out = []
    for raw in raw_articles:
        try:
            url = raw.get("url", "").strip()
            if not url or not url.startswith(("http://", "https://")):
                continue
            source = raw.get("source", "Unknown") or "Unknown"
            title = raw.get("title", "") or ""
            desc = raw.get("description", "") or ""
            author = raw.get("author") or None
            category = raw.get("category") or None

            crawled_at_str = raw.get("crawled_at") or data.get("crawled_at")
            try:
                crawled_at = datetime.fromisoformat(crawled_at_str.replace("Z", "+00:00")) if crawled_at_str else datetime.utcnow()
            except (ValueError, AttributeError):
                crawled_at = datetime.utcnow()

            art = ArticleSchema(
                url=url,
                source=source,
                title=title,
                description=desc,
                content=raw.get("content", "") or "",
                author=author,
                category=category,
                published_date=raw.get("published_date"),
                crawled_at=crawled_at,
            ).derive_fields()

            if art.word_count >= 5 or art.has_title:
                out.append(art)
        except Exception:
            continue
    return out


def write_partitioned_parquet(
    articles: List[ArticleSchema],
    output_root: str = None,
) -> dict:
    """Write articles to Hive-partitioned parquet. Returns stats dict."""
    import os
    if output_root is None:
        base = Path(os.environ.get("DATA_DIR", "/app/data"))
        output_root = str(base / "parquet")
    if not articles:
        return {"written": 0, "partitions": 0}

    df = pd.DataFrame([a.dict() for a in articles])
    df["crawled_at"] = pd.to_datetime(df["crawled_at"], utc=True)
    df["year"] = df["crawled_at"].dt.year.astype(str)
    df["month"] = df["crawled_at"].dt.month.astype("Int64").astype(str).str.zfill(2)
    df["day"] = df["crawled_at"].dt.day.astype("Int64").astype(str).str.zfill(2)

    partitions_written = 0
    rows_written = 0

    for (source, year, month, day), group in df.groupby(["source", "year", "month", "day"], dropna=False):
        partition_dir = os.path.join(
            output_root, f"source={source}", f"year={year}", f"month={month}", f"day={day}"
        )
        os.makedirs(partition_dir, exist_ok=True)

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        out_file = os.path.join(partition_dir, f"part-{ts}.parquet")

        drop_cols = [c for c in ("year", "month", "day") if c in group.columns]
        group_clean = group.drop(columns=drop_cols)

        group_clean.to_parquet(out_file, engine="pyarrow", index=False)
        partitions_written += 1
        rows_written += len(group_clean)

    return {
        "written": rows_written,
        "partitions": partitions_written,
        "root": output_root,
    }


def convert_raw_json_to_parquet(
    raw_dir: str = "data/raw",
    output_root: str = None,
    use_dedup: bool = True,
) -> dict:
    """Read all raw JSON files, optionally dedupe, then write partitioned Parquet."""
    from .deduplicator import Deduplicator
    import os
    if output_root is None:
        base = Path(os.environ.get("DATA_DIR", "/app/data"))
        output_root = str(base / "parquet")

    raw_files = sorted(glob.glob(os.path.join(raw_dir, "raw_crawl_*.json")))
    if not raw_files:
        return {"written": 0, "partitions": 0, "files_processed": 0, "duplicates_removed": 0}

    all_articles: List[ArticleSchema] = []
    dedup = Deduplicator() if use_dedup else None
    dup_count = 0
    files_processed = 0

    for raw_file in raw_files:
        arts = _articles_from_raw_json(raw_file)
        if dedup:
            kept, dups = dedup.deduplicate(arts)
            dup_count += len(dups)
            all_articles.extend(kept)
        else:
            all_articles.extend(arts)
        files_processed += 1

    write_stats = write_partitioned_parquet(all_articles, output_root=output_root)

    return {
        **write_stats,
        "files_processed": files_processed,
        "duplicates_removed": dup_count,
        "total_in": len(all_articles),
    }


if __name__ == "__main__":
    import sys
    raw_dir = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
    out_root = sys.argv[2] if len(sys.argv) > 2 else "data/parquet"
    stats = convert_raw_json_to_parquet(raw_dir=raw_dir, output_root=out_root)
    print(json.dumps(stats, indent=2, default=str))
