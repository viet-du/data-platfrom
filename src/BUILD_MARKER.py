"""Build marker — chỉ tồn tại để bust Docker COPY cache.

Mỗi lần bump version, file này đổi SHA → COPY src/ chắc chắn re-run
trên Railway. KHÔNG được import bởi code production.

Current build: 2026-10-03-cache-bust-v4
"""
BUILD_TAG = "2026-10-03-cache-bust-v10-drive-retry-queue"
BUILD_NOTE = "Drive write retry 3x + UploadRetryQueue + /retry command + boot flush"