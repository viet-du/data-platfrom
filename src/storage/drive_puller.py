"""
Drive Puller — kéo JSON batches từ Google Drive về local theo cửa sổ thời gian
                    rồi đẩy vào Bronze/Silver/Gold pipeline.

Lý do tồn tại:
  Pipeline trên Railway free tier đẩy batch thẳng lên Drive (`GoogleDriveSink`)
  và không giữ local để tránh OOM. Nhưng RAG layer cần gold JSON để build
  vector index — và index đó là thứ user truy vấn qua /ask, /news. Nếu container
  khởi động với chroma trống, /ask trả "no relevant articles" cho đến khi
  snapshot RAG cũ được restore.

  Module này lấp khoảng trống bằng cách:
    1. Mỗi sáng (sau auto-crawl), liệt kê file .json trong folder Drive của
       từng nguồn, tải về /app/data/raw_pulled/<source>/.
    2. Mỗi file pulled là 1 Gold batch đã dedup — chuyển thành ArticleSchema
       rồi chạy Pipeline.process_batch() (Silver → Gold → Parquet → RAG index).
    3. Cuối ngày (sau daily report), xoá /app/data/raw_pulled và /app/data/parquet
       của "ngày hôm nay" để giải phóng volume. Drive vẫn giữ bản gốc.

  Idempotency: Pipeline đã có dedup ở cả Silver lẫn Gold, nên nếu pull
  trùng batch đã crawl thì không tạo record mới.

Hai chế độ:
  - sync_today():   pull + Pipeline.process_batch() + RAG reindex. Chạy sáng.
  - prune_local():  xoá /app/data/raw_pulled + /app/data/parquet cũ.
                    Chạy tối sau daily report.

Sinks:
  Chỉ làm việc khi có GOOGLE_DRIVE_CREDENTIALS(_PATH) hợp lệ. Nếu không, log
  cảnh báo và trả về dict ok=False để scheduler ghi vào digest.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# Folder local chứa JSON kéo về từ Drive. Tách riêng với /app/data/raw (Bronze
# của crawler) để cleanup không vô tình xoá Bronze thật. Sau khi pull, mỗi
# file được parse thành ArticleSchema rồi đẩy qua Pipeline → Silver/Gold/Index.
PULLED_RAW_SUBDIR = "raw_pulled"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _file_modified_after(drive_obj: Dict, max_age_hours: int) -> bool:
    """Lọc file Drive theo tuổi (so với thời điểm modifiedTime)."""
    modified = drive_obj.get("modifiedTime") or drive_obj.get("createdTime")
    if not modified:
        return True
    try:
        ts = datetime.fromisoformat(modified.replace("Z", "+00:00"))
    except ValueError:
        return True
    age_hours = (_now_utc() - ts).total_seconds() / 3600
    return age_hours <= max_age_hours


def _gold_batch_to_articles(payload, fallback_source: str) -> List:
    """Convert 1 payload (Gold batch từ Drive) → ArticleSchema list.

    Hỗ trợ 2 format:
      A. {"source": "...", "articles": [...]}      — schema cũ (raw batch từ crawler)
      B. Gold (list-of-record hoặc {"records": [...]}) — schema mới
    """
    from src.pipeline import ArticleSchema

    if isinstance(payload, list):
        records = payload
    else:
        records = payload.get("articles") or payload.get("records") or []

    out = []
    for r in records:
        try:
            url = (r.get("article_url") or r.get("url") or "").strip()
            if not url.startswith(("http://", "https://")):
                continue
            source = r.get("source_name") or r.get("source") or fallback_source
            title = r.get("title") or ""
            description = r.get("description") or ""
            # Trong Gold mới: content đã join title+desc+content.
            # Khi pull về, ta tách ngược: lấy `content` Gold làm `content`
            # (ArticleSchema validator sẽ clean_text lại — idempotent).
            content = r.get("content") or ""
            crawled_at_raw = r.get("crawled_at") or payload.get("crawled_at") if isinstance(payload, dict) else None
            crawled_at = None
            if crawled_at_raw:
                try:
                    crawled_at = datetime.fromisoformat(
                        str(crawled_at_raw).replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    crawled_at = None

            art = ArticleSchema(
                url=url,
                source=source,
                title=title,
                description=description,
                content=content,
                author=r.get("author"),
                category=r.get("category"),
                published_date=r.get("published_at") or r.get("published_date"),
                crawled_at=crawled_at or datetime.now(timezone.utc),
            ).derive_fields()
            out.append(art)
        except Exception as e:
            logger.warning("gold→article conversion failed: %s", e)
            continue
    return out


class DrivePuller:
    """Tải JSON batch từ Drive về local theo nguồn + cửa sổ thời gian."""

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        parent_folder_id: Optional[str] = None,
        max_age_hours: Optional[int] = None,
        max_files_per_source: Optional[int] = None,
        local_data_dir: Optional[str] = None,
    ):
        self.creds_path = (
            credentials_path
            or os.environ.get("GOOGLE_DRIVE_CREDENTIALS")
            or os.environ.get("GOOGLE_DRIVE_CREDENTIALS_PATH")
            or os.environ.get("GOOGLE_CREDENTIALS_PATH")
        )
        self.parent_folder_id = parent_folder_id or os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
        self.max_age_hours = int(
            max_age_hours
            if max_age_hours is not None
            else os.environ.get("PULL_TODAY_AGE_HOURS", "24")
        )
        self.max_files = int(
            max_files_per_source
            if max_files_per_source is not None
            else os.environ.get("PULL_TODAY_MAX_FILES", "20")
        )
        self.local_root = Path(
            local_data_dir or os.environ.get("DATA_DIR", "/app/data")
        )
        self.pulled_root = self.local_root / PULLED_RAW_SUBDIR
        self._service = None  # lazy

    # ---------- Drive plumbing ----------

    def _drive_service(self):
        if self._service is not None:
            return self._service
        if not self.creds_path or not Path(self.creds_path).exists():
            logger.warning(
                "DrivePuller: credentials not found at %s — pull disabled.",
                self.creds_path,
            )
            return None
        try:
            from src.services.google_drive_service import GoogleDriveService

            helper = GoogleDriveService(
                credentials_path=self.creds_path,
                folder_id=self.parent_folder_id,
                use_oauth=False,
            )
            self._service = helper.service
            return self._service
        except Exception as e:
            logger.error("DrivePuller: failed to init Drive service: %s", e)
            return None

    def _list_source_folder(self, source_name: str) -> Optional[str]:
        svc = self._drive_service()
        if not svc or not self.parent_folder_id:
            return None
        try:
            q = (
                f"'{self.parent_folder_id}' in parents and "
                f"name='{source_name}' and "
                f"mimeType='application/vnd.google-apps.folder' and "
                f"trashed=false"
            )
            results = (
                svc.files()
                .list(
                    q=q,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    fields="files(id, name)",
                )
                .execute()
            )
            files = results.get("files", [])
            if not files:
                return None
            return files[0]["id"]
        except Exception as e:
            logger.error("DrivePuller: list folder %s failed: %s", source_name, e)
            return None

    def _list_recent_jsons(self, folder_id: str) -> List[Dict]:
        svc = self._drive_service()
        if not svc:
            return []
        try:
            q = (
                f"'{folder_id}' in parents and "
                f"mimeType='application/json' and "
                f"trashed=false"
            )
            results = (
                svc.files()
                .list(
                    q=q,
                    pageSize=200,
                    orderBy="modifiedTime desc",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    fields="files(id, name, modifiedTime, size)",
                )
                .execute()
            )
            files = results.get("files", [])
            return [
                f for f in files
                if _file_modified_after(f, self.max_age_hours)
            ][: self.max_files]
        except Exception as e:
            logger.error("DrivePuller: list JSONs in %s failed: %s", folder_id, e)
            return []

    def _download_json(self, file_id: str, dest: Path) -> bool:
        svc = self._drive_service()
        if not svc:
            return False
        try:
            from googleapiclient.http import MediaIoBaseDownload
            import io

            fh = io.BytesIO()
            request = svc.files().get_media(fileId=file_id, supportsAllDrives=True)
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(fh.getvalue())
            return True
        except Exception as e:
            logger.error("DrivePuller: download %s failed: %s", file_id, e)
            return False

    # ---------- public API ----------

    def sync_today(self, sources: List[str], reindex: bool = False) -> Dict:
        """
        Kéo JSON batches của các nguồn trong `sources` từ Drive về local
        rồi đẩy qua Pipeline Bronze/Silver/Gold.

        Mỗi file JSON Drive (Gold batch) được parse thành ArticleSchema list
        rồi gọi Pipeline.process_batch(source=...) — Pipeline sẽ tự dedup
        chéo với data đã crawl trong ngày (cùng article_id → skip).

        Trả về:
          {
            "ok": bool,
            "reason": str (nếu !ok),
            "per_source": {source: {"files": N, "articles": N, "mb": float,
                                     "pipeline": {...}}},
            "downloaded": int,
            "skipped": int,
            "indexed": int,
          }
        """
        if not self._drive_service():
            return {"ok": False, "reason": "no_drive_credentials", "per_source": {}}

        from src.pipeline import get_pipeline
        pipeline = get_pipeline()

        per_source: Dict[str, Dict] = {}
        downloaded = 0
        skipped = 0
        indexed_total = 0

        for source in sources:
            folder_id = self._list_source_folder(source)
            if not folder_id:
                logger.info("DrivePuller: no Drive folder for %s — skip", source)
                per_source[source] = {"files": 0, "articles": 0, "mb": 0.0}
                continue

            files = self._list_recent_jsons(folder_id)
            if not files:
                per_source[source] = {"files": 0, "articles": 0, "mb": 0.0}
                continue

            source_dir = self.pulled_root / source
            source_dir.mkdir(parents=True, exist_ok=True)
            all_articles = []
            bytes_total = 0

            for f in files:
                dest = source_dir / f["name"]
                if dest.exists():
                    skipped += 1
                else:
                    if self._download_json(f["id"], dest):
                        downloaded += 1
                    else:
                        skipped += 1
                        continue
                # Parse ngay để đẩy vào pipeline (kể cả file đã cache).
                try:
                    payload = json.loads(dest.read_text(encoding="utf-8"))
                    bytes_total += dest.stat().st_size
                except (OSError, ValueError) as e:
                    logger.warning("DrivePuller: parse %s failed: %s", dest, e)
                    continue
                all_articles.extend(_gold_batch_to_articles(payload, fallback_source=source))

            # Đẩy qua Pipeline Bronze→Silver→Gold→Parquet (reindex tổng cuối).
            pipeline_stats = None
            if all_articles:
                try:
                    p_result = pipeline.process_batch(source=source, articles=all_articles)
                    pipeline_stats = p_result.as_dict()
                    indexed_total += p_result.indexed
                except Exception as e:
                    logger.error("DrivePuller: pipeline.process_batch(%s) failed: %s", source, e)
                    pipeline_stats = {"error": str(e)}

            per_source[source] = {
                "files": len(files),
                "articles": len(all_articles),
                "mb": round(bytes_total / (1024 * 1024), 2),
                "pipeline": pipeline_stats,
            }

        # Optional: reindex Chroma từ gold hôm nay (chỉ chạy 1 lần cuối).
        if reindex and indexed_total == 0:
            try:
                indexed_total = pipeline._reindex_chroma()
            except Exception as e:
                logger.warning("DrivePuller: post-sync reindex failed: %s", e)

        return {
            "ok": True,
            "per_source": per_source,
            "downloaded": downloaded,
            "skipped": skipped,
            "indexed": indexed_total,
        }

    def prune_local(self, keep_hours: Optional[int] = None) -> Dict:
        """
        Xoá JSON pulled và parquet local cũ hơn `keep_hours` để giải phóng volume.

        Mặc định `keep_hours` lấy từ `PULL_TODAY_KEEP_LOCAL_HOURS` (24h).
        Drive vẫn giữ bản gốc, chỉ xoá local.
        """
        keep_h = int(
            keep_hours
            if keep_hours is not None
            else os.environ.get("PULL_TODAY_KEEP_LOCAL_HOURS", "24")
        )
        cutoff = _now_utc() - timedelta(hours=keep_h)
        deleted_files = 0
        bytes_freed = 0

        for sub in (PULLED_RAW_SUBDIR, "parquet"):
            root = self.local_root / sub
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                try:
                    mtime = datetime.fromtimestamp(
                        path.stat().st_mtime, tz=timezone.utc
                    )
                except OSError:
                    continue
                if mtime >= cutoff:
                    continue
                try:
                    size = path.stat().st_size
                    path.unlink()
                    deleted_files += 1
                    bytes_freed += size
                except OSError as e:
                    logger.warning("DrivePuller: failed to delete %s: %s", path, e)

        # Xoá partition dir rỗng (chỉ áp dụng cho parquet vì hive-style).
        for day_dir in (self.local_root / "parquet").rglob("day=*"):
            try:
                if not any(day_dir.iterdir()):
                    day_dir.rmdir()
            except OSError:
                continue

        # Reset chroma index — embeddings giờ không match với data local nữa.
        # Nếu user muốn /ask tiếp, cần pull + reindex. Drive snapshot vẫn còn.
        chroma_dir = self.local_root / "chroma"
        chroma_cleared = False
        if chroma_dir.exists():
            try:
                shutil.rmtree(chroma_dir)
                chroma_cleared = True
            except OSError as e:
                logger.warning("DrivePuller: failed to clear chroma: %s", e)

        return {
            "ok": True,
            "deleted_files": deleted_files,
            "bytes_freed_mb": round(bytes_freed / (1024 * 1024), 2),
            "chroma_cleared": chroma_cleared,
            "keep_hours": keep_h,
        }


_puller: Optional[DrivePuller] = None


def get_drive_puller() -> DrivePuller:
    """Singleton factory — tránh rebuild GoogleDriveService nhiều lần."""
    global _puller
    if _puller is None:
        _puller = DrivePuller()
    return _puller
