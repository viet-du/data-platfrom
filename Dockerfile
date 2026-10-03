FROM python:3.10-slim-bookworm

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first. This avoids pulling the ~3.5 GB of
# CUDA/cuDNN/NCCL packages that the default torch wheel drags in.
# The MiniLM embedder runs fine on CPU on a 512 MB container.
RUN pip install --upgrade pip \
    && pip install --no-cache-dir \
       --index-url https://download.pytorch.org/whl/cpu \
       torch==2.4.0

# Copy requirements first for caching
COPY requirements.txt .

# Force rebuild layer: any change to this line invalidates Docker cache.
RUN echo "deps build: 2026-10-03-cache-bust-v6-marker" \
    && pip install --no-cache-dir -r requirements.txt

# ============================================================
# SOURCE-COPY CACHE BUST (guaranteed fresh code on Railway)
# ============================================================
# BuildKit caches each `COPY <tree> ./dest/` layer against the
# content-hash of `<tree>`. If git checkout preserves the same
# hash between pushes (very common — git content is content-
# addressed regardless of timestamp), BuildKit reuses the OLD
# layer and the new code never lands in the container.
#
# The marker file below is generated with `date` so its content
# is unique on every single build, which forces the SHA of src/
# to differ even when no other files moved. Then `COPY src/`
# always misses cache and re-reads the build context.
# ============================================================
ARG BUILD_TAG=2026-10-03-cache-bust-v6-marker
RUN echo "${BUILD_TAG} $(date -u +%FT%TZ.%N)" > /app/_build_marker

# Wipe + re-COPY in one logical step. We do `rm -rf` BEFORE COPY
# so that even if a cached layer gets reused somehow, the new
# COPY step still overwrites with current build context.
RUN rm -rf /app/src /app/scripts /app/configs /app/dags
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY configs/ ./configs/
COPY dags/ ./dags/

# Sanity-check: prove the new __init__.py is on disk before we
# declare the build done. If COPY skipped due to cache, this
# would print the OLD first 5 lines — visible in build log.
RUN echo "=== /app/src/rag/__init__.py first 5 lines ===" \
 && head -5 /app/src/rag/__init__.py \
 && echo "=== /app/src/BUILD_MARKER.py ===" \
 && cat /app/src/BUILD_MARKER.py \
 && echo "=== BUILD_TAG was: ${BUILD_TAG} ==="

# Create data directories (Railway Volume will be mounted here)
RUN mkdir -p /app/data/raw /app/data/silver /app/data/gold \
    /app/data/logs /app/data/summary /app/data/parquet \
    /app/data/chroma /app/data/backups /app/data/raw_pulled

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DATA_DIR=/app/data

# Remove any conflicting root .py files (safety)
RUN find /app -maxdepth 1 -name "*.py" -delete

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command - runs all services
CMD ["python", "-u", "scripts/main_service.py"]