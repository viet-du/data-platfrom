"""
Persistent Vector Store — keeps the Chroma index alive across container restarts.

Why this exists:
  The container on Railway free tier restarts whenever a deploy happens or
  when the region migrates, and the `/app/data` Volume sometimes gets wiped.
  Without persistence:
    - /ask starts working but immediately returns "no relevant articles"
      because Chroma boots with an empty collection.
    - The user has to manually re-run /index after every redeploy, which
      costs CPU time and looks like the bot is broken.

  With this wrapper:
    1. Chroma persists at /app/data/chroma as before (Layer 1).
    2. Every N hours, the snapshot is tarred and pushed to Drive
       (Layer 2).
    3. On startup, if the local collection is empty, we look for the
       latest Drive snapshot and restore it (Layer 3).
    4. Telegram notifies whether the index was healthy on boot.

Backends supported:
  - Local chromadb (always)
  - Google Drive snapshot (when GOOGLE_DRIVE_CREDENTIALS env is set)
"""
from __future__ import annotations

import io
import json
import logging
import os
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .vector_store import VectorStore, DEFAULT_COLLECTION

logger = logging.getLogger(__name__)

SNAPSHOT_DRIVE_FOLDER = "rag-snapshots"


class PersistentVectorStore(VectorStore):
    """VectorStore that snapshots itself to Drive and restores on boot."""

    def __init__(
        self,
        persist_dir: str = None,
        collection_name: str = DEFAULT_COLLECTION,
        embedding_model: str = None,
        snapshot_folder: str = None,
    ):
        super().__init__(
            persist_dir=persist_dir,
            collection_name=collection_name,
            embedding_model=embedding_model or "sentence-transformers/all-MiniLM-L6-v2",
        )
        self.snapshot_folder = snapshot_folder or SNAPSHOT_DRIVE_FOLDER
        self._last_snapshot_at: Optional[datetime] = None
        self._restored_from: Optional[str] = None

    # ---------- snapshot helpers ----------

    def _archive_path(self) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return Path("/tmp") / f"rag_snapshot_{ts}.tar.gz"

    def _build_archive(self, dest: Path) -> Path:
        """Tar + gzip the entire chroma persist_dir."""
        src = Path(self.persist_dir)
        if not src.exists():
            raise FileNotFoundError(f"No chroma dir to snapshot at {src}")
        with tarfile.open(dest, "w:gz") as tar:
            tar.add(str(src), arcname="chroma")
        return dest

    def snapshot_to_drive(self) -> Optional[str]:
        """Upload a fresh snapshot archive to Drive. Returns the file id.

        Why: even with persist_dir on a Railway Volume, a region
        migration wipes the disk. Pushing a copy of the index to Drive
        lets us restore from any new container that boots in a
        different region.
        """
        creds_path = os.environ.get("GOOGLE_DRIVE_CREDENTIALS") or os.environ.get(
            "GOOGLE_CREDENTIALS_PATH"
        )
        if not creds_path or not Path(creds_path).exists():
            logger.info(
                "snapshot_to_drive: GOOGLE_DRIVE_CREDENTIALS not configured; skipping"
            )
            return None

        try:
            self._ensure_loaded()
        except Exception as e:
            logger.error("snapshot_to_drive: failed to load store: %s", e)
            return None

        archive = self._build_archive(self._archive_path())
        try:
            from googleapiclient.http import MediaFileUpload
            from googleapiclient.errors import HttpError

            from src.services.google_drive_service import GoogleDriveService

            drive = GoogleDriveService(credentials_path=creds_path, use_oauth=False)
            folder_id = drive.create_folder(self.snapshot_folder)
            if not folder_id:
                logger.warning("snapshot_to_drive: could not create %s folder", self.snapshot_folder)
                return None

            media = MediaFileUpload(str(archive), mimetype="application/gzip", resumable=True)
            created = drive.service.files().create(
                body={"name": archive.name, "parents": [folder_id]},
                media_body=media,
                fields="id",
                supportsAllDrives=True,
            ).execute()
            file_id = created.get("id")
            self._last_snapshot_at = datetime.now(timezone.utc)
            logger.info(
                "snapshot_to_drive: uploaded %s -> Drive file id=%s",
                archive.name,
                file_id,
            )
            return file_id
        except Exception as e:
            logger.error("snapshot_to_drive failed: %s", e)
            return None
        finally:
            try:
                archive.unlink()
            except OSError:
                pass

    def restore_from_drive(self) -> bool:
        """If the local index is empty, pull the latest Drive archive and
        restore it. Returns True if we restored something."""
        if Path(self.persist_dir).exists() and any(Path(self.persist_dir).iterdir()):
            count_estimate = self._estimate_local_count()
            if count_estimate and count_estimate > 0:
                logger.info(
                    "restore_from_drive: local chroma already has data; skip"
                )
                return False

        creds_path = os.environ.get("GOOGLE_DRIVE_CREDENTIALS") or os.environ.get(
            "GOOGLE_CREDENTIALS_PATH"
        )
        if not creds_path or not Path(creds_path).exists():
            logger.info("restore_from_drive: no Drive credentials; cannot restore")
            return False

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError

            creds = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/drive"],
            )
            svc = build("drive", "v3", credentials=creds)

            folder_q = (
                f"name='{self.snapshot_folder}' and "
                f"mimeType='application/vnd.google-apps.folder' and trashed=false"
            )
            folders = svc.files().list(
                q=folder_q,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields="files(id, name)",
            ).execute().get("files", [])
            if not folders:
                logger.info("restore_from_drive: no %s folder on Drive", self.snapshot_folder)
                return False

            folder_id = folders[0]["id"]
            snaps = svc.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                orderBy="modifiedTime desc",
                pageSize=5,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields="files(id, name, modifiedTime, size)",
            ).execute().get("files", [])
            if not snaps:
                logger.info("restore_from_drive: no snapshots in folder")
                return False

            latest = snaps[0]
            request = svc.files().get_media(
                fileId=latest["id"], supportsAllDrives=True
            )
            archive_bytes = request.execute()

            with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tar:
                # Extract to a temp dir first then move into place.
                tmp_root = Path("/tmp") / f"rag_restore_{datetime.now().strftime('%H%M%S')}"
                tmp_root.mkdir(parents=True, exist_ok=True)
                tar.extractall(tmp_root)
                extracted_chroma = tmp_root / "chroma"
                if not extracted_chroma.exists():
                    logger.error("restore_from_drive: archive has no chroma/ inside")
                    return False

                # Wipe local and copy in. We don't try to merge.
                if Path(self.persist_dir).exists():
                    shutil.rmtree(self.persist_dir)
                shutil.copytree(extracted_chroma, self.persist_dir)
                shutil.rmtree(tmp_root)

            self._restored_from = latest.get("name", "?")
            self._client = None  # force reload on next query
            self._collection = None
            logger.info(
                "restore_from_drive: restored %s (%s) into %s",
                latest.get("name"),
                latest.get("size"),
                self.persist_dir,
            )
            return True
        except Exception as e:
            logger.error("restore_from_drive failed: %s", e)
            return False

    def _estimate_local_count(self) -> int:
        """Cheap count that doesn't force-load Chroma.

        We just sum sqlite rowcount from chroma's sqlite file if present,
        otherwise we return 0 so restore is allowed to attempt.
        """
        sqlite = Path(self.persist_dir) / "chroma.sqlite3"
        if not sqlite.exists():
            return 0
        try:
            import sqlite3

            con = sqlite3.connect(str(sqlite))
            cur = con.execute(
                "SELECT count(*) FROM embeddings e "
                "JOIN collections c ON e.collection_id = c.id "
                "WHERE c.name = ?",
                (self.collection_name,),
            )
            return int(cur.fetchone()[0])
        except Exception:
            return 0

    # ---------- status helpers ----------

    def status(self) -> dict:
        """Return a dict for Telegram /ragstats-style reporting."""
        try:
            self._ensure_loaded()
            count = self.count
            local_count = self._estimate_local_count()
        except Exception as e:
            return {"ok": False, "error": str(e)}

        return {
            "ok": True,
            "collection": self.collection_name,
            "embedding_model": self.embedding_model_name,
            "documents_in_collection": count,
            "documents_in_sqlite": local_count,
            "persist_dir": self.persist_dir,
            "snapshot_folder": self.snapshot_folder,
            "last_snapshot_at": self._last_snapshot_at.isoformat() if self._last_snapshot_at else None,
            "restored_from": self._restored_from,
        }


# Singleton used by main_service.py — created lazily so the bot doesn't
# load Chroma + sentence-transformers at module import time.
_persistent_store: Optional[PersistentVectorStore] = None


def get_persistent_store() -> PersistentVectorStore:
    global _persistent_store
    if _persistent_store is None:
        _persistent_store = PersistentVectorStore()
    return _persistent_store