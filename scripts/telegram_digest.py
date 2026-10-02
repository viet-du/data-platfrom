"""
Telegram log digest — buffer transient events and ship them as a
single daily digest, instead of spamming the user with a message per
crawl / per snapshot / per backup.

Why:
  Telegram notifications are useful — but only when they signal
  *something the user must look at*. A constant stream of "crawling
  started", "crawling done", "snapshot pushed" turns the chat into
  noise and the user starts muting the bot, missing the real alerts
  (errors, milestones, weekly stats).

Design:
  - High-importance events (errors, milestones, restart, user-requested
    reply) still send IMMEDIATELY — never buffer those.
  - Low-importance events (crawl start/stop, snapshot OK, hourly
    heartbeat, backup OK) get appended to an in-memory ring buffer.
  - At a configured hour (default 20:00 local) the bot sends a single
    digest message summarising the day's events.
  - Buffer size is capped so a runaway loop can't OOM the container.
  - Everything is thread-safe — the scheduler is on its own thread
    and the bot runs handlers on the main thread.
"""
from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Callable, Optional


logger = logging.getLogger(__name__)

# Cap at 200 entries — enough for one full day, never enough to OOM.
_MAX_BUFFER = 200


class TelegramDigest:
    """Buffered, batched Telegram reporter.

    Use `digest(buffer)(report)` for low-importance events, and the
    underlying `send` method directly for high-importance events.
    """

    def __init__(self, sender: Callable[[str], None], chat_id: Optional[str] = None):
        # sender: a callable that takes a single HTML string.
        self._send = sender
        self._chat_id = chat_id
        self._buf: deque[dict] = deque(maxlen=_MAX_BUFFER)
        self._lock = threading.Lock()
        self._events_recorded = 0  # for the day's stats in the digest header

    # ---------- buffer-only mode ----------

    def buffer(self, event: str, level: str = "info", detail: str = ""):
        """Record a low-importance event for the next digest. Never sends."""
        with self._lock:
            self._buf.append({
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "event": event,
                "level": level,           # INFO | OK | WARN | ERR
                "detail": detail,
            })
            self._events_recorded += 1

    # ---------- immediate-send mode (errors & milestones) ----------

    def send(self, message: str):
        """Send immediately. Use only for high-importance events.

        Also records the message into the buffer so the digest shows
        "Crawl started at 7am, finished at 7:04" with timestamps.
        """
        try:
            self._send(message)
        except Exception as e:
            logger.warning("Telegram send failed: %s", e)
            return
        # Mirror into the buffer so the user sees a timeline in the digest.
        with self._lock:
            first_line = message.split("\n", 1)[0]
            self._buf.append({
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "event": first_line,
                "level": "SEND",
                "detail": "",
            })

    # ---------- digest ----------

    def format_digest(self) -> Optional[str]:
        """Return a pretty Telegram-friendly digest, or None if empty."""
        with self._lock:
            entries = list(self._buf)
            self._buf.clear()
            self._events_recorded = 0
        if not entries:
            return None

        # Bucket by level so the user sees signal-vs-noise at a glance.
        buckets: dict[str, list[str]] = {"ERR": [], "WARN": [], "OK": [], "INFO": [], "SEND": []}
        for e in entries:
            level = e["level"] if e["level"] in buckets else "INFO"
            ts_short = e["ts"][11:16]  # HH:MM
            line = f"  {ts_short}  {e['event']}"
            if e["detail"]:
                line += f"  ({e['detail']})"
            buckets[level].append(line)

        out: list[str] = [
            f"📋 <b>Daily Digest</b> ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
            f"📝 {len(entries)} sự kiện đã ghi nhận\n",
        ]
        # Order: errors → warnings → successes → info → sent messages.
        order = [("ERR", "❌ Errors"), ("WARN", "⚠️ Warnings"),
                 ("INFO", "ℹ️ Activity"), ("OK", "✅ Successes"),
                 ("SEND", "📨 Outgoing")]
        for level, header in order:
            if buckets[level]:
                out.append(f"<b>{header}</b> ({len(buckets[level])})")
                # Cap each section at 20 lines so we don't blow Telegram's
                # 4096 char limit on a noisy day.
                shown = buckets[level][-20:]
                out.extend(shown)
                if len(buckets[level]) > 20:
                    out.append(f"    … +{len(buckets[level]) - 20} more")
                out.append("")
        # Trim hard if still too long (Telegram limit 4096).
        text = "\n".join(out)
        if len(text) > 3800:
            text = text[:3800] + "\n…(truncated)"
        return text

    def flush_digest(self) -> bool:
        """Send the current digest and clear the buffer. Returns True if sent."""
        msg = self.format_digest()
        if msg is None:
            return False
        try:
            self._send(msg)
            return True
        except Exception as e:
            logger.warning("Telegram digest send failed: %s", e)
            return False

    def stats(self) -> dict:
        """Return counters for /status."""
        with self._lock:
            return {
                "buffered": len(self._buf),
                "cap": _MAX_BUFFER,
            }