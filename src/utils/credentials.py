"""Resolve Google service account credentials path.

Order of precedence:
  1. GOOGLE_DRIVE_CREDENTIALS env var pointing to an existing file path
     (the historical contract; the file is typically configs/google-drive-
     credentials.json inside the image).
  2. GOOGLE_DRIVE_CREDENTIALS_JSON env var containing the raw JSON
     contents. This is the recommended setup for Railway: paste the
     service account JSON into a variable rather than baking it into
     the image. We materialize the JSON to a tmp file and return its
     path so existing call sites that take a file path keep working.
  3. The committed configs/google-drive-credentials.json file (legacy
     fallback for local dev). New deployments should prefer option 2.

Returns:
  - Path to a credentials file on disk, or
  - None if no credentials could be resolved (callers should treat
    this as "Drive features disabled" rather than crashing).
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Env var name for the raw JSON contents (preferred on Railway).
_ENV_JSON = "GOOGLE_DRIVE_CREDENTIALS_JSON"
# Env var name for a pre-existing file path (also read by callers).
_ENV_PATH = "GOOGLE_DRIVE_CREDENTIALS"
# Legacy fallback path inside the image (only for local dev).
_LEGACY_PATH = "configs/google-drive-credentials.json"


def resolve_credentials_path() -> str | None:
    """Return a path to a valid SA JSON file, or None if unavailable."""
    # 1) Explicit path via env var wins.
    explicit = os.environ.get(_ENV_PATH)
    if explicit and Path(explicit).is_file():
        return explicit

    # 2) Raw JSON in env var: materialize to a tmp file once.
    raw = os.environ.get(_ENV_JSON)
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error("GOOGLE_DRIVE_CREDENTIALS_JSON is not valid JSON: %s", e)
            return None
        # Validate the minimum required SA fields so we fail loud
        # rather than mysteriously later inside the auth library.
        for key in ("type", "client_email", "private_key", "token_uri"):
            if key not in data:
                logger.error("GOOGLE_DRIVE_CREDENTIALS_JSON missing field: %s", key)
                return None
        if data.get("type") != "service_account":
            logger.error(
                "GOOGLE_DRIVE_CREDENTIALS_JSON must be a service_account; got %r",
                data.get("type"),
            )
            return None

        fd, path = tempfile.mkstemp(prefix="gdrive_sa_", suffix=".json")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f)
            # Restrict perms since the JSON contains a private key.
            os.chmod(path, 0o600)
        except Exception:
            logger.exception("Failed to materialize Drive credentials")
            return None
        logger.info(
            "Drive credentials loaded from %s (client_email=%s)",
            _ENV_JSON, data.get("client_email"),
        )
        return path

    # 3) Legacy in-repo file (local dev convenience).
    legacy = Path(_LEGACY_PATH)
    if legacy.is_file():
        return str(legacy)

    logger.info(
        "No Drive credentials configured (env %s unset, legacy missing)",
        _ENV_JSON,
    )
    return None