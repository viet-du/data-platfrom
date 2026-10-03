"""
Cloud Sink — abstracts where crawled data ends up.

Why this exists: the user wants a "cloud-first" pipeline where the
running container never accumulates more than a tiny buffer of state.
Whether the destination is Drive, S3, or Databricks Volume, the
crawler should call the same `sink.write_batch(...)` interface.

Add a new backend (S3, GCS, Databricks Volume) by implementing
`CloudSink.write_batch` and `CloudSink.health_check`.
"""
from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


class CloudSink(ABC):
    """Abstract destination for crawled batches."""

    name: str = "abstract"

    @abstractmethod
    def write_batch(self, source: str, articles: List[Dict[str, Any]]) -> Optional[str]:
        """Persist a batch of articles. Returns the destination id/path."""

    @abstractmethod
    def write_payload(self, source: str, payload: Dict[str, Any], filename: str) -> Optional[str]:
        """Persist an already-built payload (e.g. Gold JSON from the
        Bronze/Silver/Gold pipeline). Symmetric with write_batch so
        callers can switch sink backends without changing call sites."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the sink is reachable."""


class GoogleDriveSink(CloudSink):
    """Stream batches directly into Drive under a per-source folder.

    Why: a free Railway container only has 512 MB of RAM and no persistent
    disk between deploys. Saving JSON to /app/data first then uploading
    later leaves bytes on the container that we don't actually need
    once Drive has them. This sink writes straight to Drive and
    returns the file id so the caller can log it.
    """

    name = "drive"

    def __init__(self, credentials_path: str, parent_folder_id: Optional[str] = None):
        self.credentials_path = credentials_path
        self.parent_folder_id = parent_folder_id or os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
        self._service = None
        self._folder_cache: Dict[str, str] = {}

    def _get_service(self):
        if self._service is None:
            from src.services.google_drive_service import GoogleDriveService
            self._service = GoogleDriveService(
                credentials_path=self.credentials_path,
                folder_id=self.parent_folder_id,
                use_oauth=False,
            )
        return self._service.service

    def _ensure_folder(self, name: str) -> Optional[str]:
        if name in self._folder_cache:
            return self._folder_cache[name]
        svc = self._get_service()
        try:
            from src.services.google_drive_service import GoogleDriveService
            from googleapiclient.errors import HttpError
            helper = GoogleDriveService(
                credentials_path=self.credentials_path,
                folder_id=self.parent_folder_id,
                use_oauth=False,
            )
            folder_id = helper.create_folder(name, self.parent_folder_id)
        except HttpError as e:
            logger.error("Drive folder lookup failed for %s: %s", name, e)
            return None
        if folder_id:
            self._folder_cache[name] = folder_id
        return folder_id

    def write_batch(self, source: str, articles: List[Dict[str, Any]]) -> Optional[str]:
        if not articles:
            return None
        from googleapiclient.http import MediaIoBaseUpload
        from googleapiclient.errors import HttpError
        import io

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        payload = {
            "source": source,
            "crawled_at": datetime.utcnow().isoformat(),
            "article_count": len(articles),
            "articles": articles,
        }
        return self._upload_json(source, payload, f"{source}_{ts}.json")

    def write_payload(self, source: str, payload: Dict[str, Any], filename: str) -> Optional[str]:
        """Upload an already-built payload (e.g. Gold JSON) under the
        per-source folder. Returns the file id or None on failure.

        Why this exists: with the Bronze/Silver/Gold pipeline, the
        Gold file is already written locally by Pipeline.write_gold().
        We want to push that file to Drive as-is (with dedup hash) so
        downstream RAG restore / external consumers see the same data.
        """
        if not payload:
            return None
        return self._upload_json(source, payload, filename)

    def _upload_json(self, source: str, payload: Dict[str, Any], filename: str) -> Optional[str]:
        from googleapiclient.http import MediaIoBaseUpload
        from googleapiclient.errors import HttpError
        import io

        svc = self._get_service()
        if not svc:
            return None
        folder_id = self._ensure_folder(source)
        if not folder_id:
            return None

        body_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        media = MediaIoBaseUpload(
            io.BytesIO(body_bytes),
            mimetype="application/json",
            resumable=False,
        )
        file_meta = {"name": filename, "parents": [folder_id]}
        try:
            created = svc.files().create(
                body=file_meta,
                media_body=media,
                fields="id",
                supportsAllDrives=True,
            ).execute()
            file_id = created.get("id")
            logger.info(
                "Drive upload OK: %s/%s (%d records, file id=%s)",
                source, filename, len(payload) if isinstance(payload, list) else payload.get("article_count", "?"),
                file_id,
            )
            return file_id
        except HttpError as e:
            logger.error(
                "Drive upload FAILED HttpError %s: %s",
                e.resp.status,
                e._get_reason(),
            )
            return None

    def health_check(self) -> bool:
        try:
            self._get_service()
            return True
        except Exception as e:
            logger.warning("Drive health check failed: %s", e)
            return False


class LocalJsonSink(CloudSink):
    """Fallback sink: write JSON to a local directory.

    Only used when no cloud destination is configured or as a debugging
    fallback on the dev machine.
    """

    name = "local"

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)

    def write_batch(self, source: str, articles: List[Dict[str, Any]]) -> Optional[str]:
        if not articles:
            return None
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_dir = self.base_dir / "raw" / source
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{source}_{ts}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "source": source,
                    "crawled_at": datetime.utcnow().isoformat(),
                    "article_count": len(articles),
                    "articles": articles,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        return str(out_path)

    def write_payload(self, source: str, payload: Dict[str, Any], filename: str) -> Optional[str]:
        """Persist an already-built payload to local JSON. Symmetric with
        GoogleDriveSink.write_payload() so the same call site works
        whether Drive or Local is selected."""
        if payload is None:
            return None
        out_dir = self.base_dir / "gold" / source
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return str(out_path)

    def health_check(self) -> bool:
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            return False


def build_sink_from_env() -> CloudSink:
    """Pick the right sink based on environment variables.

    Priority:
    1. DATABRICKS_HOST + TOKEN + VOLUME_PATH     -> Databricks Volume
    2. AWS_S3_BUCKET                              -> S3 (added when needed)
    3. GOOGLE_DRIVE_CREDENTIALS                   -> Drive
    4. Fallback                                   -> LocalJsonSink (data
       will NOT survive a redeploy).
    """
    from .databricks_sink import try_build_databricks_sink

    dbx = try_build_databricks_sink()
    if dbx:
        return dbx

    creds = (
        os.environ.get("GOOGLE_DRIVE_CREDENTIALS")
        or os.environ.get("GOOGLE_CREDENTIALS_PATH")
        # Default candidates: file đã được COPY vào image qua Dockerfile.railway.
        # Tìm theo thứ tự ưu tiên — file nào tồn tại thì dùng. Tránh phải
        # cấu hình env var trên Railway Dashboard cho mỗi lần deploy.
        or (
            "/app/configs/google-drive-credentials.json"
            if Path("/app/configs/google-drive-credentials.json").exists()
            else None
        )
        or (
            "/app/configs/client_secret_token.json"
            if Path("/app/configs/client_secret_token.json").exists()
            else None
        )
        or (
            "./configs/google-drive-credentials.json"
            if Path("./configs/google-drive-credentials.json").exists()
            else None
        )
        or (
            "./configs/client_secret_token.json"
            if Path("./configs/client_secret_token.json").exists()
            else None
        )
    )
    if creds and Path(creds).exists():
        logger.info("Cloud sink: using credentials at %s", creds)
        return GoogleDriveSink(credentials_path=creds)

    base = os.environ.get("DATA_DIR", "/app/data")
    logger.warning(
        "No cloud sink configured (DATABRICKS_* or GOOGLE_DRIVE_CREDENTIALS missing; "
        "no fallback credentials file under /app/configs or ./configs). "
        "Falling back to LocalJsonSink at %s — data will NOT persist across deploys.",
        base,
    )
    return LocalJsonSink(base_dir=base)