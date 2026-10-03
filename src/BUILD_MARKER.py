"""Build marker — chỉ tồn tại để bust Docker COPY cache.

Mỗi lần bump version, file này đổi SHA → COPY src/ chắc chắn re-run
trên Railway. KHÔNG được import bởi code production.

Current build: 2026-10-03-cache-bust-v4
"""
BUILD_TAG = "2026-10-03-cache-bust-v7-drive-pull-on-boot"
BUILD_NOTE = "auto DrivePuller when gold_dir empty + volume diagnostics (df/du/ls)"