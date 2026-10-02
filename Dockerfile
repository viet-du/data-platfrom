FROM python:3.10-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Force rebuild layer: any change to this line invalidates Docker cache.
# Bump this whenever requirements.txt changes so Railway does not
# serve a stale image missing the new packages.
RUN echo "deps build: 2026-10-02-rag-error-surfacing-v2" && pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy app
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY configs/ ./configs/

# Create dirs
RUN mkdir -p /app/data/raw /app/data/logs /app/data/silver /app/data/gold /app/data/summary

# Remove any conflicting root .py files
RUN find /app -maxdepth 1 -name "*.py" -delete

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run main service
CMD ["python", "-u", "scripts/main_service.py"]