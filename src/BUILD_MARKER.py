"""Build marker - chi ton tai de bust Docker COPY cache.

Moi lan bump version, file nay doi SHA -> COPY src/ chac chan re-run
tren Railway. KHONG duoc import boi code production.

Current build: 2026-10-03-cache-bust-v12-credentials-precedence-fix
"""
BUILD_TAG = "2026-10-03-cache-bust-v12-credentials-precedence-fix"
BUILD_NOTE = "v12 fix: raw JSON env wins over stale path env (client_secret_token.json bypass)"
