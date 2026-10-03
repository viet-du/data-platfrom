"""Build marker — chỉ tồn tại để bust Docker COPY cache.

Mỗi lần bump version, file này đổi SHA → COPY src/ chắc chắn re-run
trên Railway. KHÔNG được import bởi code production.

Current build: 2026-10-03-cache-bust-v4
"""
BUILD_TAG = "2026-10-03-cache-bust-v8-always-push-gold"
BUILD_NOTE = "always push gold_*.json to Drive after each crawl (no gate on gold>0)"