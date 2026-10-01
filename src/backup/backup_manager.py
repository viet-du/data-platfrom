"""
Backup Manager - Syncs Parquet + Chroma metadata to a Drive folder.

Why: Even with Railway Volume (persistent disk), you still want an off-host
copy in case the volume is wiped during a region migration or you
accidentally destroy the service.
"""
import os
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.services.google_drive_service import GoogleDriveService


BACKUP_FOLDER_NAME = os.getenv("BRACKUP_DRIVE_FOLDER", "data-backups")


def create_local_archive(data_dir: str = None, archive_path: str = None) -> str:
    """Tar + gzip the parquet + chroma dirs into a single archive."""
    base = Path(data_dir or os.environ.get("DATA_DIR", "/app/data"))
    if archive_path is None:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archive_path = str(base / "backups" / f"backup_{ts}.tar.gz")

    Path(archive_path).parent.mkdir(parents=True, exist_ok=True)

    sources = []
    for sub in ("parquet", "chroma"):
        p = base / sub
        if p.exists():
            sources.append((p, sub))

    if not sources:
        return ""

    with tarfile.open(archive_path, "w:gz") as tar:
        for path, arcname in sources:
            tar.add(str(path), arcname=arcname)

    return archive_path


def upload_backup_to_drive(archive_path: str, drive_service: GoogleDriveService) -> Optional[str]:
    """Upload the archive to Drive under BACKUP_FOLDER_NAME; returns file id."""
    from googleapiclient.http import MediaFileUpload

    service = drive_service.service
    if not service:
        return None

    folder_id = drive_service.get_or_create_folder(BACKUP_FOLDER_NAME)
    if not folder_id:
        return None

    file_metadata = {
        "name": Path(archive_path).name,
        "parents": [folder_id],
    }
    media = MediaFileUpload(archive_path, mimetype="application/gzip", resumable=False)
    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return file.get("id")


def prune_old_archives(data_dir: str = None, keep: int = 7) -> int:
    """Keep only the N most recent local archives to bound disk usage."""
    base = Path(data_dir or os.environ.get("DATA_DIR", "/app/data"))
    backup_dir = base / "backups"
    if not backup_dir.exists():
        return 0

    archives = sorted(backup_dir.glob("backup_*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    removed = 0
    for old in archives[keep:]:
        try:
            old.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def run_backup(upload_to_drive: bool = True, keep_local: int = 7) -> dict:
    """Create archive, optionally upload to Drive, prune old copies."""
    archive = create_local_archive()
    if not archive:
        return {"ok": False, "reason": "no data to archive"}

    size_mb = Path(archive).stat().st_size / (1024 * 1024)
    result = {"ok": True, "archive": archive, "size_mb": round(size_mb, 2)}

    if upload_to_drive:
        try:
            creds_path = os.environ.get("GOOGLE_DRIVE_CREDENTIALS")
            if creds_path:
                drive = GoogleDriveService(credentials_path=creds_path, use_oauth=False)
                file_id = upload_backup_to_drive(archive, drive)
                if file_id:
                    result["drive_file_id"] = file_id
                else:
                    result["drive_error"] = "Drive upload returned no id"
        except Exception as e:
            result["drive_error"] = str(e)

    result["pruned_local"] = prune_old_archives(keep=keep_local)
    return result


if __name__ == "__main__":
    import json as json_mod
    print(json_mod.dumps(run_backup(), indent=2))