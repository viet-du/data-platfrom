# Multi-Source News Crawler

**Hệ thống thu thập và lưu trữ dữ liệu tin tức đa nguồn tự động**

**Tác giả / Liên hệ**
**Email:** [duviet720@gmail.com](mailto:duviet720@gmail.com)
**Số điện thoại:** 0372876814
**GitHub:** https://github.com/viet-du/data-platfrom

---

# 1. Tổng quan dự án

**Multi-Source News Crawler** là hệ thống crawler được xây dựng để **tự động thu thập bài viết từ nhiều nguồn tin tức lớn tại Việt Nam, chuẩn hóa dữ liệu về một cấu trúc thống nhất, loại bỏ dữ liệu trùng lặp và lưu trữ dữ liệu để phục vụ các bước xử lý hoặc khai thác dữ liệu tiếp theo**.

Khác với một script crawler đơn lẻ chỉ lấy dữ liệu từ một website, dự án được tổ chức theo hướng có thể **mở rộng nhiều nguồn**, trong đó mỗi nguồn tin có crawler riêng nhưng dùng chung một kiến trúc và interface cơ sở.

Hiện tại hệ thống hỗ trợ:

* VNExpress
* Tuổi Trẻ
* VietnamNet
* Dân Trí

Pipeline được tự động hóa bằng **Apache Airflow**, các crawler có thể thực thi song song bằng **ThreadPoolExecutor**, dữ liệu được kiểm tra trùng lặp bằng hash của URL, chuẩn hóa về schema thống nhất, sau đó được ghi ra dữ liệu JSON và upload lên Google Drive theo từng nguồn.

---

# 2. Bài toán dự án giải quyết

Dữ liệu tin tức trên Internet có một số vấn đề điển hình:

* Có nhiều nguồn khác nhau.
* Mỗi website có cấu trúc HTML/RSS khác nhau.
* Cách biểu diễn metadata giữa các nguồn không đồng nhất.
* Một bài viết có thể xuất hiện lại trong nhiều lần crawl.
* Việc thu thập thủ công không ổn định và khó duy trì.
* Cần một cơ chế định kỳ để tự động chạy pipeline.

Nếu chỉ viết một script cho từng website rồi lưu dữ liệu thủ công, khi số lượng nguồn tăng lên hệ thống sẽ nhanh chóng trở nên khó quản lý.

Vì vậy, dự án giải quyết bài toán theo chuỗi:

```text
Thu thập dữ liệu
      ↓
Phân tích / Parse
      ↓
Chuẩn hóa
      ↓
Kiểm tra dữ liệu trùng
      ↓
Lưu dữ liệu
      ↓
Upload / Consumption
```

Mục tiêu quan trọng là biến một nhóm crawler rời rạc thành **một pipeline thu thập dữ liệu có tổ chức, có orchestration và có khả năng mở rộng**.

---

# 3. Mục tiêu chính

Dự án hướng tới 5 mục tiêu chính.

### 3.1. Tự động hóa

Không cần chạy crawler thủ công liên tục.

Apache Airflow được sử dụng để lập lịch pipeline theo các mốc:

```text
06:00
  ↓
Crawl

18:00
  ↓
Crawl
```

Tần suất được mô tả trong kiến trúc hiện tại là **6 giờ sáng và 18 giờ**.

---

### 3.2. Thu thập đa nguồn

Mỗi nguồn tin có một crawler riêng:

```text
VNExpress   → VNExpressCrawler
Tuổi Trẻ    → TuoiTreCrawler
VietnamNet  → VietnamNetCrawler
Dân Trí     → DanTriCrawler
```

Nhờ vậy khi thêm nguồn mới, không cần viết lại toàn bộ hệ thống.

---

### 3.3. Chuẩn hóa dữ liệu

Mặc dù dữ liệu đầu vào đến từ các nguồn khác nhau, hệ thống đưa dữ liệu về cùng một mô hình `Article`.

Ví dụ:

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

Schema này cho phép downstream xử lý dữ liệu mà không cần hiểu chi tiết từng website.

---

### 3.4. Loại bỏ dữ liệu trùng

Sau khi crawler lấy dữ liệu, hệ thống thực hiện **Deduplication bằng hash của URL**.

Luồng:

```text
Article URL
    ↓
Hash URL
    ↓
So sánh
    ↓
Đã tồn tại? ── Yes ──→ Loại bỏ
    │
    No
    ↓
Tiếp tục pipeline
```

Cơ chế này giúp giảm việc lưu lặp cùng một bài viết trong các lần crawl.

---

### 3.5. Dễ mở rộng

Kiến trúc được xây dựng dựa trên `BaseCrawler`, vì vậy một nguồn mới chỉ cần kế thừa lớp cơ sở và triển khai logic riêng cho nguồn đó.

Điều này giúp hệ thống có thể phát triển từ:

```text
4 nguồn
```

thành:

```text
10 nguồn
     ↓
20 nguồn
     ↓
Nhiều nguồn hơn
```

mà không cần thay đổi kiến trúc lõi.

---

# 4. Nguồn dữ liệu

Hiện tại hệ thống hỗ trợ 4 nguồn tin.

| Nguồn      | Cơ chế đầu vào | Thư mục           |
| ---------- | -------------- | ----------------- |
| VNExpress  | RSS            | `vnexpress-news`  |
| Tuổi Trẻ   | RSS            | `tuoitre-news`    |
| VietnamNet | RSS            | `vietnamnet-news` |
| Dân Trí    | HTML           | `dantri-news`     |

Ba nguồn đầu tiên sử dụng RSS trong data architecture hiện tại, trong khi Dân Trí sử dụng HTML parsing.

Điểm quan trọng ở đây là **pipeline không giả định mọi website có cùng cách cung cấp dữ liệu**.

Ví dụ:

```text
VNExpress
RSS
  ↓
Parser
  ↓
Article

Dân Trí
HTML
  ↓
HTML Parser
  ↓
Article
```

Nhưng cả hai cuối cùng đều đưa về cùng một schema:

```text
Article
```

Đây là nguyên tắc quan trọng của hệ thống.

---

# 5. Kiến trúc tổng thể

## 5.1. System Architecture

Kiến trúc hệ thống có thể hiểu đơn giản theo 4 lớp:

```text
                 ┌──────────────────┐
                 │     AIRFLOW      │
                 │    Scheduler     │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │    EXECUTOR      │
                 │  ThreadPool      │
                 └────────┬─────────┘
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
     VNExpress         Tuổi Trẻ       VietnamNet
     Crawler           Crawler         Crawler
          │               │                │
          └───────────────┼────────────────┘
                          │
                          ▼
                    Dân Trí Crawler
                          │
                          ▼
                  ┌───────────────┐
                  │ Dedup Check   │
                  │ URL Hash      │
                  └───────┬───────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ Normalize &   │
                  │ Validate      │
                  └───────┬───────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ JSON Storage  │
                  └───────┬───────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ Google Drive  │
                  └───────────────┘
```

Kiến trúc này được mô tả trong tài liệu gốc với ba thành phần điều phối chính: **Scheduler → Executor → Storage**, sau đó phân nhánh thành các crawler và đi qua deduplication, normalization/validation và upload.

---

# 6. Hiểu hệ thống theo tư duy Data Engineering

Nếu một người mới vào dự án, có thể hiểu pipeline như sau:

```text
SOURCE
  ↓
INGESTION
  ↓
PARSING
  ↓
NORMALIZATION
  ↓
DEDUPLICATION
  ↓
STORAGE
  ↓
CONSUMPTION
```

Trong đó:

### Source

Nơi dữ liệu gốc tồn tại:

```text
VNExpress
Tuổi Trẻ
VietnamNet
Dân Trí
```

### Ingestion

Crawler lấy dữ liệu từ source.

### Parsing

Chuyển RSS/HTML thành dữ liệu có cấu trúc.

### Normalization

Đưa dữ liệu của mọi nguồn về cùng schema.

### Deduplication

Kiểm tra bài viết đã tồn tại hay chưa.

### Storage

Ghi dữ liệu thành JSON và upload.

### Consumption

Dữ liệu sau đó có thể được dùng cho những hệ thống downstream khác.

---

# 7. Data Flow chi tiết

## Bước 1 – Scheduler

Apache Airflow kích hoạt pipeline theo lịch:

```text
06:00
18:00
```

Airflow đảm nhiệm orchestration thay vì để người dùng chạy script thủ công.

---

## Bước 2 – Parallel Fetch

Sau khi pipeline được kích hoạt, các crawler có thể chạy song song thông qua `ThreadPoolExecutor`.

Ví dụ:

```text
Thread 1 → VNExpress
Thread 2 → Tuổi Trẻ
Thread 3 → VietnamNet
Thread 4 → Dân Trí
```

Tài liệu mô tả cơ chế executor ở khoảng **4–8 threads**, còn ví dụ data flow minh họa 4 thread tương ứng với 4 nguồn.
Lý do sử dụng parallel execution là vì các nguồn là các tác vụ I/O-bound: hệ thống phải chờ network response khi gửi HTTP request.

---

# 8. Parsing

Mỗi crawler chịu trách nhiệm hiểu cấu trúc của nguồn mà nó thu thập.

Ví dụ:

```text
RSS
 ↓
Parse XML / RSS
 ↓
Extract fields

HTML
 ↓
Parse DOM
 ↓
Extract fields
```

Sau khi parsing, dữ liệu chưa cần giống hoàn toàn về cách lấy, nhưng phải chuyển về cùng một object `Article`.

---

# 9. Normalization

Đây là bước rất quan trọng.

Giả sử:

```text
Nguồn A:
published
```

Trong khi:

```text
Nguồn B:
pubDate
```

Crawler sẽ chuyển về:

```text
published_at
```

Tương tự:

```text
title
content
url
author
category
tags
```

được chuẩn hóa thành một schema thống nhất.

Tài liệu kiến trúc mô tả trực tiếp bước **Normalize & Validate – Chuẩn hóa schema**.

---

# 10. Deduplication

Sau khi chuẩn hóa, hệ thống kiểm tra duplicate.

Cách tiếp cận hiện tại:

```text
URL
 ↓
Hash
 ↓
article_id / duplicate key
```

Ví dụ:

```text
https://vnexpress.net/example-article
```

được hash thành một định danh:

```text
abc123hash...
```

Nếu cùng URL xuất hiện ở các lần chạy tiếp theo, hệ thống có thể phát hiện đó là bài viết đã từng thu thập.

---

# 11. Storage Architecture

Dữ liệu hiện được tổ chức theo các lớp:

```text
RAW DATA
   ↓
PROCESSED DATA
   ↓
CONSUMPTION
```

Tài liệu mô tả:

### Raw Data Layer

Chứa dữ liệu JSON/HTML chưa xử lý.

### Processed Layer

Chứa dữ liệu đã:

* cleaned
* normalized

### Consumption Layer

Sử dụng Google Drive/GCS trong sơ đồ kiến trúc tài liệu; implementation hiện tại có `GoogleDriveService` và pipeline upload theo thư mục từng nguồn.
Trong tài liệu vận hành, Google Drive là nơi lưu dữ liệu theo source folder:

```text
vnexpress-news/
tuoitre-news/
vietnamnet-news/
dantri-news/
```

---

# 12. Data Model

Entity trung tâm của hệ thống là:

```text
Article
```

Các trường chính:

| Field          | Ý nghĩa                      |
| -------------- | ---------------------------- |
| `source_id`    | ID nguồn                     |
| `source_name`  | Tên nguồn                    |
| `url`          | URL bài viết                 |
| `article_id`   | ID/hash định danh            |
| `title`        | Tiêu đề                      |
| `description`  | Mô tả                        |
| `content`      | Nội dung                     |
| `author`       | Tác giả                      |
| `published_at` | Thời điểm xuất bản           |
| `category`     | Danh mục                     |
| `tags`         | Danh sách tag                |
| `created_at`   | Thời điểm crawler tạo record |
| `status`       | Trạng thái xử lý             |

Schema đầy đủ được định nghĩa trong tài liệu dự án.

---

# 13. OOP Architecture

Một trong những điểm đáng chú ý của dự án là crawler không được viết theo kiểu mỗi file là một script hoàn toàn độc lập.

Thay vào đó có một abstract class:

```text
BaseCrawler
```

và các crawler cụ thể kế thừa:

```text
                  BaseCrawler
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
     VNExpress      Tuổi Trẻ    VietnamNet
       Crawler       Crawler      Crawler
          │
          ▼
       Dân Trí
       Crawler
```

BaseCrawler cung cấp các thành phần chung như:

```text
name
base_url
categories
crawl()
parse_article()
fetch()
parse_list()
```

Các crawler con chỉ tập trung vào logic đặc thù của website.

Kiến trúc này được thể hiện trực tiếp trong tài liệu OOP của dự án.

---

# 14. Design Patterns

Dự án sử dụng ba design pattern chính.

## 14.1. Template Method

`BaseCrawler` định nghĩa skeleton chung của crawler.

Subclass triển khai phần chi tiết.

```text
BaseCrawler
    │
    ├── workflow chung
    │
    └── chi tiết source-specific
```

---

## 14.2. Strategy Pattern

Mỗi nguồn có parser/logic xử lý riêng.

Ví dụ:

```text
VNExpress Strategy
Tuổi Trẻ Strategy
VietnamNet Strategy
Dân Trí Strategy
```

Tài liệu xác định Strategy Pattern được dùng để tách parser theo từng nguồn.

---

## 14.3. Factory Pattern

Factory được dùng để tạo crawler tương ứng với source.

Ví dụ về mặt tư duy:

```text
source = "vnexpress"
        ↓
Crawler Factory
        ↓
VNExpressCrawler
```

Điều này giúp phần orchestrator không phải tự biết cách khởi tạo từng class cụ thể.

---

# 15. Google Drive Service

Hệ thống có một service chuyên trách giao tiếp với Google Drive:

```text
GoogleDriveService
```

Các chức năng chính:

```text
authenticate()
create_folder()
upload_json()
upload_batch()
```

Việc tách service riêng giúp crawler không phải trực tiếp xử lý logic authentication và upload.

Kiến trúc:

```text
Crawler
   ↓
Data
   ↓
GoogleDriveService
   ↓
Google Drive
```

Như vậy storage concern được tách khỏi crawling concern.

---

# 16. Cấu trúc project

Cấu trúc project hiện tại:

```text
data-platform/
│
├── src/
│   ├── crawlers/
│   │   ├── base_crawler.py
│   │   ├── config.py
│   │   ├── vnexpress_crawler.py
│   │   ├── tuoitre_crawler.py
│   │   ├── vietnamnet_crawler.py
│   │   └── dantri_crawler.py
│   │
│   └── services/
│       └── google_drive_service.py
│
├── data/
│   └── raw/
│
├── dags/
│   └── crawl_news_dag.py
│
├── docker-compose.yml
├── crawl_news.py
└── requirements-crawler.txt
```

Cấu trúc này được mô tả trong tài liệu project.

---

# 17. Trách nhiệm của từng thư mục

## `src/crawlers/`

Đây là khu vực chứa logic crawling.

### `base_crawler.py`

Lớp trừu tượng dùng chung cho mọi crawler.

### `vnexpress_crawler.py`

Logic riêng cho VNExpress.

### `tuoitre_crawler.py`

Logic riêng cho Tuổi Trẻ.

### `vietnamnet_crawler.py`

Logic riêng cho VietnamNet.

### `dantri_crawler.py`

Logic riêng cho Dân Trí.

### `config.py`

Lưu cấu hình nguồn.

---

## `src/services/`

Chứa các service dùng chung của hệ thống.

Hiện tại có:

```text
google_drive_service.py
```

chịu trách nhiệm giao tiếp với Google Drive.

---

## `dags/`

Chứa Airflow DAG.

File chính:

```text
crawl_news_dag.py
```

Đây là nơi định nghĩa workflow automation.

---

## `data/raw/`

Chứa dữ liệu raw JSON trong quá trình crawler chạy.

---

# 18. Cách chạy project

## Bước 1 – Tạo virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Bước 2 – Cài dependency

```bash
pip install -r requirements-crawler.txt
```

Các bước cài đặt này được ghi trong tài liệu dự án.

---

## Bước 3 – Chạy crawler không upload Drive

```bash
python crawl_news.py --no-upload
```

Mục đích:

* Kiểm tra crawler.
* Kiểm tra parsing.
* Kiểm tra output.
* Không phụ thuộc upload service.

---

## Bước 4 – Chạy crawler có upload

```bash
python crawl_news.py
```

Khi đó dữ liệu được đưa qua pipeline upload.

---

# 19. Chạy với Docker / Airflow

Có thể khởi động môi trường Airflow thông qua Docker:

```bash
docker-compose up -d
```

Sau đó truy cập:

```text
http://localhost:8080
```

Thông tin này được ghi trong phần hướng dẫn Docker của project.

---

# 20. Configuration

Một số biến môi trường chính:

```env
# Google Drive
GOOGLE_DRIVE_CREDENTIALS_FILE=./configs/google-drive-credentials.json

# Crawler
CRAWLER_THREADS=4
CRAWLER_RETRY_COUNT=3
CRAWLER_TIMEOUT=30

# Output
DATA_OUTPUT_PATH=./data/raw
```

Ý nghĩa:

### `CRAWLER_THREADS`

Số lượng thread dùng cho parallel crawling.

### `CRAWLER_RETRY_COUNT`

Số lần retry khi request/crawler gặp lỗi.

### `CRAWLER_TIMEOUT`

Thời gian timeout cho request.

### `DATA_OUTPUT_PATH`

Đường dẫn lưu dữ liệu raw.

---

# 21. Khi một crawler bị lỗi thì phải suy luận ở đâu?

Đây là phần quan trọng cho người mới tham gia project.

Giả sử:

```text
VNExpress chạy
Tuổi Trẻ chạy
VietnamNet lỗi
Dân Trí chạy
```

Không nên kiểm tra toàn bộ project một cách ngẫu nhiên.

Hãy suy luận theo pipeline:

```text
Source
  ↓
Crawler
  ↓
Parser
  ↓
Normalization
  ↓
Dedup
  ↓
Storage
```

Sau đó xác định lỗi thuộc tầng nào.

### Trường hợp 1 – Không lấy được URL

Kiểm tra:

```text
get_article_urls()
```

### Trường hợp 2 – Lấy được URL nhưng không parse được

Kiểm tra:

```text
parse_article()
```

### Trường hợp 3 – Parse đúng nhưng schema sai

Kiểm tra:

```text
normalize / validation
```

### Trường hợp 4 – Dữ liệu đúng nhưng không upload

Kiểm tra:

```text
GoogleDriveService
authentication
upload_json()
upload_batch()
```

### Trường hợp 5 – Script chạy được nhưng Airflow không chạy

Kiểm tra:

```text
crawl_news_dag.py
Docker
Airflow scheduler
task execution
```

Cách debug này giúp người mới hiểu hệ thống theo **flow của dữ liệu**, thay vì đọc code một cách tuyến tính.

---

# 22. Cách thêm một nguồn báo mới

Đây là một trong những đặc điểm quan trọng nhất của kiến trúc.

Giả sử muốn thêm:

```text
Example News
```

Không cần sửa lại toàn bộ crawler.

Thực hiện:

### Bước 1

Tạo:

```text
src/crawlers/newsource_crawler.py
```

### Bước 2

Kế thừa:

```python
from src.crawlers.base_crawler import BaseCrawler
```

### Bước 3

Tạo class:

```python
class NewSourceCrawler(BaseCrawler):
    name = "newsource"
    base_url = "https://newsource.com"
```

### Bước 4

Implement:

```python
get_article_urls()
parse_article()
```

### Bước 5

Thêm cấu hình trong:

```text
config.py
```

### Bước 6

Đăng ký crawler vào:

```text
CRAWLERS
```

trong:

```text
crawl_news.py
```

Đây chính là quy trình mở rộng nguồn được mô tả trong tài liệu dự án.

---

# 23. Tại sao kiến trúc này dễ mở rộng?

Có thể nhìn architecture theo nguyên tắc:

```text
COMMON LOGIC
     │
     ▼
BaseCrawler
     │
     ├───────────────┬───────────────┬───────────────┐
     ▼               ▼               ▼               ▼
VNExpress        Tuổi Trẻ       VietnamNet       Dân Trí
```

Thay vì:

```text
crawl_vnexpress.py
crawl_tuoitre.py
crawl_vietnamnet.py
crawl_dantri.py
```

và mỗi file chứa một logic hoàn toàn khác nhau.

Cách tổ chức hiện tại giúp:

* giảm code duplication;
* chuẩn hóa interface;
* dễ test;
* dễ thêm source;
* dễ bảo trì;
* tách logic chung và logic đặc thù.

---

# 24. Data Lifecycle

Toàn bộ vòng đời của một bài viết có thể được hình dung như sau:

```text
                 INTERNET
                    │
                    ▼
              NEWS WEBSITE
                    │
                    ▼
               CRAWLER
                    │
                    ▼
                 PARSER
                    │
                    ▼
               ARTICLE
                    │
                    ▼
             NORMALIZATION
                    │
                    ▼
              VALIDATION
                    │
                    ▼
             DEDUPLICATION
                    │
                    ▼
                RAW JSON
                    │
                    ▼
             GOOGLE DRIVE
                    │
                    ▼
             DOWNSTREAM USE
```

Đây là cách một người mới có thể đọc architecture và suy ra toàn bộ pipeline mà không cần đọc từng dòng code trước.

---

# 25. Nguyên tắc thiết kế

Dự án được tổ chức xoay quanh một số nguyên tắc:

### Separation of Concerns

Crawler không nên đồng thời chịu trách nhiệm cho toàn bộ storage logic.

```text
Crawler
  ↓
Data
  ↓
Service
  ↓
Storage
```

### Reusability

Logic chung đặt trong `BaseCrawler`.

### Extensibility

Nguồn mới có thể được thêm bằng subclass.

### Maintainability

Mỗi thành phần có trách nhiệm riêng.

### Automation

Airflow chịu trách nhiệm scheduling/orchestration.

---

# 26. Những gì dự án hiện tại đã giải quyết

Từ góc nhìn Data Engineering, hệ thống hiện tại đã thể hiện các thành phần:

```text
Data Source
      ↓
Data Ingestion
      ↓
Parallel Processing
      ↓
Parsing
      ↓
Normalization
      ↓
Deduplication
      ↓
Raw / Processed Data
      ↓
Cloud Storage
      ↓
Workflow Orchestration
```

## Các thành phần này được thể hiện trực tiếp trong architecture và data flow của project.

# 27. Hướng phát triển

Kiến trúc hiện tại tạo nền tảng để tiếp tục mở rộng sang một Data Platform hoàn chỉnh hơn.

Một số hướng phát triển tự nhiên của hệ thống:

```text
Current Crawler
      ↓
Data Lake
      ↓
ETL / ELT
      ↓
Data Warehouse
      ↓
Analytics
      ↓
Machine Learning
      ↓
AI / RAG
```

Ở giai đoạn hiện tại, phần đã được triển khai và tài liệu hóa rõ nhất là **multi-source ingestion, crawler abstraction, deduplication, normalization, local/cloud storage và Airflow orchestration**. Các tầng phía sau có thể được xây dựng tiếp mà không cần phá bỏ kiến trúc crawler hiện tại.

---

# 28. Project Summary

Nếu phải mô tả dự án trong một đoạn ngắn:

> **Multi-Source News Crawler là hệ thống Data Ingestion Pipeline tự động thu thập dữ liệu từ nhiều nguồn tin tức Việt Nam, sử dụng Apache Airflow để orchestration, ThreadPoolExecutor để thực thi crawler song song, áp dụng kiến trúc OOP với BaseCrawler và các design pattern như Template Method, Strategy và Factory, sau đó thực hiện parsing, normalization, deduplication và lưu trữ dữ liệu theo từng nguồn trên Google Drive.**

---

# 29. Skills được thể hiện qua dự án

Dự án thể hiện các kỹ năng:

**Programming**

* Python
* Object-Oriented Programming
* Abstract Class
* Design Patterns

**Data Engineering**

* Data Ingestion
* ETL Pipeline
* Data Normalization
* Deduplication
* Data Storage
* Workflow Orchestration

**Automation**

* Apache Airflow
* Scheduled Pipeline
* Parallel Execution
* Retry / Timeout Configuration

**Data Source Processing**

* RSS Parsing
* HTML Parsing
* Multi-source Crawling

**Cloud / Storage**

* Google Drive API
* Cloud Storage concept

**Software Engineering**

* Separation of Concerns
* Reusable Components
* Extensible Architecture
* Configuration Management
* Docker

---

# 30. Thông tin liên hệ

**Dự án:** Multi-Source News Crawler
**Định hướng:** Data Engineering / Data Platform

**GitHub:**
https://github.com/viet-du/data-platfrom

**Email:**
[duviet720@gmail.com](mailto:duviet720@gmail.com)

**Số điện thoại:**
0372876814

---

# 31. Quick Start cho người mới vào project

Nếu một developer/Data Engineer mới tham gia, thứ tự đọc đề xuất là:

```text
1. README / Project Overview
           ↓
2. System Architecture
           ↓
3. Data Flow
           ↓
4. BaseCrawler
           ↓
5. Một crawler cụ thể
           ↓
6. crawl_news.py
           ↓
7. GoogleDriveService
           ↓
8. Airflow DAG
           ↓
9. Configuration
           ↓
10. Run thử pipeline
```

Sau khi hiểu 10 bước này, developer có thể trả lời được 5 câu hỏi quan trọng:

```text
1. Dữ liệu đến từ đâu?
2. Dữ liệu được crawl như thế nào?
3. Dữ liệu được chuẩn hóa ra sao?
4. Dữ liệu được lưu ở đâu?
5. Muốn thêm một nguồn mới thì phải sửa những gì?
```

Đó cũng là cách tốt nhất để onboarding một thành viên mới vào dự án: **hiểu data flow trước, hiểu architecture sau, rồi mới đi sâu vào implementation.**
Liên hệ: duviet720@gmail.com · 0372876814 ·
