"""Build marker — chỉ tồn tại để bust Docker COPY cache.

Mỗi lần bump version, file này đổi SHA → COPY src/ chắc chắn re-run
trên Railway. KHÔNG được import bởi code production.

Current build: 2026-10-03-cache-bust-v4
"""
BUILD_TAG = "2026-10-03-cache-bust-v9-default-creds-path"
BUILD_NOTE = "build_sink_from_env: fallback to /app/configs/*.json so Drive works without env var"