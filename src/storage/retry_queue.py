"""
Drive upload retry queue — lưu các payload push Drive fail, scheduler
retry ở các lần chạy sau để đảm bảo đồng bộ.

Tại sao cần:
    Crawl xong → write_payload() lên Drive. Nếu Drive fail (HTTP 5xx,
    network blip, quota exceeded, token tạm hết hạn), payload đã ghi
    local (Gold file) nhưng Drive trống. Trước đây code log lỗi rồi
    quên → mất đồng bộ vĩnh viễn.

    Module này lưu payload fail vào data/pending_uploads.json, scheduler
    retry mỗi lần sau crawl + boot, đến khi push thành công hoặc
    quá số lần thử (giữ entry làm audit).

Cấu trúc:
    data/pending_uploads.json = {
      "entries": [
        {
          "id": "uuid",
          "created_at": "2026-10-03T07:00:00Z",
          "last_attempt_at": "2026-10-03T07:01:00Z",
          "attempts": 1,
          "source": "VNExpress",
          "filename": "gold_VNExpress_20261003_070000_120000.json",
          "payload": {... full payload ...},
          "last_error": "HttpError 503: ..."
        }
      ]
    }
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


DEFAULT_STATE_FILE = "pending_uploads.json"
MAX_ATTEMPTS = 5
# Exponential backoff giữa các retry (giây). Tổng ~4+8+16+32+60 = 120s
# cho 5 lần retry. Đủ để vượt qua network blip / rate limit ngắn.
RETRY_BACKOFF = (2, 4, 8, 16, 32)


def _state_file_path() -> Path:
    base = Path(os.environ.get("DATA_DIR", "/app/data"))
    return base / DEFAULT_STATE_FILE


class UploadRetryQueue:
    """Persist upload payloads that hit transient Drive errors and replay
    them on subsequent scheduler runs.

    Mục tiêu: sau mỗi crawl, Drive PHẢI có gold mới nhất (trừ khi Drive
    thực sự down rất lâu). Không bao giờ mất sync vì 1 lần fail.
    """

    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = state_file or _state_file_path()

    # ---------- persistence ----------

    def _read(self) -> Dict:
        if not self.state_file.exists():
            return {"entries": []}
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or "entries" not in data:
                return {"entries": []}
            return data
        except (OSError, ValueError) as e:
            logger.warning("RetryQueue: read %s failed: %s", self.state_file, e)
            return {"entries": []}

    def _write(self, state: Dict) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            # atomic write: ghi vào .tmp rồi rename, tránh half-written crash
            tmp = self.state_file.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self.state_file)
        except OSError as e:
            logger.error("RetryQueue: write %s failed: %s", self.state_file, e)

    # ---------- public API ----------

    def enqueue(self, source: str, filename: str, payload: Dict) -> str:
        """Lưu payload fail vào queue, trả về entry id."""
        entry = {
            "id": uuid.uuid4().hex,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_attempt_at": None,
            "attempts": 0,
            "source": source,
            "filename": filename,
            "payload": payload,
            "last_error": None,
        }
        state = self._read()
        state["entries"].append(entry)
        self._write(state)
        logger.warning(
            "RetryQueue: enqueued %s/%s (id=%s, queue=%d)",
            source, filename, entry["id"], len(state["entries"]),
        )
        return entry["id"]

    def list_pending(self) -> List[Dict]:
        """Trả về entries cần retry (attempts < MAX_ATTEMPTS)."""
        state = self._read()
        return [e for e in state["entries"] if e.get("attempts", 0) < MAX_ATTEMPTS]

    def list_dead(self) -> List[Dict]:
        """Entries quá số lần — để user xem qua /status."""
        state = self._read()
        return [e for e in state["entries"] if e.get("attempts", 0) >= MAX_ATTEMPTS]

    def mark_success(self, entry_id: str) -> None:
        state = self._read()
        before = len(state["entries"])
        state["entries"] = [e for e in state["entries"] if e.get("id") != entry_id]
        self._write(state)
        if len(state["entries"]) < before:
            logger.info(
                "RetryQueue: removed success entry id=%s (queue=%d)",
                entry_id, len(state["entries"]),
            )

    def mark_failure(self, entry_id: str, error: str) -> None:
        state = self._read()
        for e in state["entries"]:
            if e.get("id") == entry_id:
                e["attempts"] = e.get("attempts", 0) + 1
                e["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
                e["last_error"] = error[:300]
                break
        self._write(state)

    def flush_pending(self, sink) -> Dict:
        """Retry tất cả pending entries. Trả về stats.

        Returns:
          {
            "attempted": int,
            "succeeded": int,
            "failed": int,
            "dead_letter": int,   # entries đã chạm MAX_ATTEMPTS
            "remaining": int,
            "details": [{"source", "filename", "ok", "error", "attempts"}]
          }
        """
        pending = self.list_pending()
        if not pending:
            return {
                "attempted": 0, "succeeded": 0, "failed": 0,
                "dead_letter": 0, "remaining": 0, "details": [],
            }

        details = []
        succeeded = 0
        failed = 0
        for entry in pending:
            attempts = entry.get("attempts", 0)
            backoff = RETRY_BACKOFF[min(attempts, len(RETRY_BACKOFF) - 1)]
            if attempts > 0:
                # Skip exponential backoff between retries
                logger.info(
                    "RetryQueue: backoff %ds before retry of %s/%s (attempt %d)",
                    backoff, entry["source"], entry["filename"], attempts + 1,
                )
                time.sleep(backoff)

            try:
                file_id = sink.write_payload(
                    source=entry["source"],
                    payload=entry["payload"],
                    filename=entry["filename"],
                )
            except Exception as e:
                file_id = None
                err_msg = f"{type(e).__name__}: {e}"
            else:
                err_msg = None

            if file_id:
                self.mark_success(entry["id"])
                succeeded += 1
                details.append({
                    "source": entry["source"],
                    "filename": entry["filename"],
                    "ok": True,
                    "file_id": file_id,
                    "attempts": entry.get("attempts", 0) + 1,
                })
            else:
                self.mark_failure(entry["id"], err_msg or "write_payload returned None")
                failed += 1
                # nếu đã chạm MAX_ATTEMPTS → giữ trong state làm audit
                new_attempts = entry.get("attempts", 0) + 1
                details.append({
                    "source": entry["source"],
                    "filename": entry["filename"],
                    "ok": False,
                    "error": err_msg,
                    "attempts": new_attempts,
                    "dead_letter": new_attempts >= MAX_ATTEMPTS,
                })

        dead = len(self.list_dead())
        remaining = len(self.list_pending())

        logger.info(
            "RetryQueue: flush done — ok=%d, fail=%d, dead=%d, remaining=%d",
            succeeded, failed, dead, remaining,
        )
        return {
            "attempted": len(pending),
            "succeeded": succeeded,
            "failed": failed,
            "dead_letter": dead,
            "remaining": remaining,
            "details": details,
        }

    def stats(self) -> Dict:
        state = self._read()
        entries = state.get("entries", [])
        return {
            "total": len(entries),
            "pending": len([e for e in entries if e.get("attempts", 0) < MAX_ATTEMPTS]),
            "dead_letter": len([e for e in entries if e.get("attempts", 0) >= MAX_ATTEMPTS]),
            "max_attempts": MAX_ATTEMPTS,
        }


_queue: Optional[UploadRetryQueue] = None


def get_retry_queue() -> UploadRetryQueue:
    """Singleton factory."""
    global _queue
    if _queue is None:
        _queue = UploadRetryQueue()
    return _queue