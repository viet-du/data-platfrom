# Multi-Source News Crawler

Hệ thống crawler tin tức đa nguồn tự động thu thập và lưu trữ bài viết từ các trang báo lớn tại Việt Nam.

## 📰 Các Nguồn Tin

| # | Nguồn | URL | Thư Mục Drive |
|---|-------|-----|---------------|
| 1 | VNExpress | vnexpress.net | `vnexpress-news` |
| 2 | Tuổi Trẻ | tuoitre.vn | `tuoitre-news` |
| 3 | VietnamNet | vietnamnet.vn | `vietnamnet-news` |
| 4 | Dân Trí | dantri.com.vn | `dantri-news` |

---

## 🏗️ Kiến Trúc Hệ Thống

### System Architecture (Event-Driven / Pipeline)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SYSTEM ARCHITECTURE                                   │
│                         (Event-Driven / Pipeline)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                    │
│  │   SCHEDULER │────▶│   EXECUTOR  │────▶│   STORAGE   │                    │
│  │  (Airflow)  │     │(ThreadPool) │     │  (JSON/GCS) │                    │
│  │             │     │             │     │             │                    │
│  │  6h, 18h    │     │  4-8 threads│     │  Raw + Proc │                    │
│  └─────────────┘     └──────┬──────┘     └─────────────┘                    │
│                             │                                                │
│         ┌───────────────────┼───────────────────┐                           │
│         ▼                   ▼                   ▼                            │
│   ┌───────────┐     ┌───────────┐     ┌───────────┐                         │
│   │  Crawler  │     │  Crawler  │     │  Crawler  │                         │
│   │ VNExpress │     │ Tuổi Trẻ  │     │VietnamNet │   ...                   │
│   │  (Thread) │     │  (Thread) │     │  (Thread) │                          │
│   └─────┬─────┘     └─────┬─────┘     └─────┬─────┘                          │
│         │                 │                 │                                 │
│         └─────────────────┼─────────────────┘                                 │
│                           ▼                                                   │
│                   ┌───────────────┐                                           │
│                   │   DEDUP       │ ← Deduplicate by URL hash                 │
│                   │   CHECK       │                                           │
│                   └───────┬───────┘                                           │
│                           │                                                   │
│                           ▼                                                   │
│                   ┌───────────────┐                                           │
│                   │   NORMALIZE   │ ← Chuẩn hóa schema                        │
│                   │   & VALIDATE  │                                           │
│                   └───────┬───────┘                                           │
│                           │                                                   │
│                           ▼                                                   │
│                   ┌───────────────┐                                           │
│                   │  GOOGLE DRIVE│ ← Upload per source folder                │
│                   │  UPLOAD      │                                           │
│                   └───────────────┘                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA ARCHITECTURE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│   │ VNExpress│    │ Tuổi Trẻ │    │VietnamNet│    │  Dân Trí │           │
│   │   RSS    │    │   RSS    │    │   RSS    │    │   HTML    │           │
│   └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘           │
│        │               │               │               │                   │
│        └───────────────┴───────────────┴───────────────┘                   │
│                                │                                             │
│                    ┌───────────▼───────────┐                                │
│                    │   RAW DATA LAYER      │                                │
│                    │   (JSON/HTML Chưa Xử Lý)                               │
│                    └───────────┬───────────┘                                │
│                                │                                             │
│                    ┌───────────▼───────────┐                                │
│                    │  PROCESSED LAYER     │                                │
│                    │  (Cleaned, Normalized)│                                │
│                    └───────────┬───────────┘                                │
│                                │                                             │
│                    ┌───────────▼───────────┐                                │
│                    │   CONSUMPTION LAYER  │                                │
│                    │  (Google Drive/GCS)  │                                │
│                    └───────────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### OOP Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     OOP ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                    ABC (Abstract)                       │  │
│   │                 BaseCrawler                              │  │
│   │  ┌─────────────────────────────────────────────────┐    │  │
│   │  │ + name: str                                      │    │  │
│   │  │ + base_url: str                                  │    │  │
│   │  │ + categories: List[str]                           │    │  │
│   │  │ + crawl() -> List[Article]                       │    │  │
│   │  │ + parse_article() -> Article                     │    │  │
│   │  │ - fetch() -> Response                             │    │  │
│   │  │ - parse_list() -> List[str]                       │    │  │
│   │  └─────────────────────────────────────────────────┘    │  │
│   └───────────────────────┬─────────────────────────────────┘  │
│                           │ extends                            │
│         ┌─────────────────┼─────────────────┬─────────────────┐│
│         ▼                 ▼                 ▼                 ▼│
│   ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐│
│   │VNExpress  │    │ Tuổi Trẻ │    │VietnamNet │    │  Dân Trí  ││
│   │Crawler    │    │ Crawler   │    │ Crawler   │    │  Crawler  ││
│   └───────────┘    └───────────┘    └───────────┘    └───────────┘│
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │              GoogleDriveService                         │  │
│   │  ┌─────────────────────────────────────────────────┐  │  │
│   │  │ - authenticate()                                  │  │  │
│   │  │ - create_folder() -> str (folder_id)             │  │  │
│   │  │ - upload_json() -> str (file_id)                 │  │  │
│   │  │ - upload_batch() -> List[str]                    │  │  │
│   │  └─────────────────────────────────────────────────┘  │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW                                         │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. SCHEDULE (6h, 18h)                                                   │
│         │                                                                │
│         ▼                                                                │
│  2. PARALLEL FETCH (ThreadPoolExecutor)                                 │
│     ┌────────────────────────────────────────────────────────────┐      │
│     │  Thread 1: VNExpress    → GET /rss/home                    │      │
│     │  Thread 2: Tuổi Trẻ    → GET /rss/home                    │      │
│     │  Thread 3: VietnamNet   → GET /rss/home                    │      │
│     │  Thread 4: Dân Trí      → GET / (HTML parse)               │      │
│     └────────────────────────────────────────────────────────────┘      │
│         │                                                                │
│         ▼                                                                │
│  3. PARSE & NORMALIZE                                                   │
│     ┌────────────────────────────────────────────────────────────┐      │
│     │  VNExpress RSS  ──▶  Article(title, content, url, ...)    │      │
│     │  Tuổi Trẻ RSS   ──▶  Article(title, content, url, ...)    │      │
│     │  VietnamNet RSS ──▶  Article(title, content, url, ...)    │      │
│     │  Dân Trí HTML   ──▶  Article(title, content, url, ...)      │      │
│     └────────────────────────────────────────────────────────────┘      │
│         │                                                                │
│         ▼                                                                │
│  4. DEDUPLICATE (Hash URL)                                              │
│         │                                                                │
│         ▼                                                                │
│  5. SAVE TO STORAGE                                                      │
│     ┌────────────────────────────────────────────────────────────┐      │
│     │  data/raw/                                                  │      │
│     │  ├── vnexpress_2026-09-14_06h.json                        │      │
│     │  ├── tuoitre_2026-09-14_06h.json                          │      │
│     │  ├── vietnamnet_2026-09-14_06h.json                       │      │
│     │  └── dantri_2026-09-14_06h.json                           │      │
│     │                                                              │      │
│     │  Google Drive:                                              │      │
│     │  ├── vnexpress-news/  (folder)                             │      │
│     │  ├── tuoitre-news/     (folder)                             │      │
│     │  ├── vietnamnet-news/  (folder)                             │      │
│     │  └── dantri-news/      (folder)                             │      │
│     └────────────────────────────────────────────────────────────┘      │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Model

### Article Schema

```json
{
  "source_id": "vnexpress",
  "source_name": "VNExpress",
  "url": "https://vnexpress.net/...",
  "article_id": "abc123hash...",
  "title": "Tiêu đề bài viết",
  "description": "Mô tả ngắn",
  "content": "Nội dung chính...",
  "author": "Tên tác giả",
  "published_at": "2026-09-14T10:30:00Z",
  "category": "thoi-su",
  "tags": ["tag1", "tag2"],
  "created_at": "2026-09-14T12:00:00Z",
  "status": "processed"
}
```

---

## 🛠️ Design Patterns

| Pattern | Mục Đích |
|---------|----------|
| **Template Method** | `BaseCrawler` định nghĩa skeleton, subclass implement chi tiết |
| **Strategy Pattern** | Mỗi nguồn có parser riêng |
| **Factory Pattern** | Tạo crawler theo source |

---

## 📁 Cấu Trúc Project

```
data-platform/
├── src/
│   ├── crawlers/
│   │   ├── base_crawler.py      # Abstract base class
│   │   ├── config.py            # Cấu hình nguồn tin
│   │   ├── vnexpress_crawler.py
│   │   ├── tuoitre_crawler.py
│   │   ├── vietnamnet_crawler.py
│   │   └── dantri_crawler.py
│   └── services/
│       └── google_drive_service.py
├── data/
│   └── raw/                    # JSON files tạm thời
├── dags/
│   └── crawl_news_dag.py      # Airflow DAG
├── docker-compose.yml          # Airflow + PostgreSQL
├── crawl_news.py              # Main script
└── requirements-crawler.txt
```

---

## 🚀 Cách Sử Dụng

### 1. Cài Đặt

```bash
# Tạo virtual environment
python3 -m venv venv
source venv/bin/activate

# Cài dependencies
pip install -r requirements-crawler.txt
```

### 2. Chạy Crawler

```bash
# Chạy không upload Drive
python crawl_news.py --no-upload

# Chạy với upload Drive
python crawl_news.py
```

### 3. Docker (Airflow)

```bash
docker-compose up -d
# Truy cập: http://localhost:8080
# Default: admin/admin
```

---

## 🔧 Cấu Hình

### Environment Variables

```env
# Google Drive
GOOGLE_DRIVE_CREDENTIALS_FILE=./configs/google-drive-credentials.json

# Crawler Config
CRAWLER_THREADS=4
CRAWLER_RETRY_COUNT=3
CRAWLER_TIMEOUT=30

# Output
DATA_OUTPUT_PATH=./data/raw
```

---

## ➕ Thêm Nguồn Tin Mới

1. Tạo file `src/crawlers/newsource_crawler.py`
2. Kế thừa `BaseCrawler`
3. Implement các method: `get_article_urls()`, `parse_article()`
4. Thêm vào `config.py`
5. Thêm vào `CRAWLERS` dict trong `crawl_news.py`

```python
from src.crawlers.base_crawler import BaseCrawler

class NewSourceCrawler(BaseCrawler):
    name = "newsource"
    base_url = "https://newsource.com"
    
    def get_article_urls(self, category: str = None) -> List[str]:
        # Implement logic
        pass
    
    def parse_article(self, url: str) -> dict:
        # Implement logic
        pass
```
