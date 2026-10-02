#!/usr/bin/env bash
# pull_logs.sh — pull the latest crawler log from Drive into a local file.
#
# Why: the user wants to "open the laptop -> see logs". The container's
# stdout lives on Railway only and is rotated. This script fetches the
# most recent `bot.log` (uploaded by the bot every hour via the
# `cmd_upload_logs` command) into ~/.cache/data-platform/logs/ so a
# quick `tail -f` works locally without SSH'ing anywhere.
#
# Required env (set in ~/.config/data-platform/env or pass inline):
#   GOOGLE_DRIVE_CREDENTIALS  absolute path to service-account JSON
#   DRIVE_LOG_FOLDER_ID       Drive folder id that holds bot logs
#
# mac auto-asks launchd to run this on login — see
# scripts/com.data-platform.logpuller.plist

set -euo pipefail

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/data-platform"
ENV_FILE="$CONFIG_DIR/env"
LOCAL_LOG_DIR="$HOME/.cache/data-platform/logs"
mkdir -p "$LOCAL_LOG_DIR"

# Load env if present, but don't fail if missing — the user may not have
# configured Drive access on the dev machine.
[ -f "$ENV_FILE" ] && set -a && . "$ENV_FILE" && set +a

if [ -z "${GOOGLE_DRIVE_CREDENTIALS:-}" ] || [ -z "${DRIVE_LOG_FOLDER_ID:-}" ]; then
    echo "[pull_logs] GOOGLE_DRIVE_CREDENTIALS or DRIVE_LOG_FOLDER_ID not set; skipping." >&2
    echo "[pull_logs] (Configure $ENV_FILE to enable auto log pull.)" >&2
    exit 0
fi

CRED_PATH="$GOOGLE_DRIVE_CREDENTIALS"
if [ ! -f "$CRED_PATH" ]; then
    echo "[pull_logs] Credentials file not found at $CRED_PATH" >&2
    exit 0
fi

python3 - "$CRED_PATH" "$DRIVE_LOG_FOLDER_ID" "$LOCAL_LOG_DIR" <<'PY'
"""Fetch the latest bot.log from a Drive folder using a service account."""
import json
import sys
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

creds_path, folder_id, log_dir = sys.argv[1], sys.argv[2], sys.argv[3]
log_dir_p = Path(log_dir)
log_dir_p.mkdir(parents=True, exist_ok=True)

creds = service_account.Credentials.from_service_account_file(
    creds_path,
    scopes=["https://www.googleapis.com/auth/drive.readonly"],
)
svc = build("drive", "v3", credentials=creds)

# Find the most recently modified bot.log in the folder.
results = svc.files().list(
    q=f"'{folder_id}' in parents and name contains 'bot.log' and trashed=false",
    orderBy="modifiedTime desc",
    pageSize=5,
    supportsAllDrives=True,
    includeItemsFromAllDrives=True,
    fields="files(id, name, modifiedTime, size)",
).execute()
files = results.get("files", [])
if not files:
    print("[pull_logs] No bot.log found in Drive folder yet.")
    sys.exit(0)

latest = files[0]
out_path = log_dir_p / "bot.log"
request = svc.files().get_media(fileId=latest["id"], supportsAllDrives=True)
with open(out_path, "wb") as fh:
    downloader = request.execute()  # bytes
    fh.write(downloader)

print(f"[pull_logs] Pulled {latest['name']} ({latest.get('size', '?')} bytes) -> {out_path}")
PY