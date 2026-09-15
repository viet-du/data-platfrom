FROM python:3.10-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY src/ ./src/
COPY crawl_news.py .
COPY crawl_raw.py .
COPY configs/ ./configs/

# Create dirs
RUN mkdir -p /app/data/raw /app/data/logs

# Run crawler
CMD ["python", "crawl_news.py"]
