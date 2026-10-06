# Multi-Source Vietnamese News Crawler — Tổng quan dự án

> Tài liệu mô tả toàn bộ project, dùng để trình bày trên LinkedIn (Featured / About / post dài).
> Giọng văn: chuyên nghiệp, có chiều sâu kỹ thuật, không hoa mỹ.

---

## Tóm tắt 60 giây

Một data platform production-ready, event-driven, tự động thu thập tin tức từ
4 báo lớn Việt Nam (VNExpress, Tuổi Trẻ, VietnamNet, Dân Trí), loại bỏ trùng
lặp, làm sạch và chuẩn hoá theo mô hình Lakehouse Bronze → Silver → Gold,
sau đó cung cấp một chatbot RAG hỏi đáp bằng tiếng Việt trên chính kho dữ
liệu đó. Toàn bộ hệ thống deploy lên Railway bằng một lần push, có Telegram
bot để vận hành, có HTTP debug endpoint để xử lý sự cố.

---

## 1. Bài toán thực tế

Tin tức Việt Nam phân mảnh trên 4+ nhà xuất bản lớn, mỗi nơi một schema RSS
riêng, một kiểu HTML khác nhau, có nơi đặt paywall, có nơi giấu feed. Để
gom lại thành một kho dữ liệu có thể truy vấn, đã dedupe, sẵn sàng cho
phân tích và cho AI, thông thường mất vài tuần chỉ để viết glue code. Dự
án này làm điều đó bằng cron 6 giờ một lần, không cần con người can
thiệp, sau đó cho phép hỏi đáp bằng ngôn ngữ tự nhiên trên kho dữ liệu
kết quả.

---

## 2. Kiến trúc end-to-end (toàn bộ pipeline)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                  data-platfrom — KIẾN TRÚC END-TO-END                         │
└──────────────────────────────────────────────────────────────────────────────┘

[ TẦNG KÍCH HOẠT ]
    │   • Airflow DAG (dags/crawl_news_dag.py)  — cron 6h & 18h
    │   • Telegram bot polling                 — lệnh /crawl, /status theo yêu cầu
    │   • HTTP endpoint /crawl                 — kick-off thủ công
    ▼
[ TẦNG THU THẬP — src/crawlers/ ]
    │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐
    │   │ VNExpressCrawl  │  │ TuoiTreCrawler  │  │ VietnamNetCrawl │  │ DanTriCrawler│
    │   │  (RSS)          │  │  (RSS)          │  │  (RSS)          │  │ (HTML)       │
    │   └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └──────┬───────┘
    │            └────────────┬───────┴────────────┬───────┴─────────────────┘
    │                         ▼                    ▼
    │              ThreadPoolExecutor (4–8 worker) — fan-out đồng thời
    ▼
[ BRONZE — JSON thô, chưa transform, partition theo nguồn & giờ crawl ]
    │   data/bronze/<source>/<YYYY-MM-DD>/<HH>h.json
    │   schema: { url, raw_html, fetched_at }   ← cố tình tối giản
    ▼
[ DEDUP — src/pipeline/deduplicator.py ]
    │   Hash(url) ∪ Hash(title_normalized) — cả hai phải trượt mới nhận
    │   State lưu vào data/_state/seen_urls.parquet (chống crash)
    ▼
[ SILVER — đã làm sạch, schema-validated, dedupe, gắn nhãn nguồn ]
    │   data/silver/<source>/<YYYY-MM-DD>/<HH>h.parquet
    │   schema: Article (url, title, description, content, author, published_at,
    │                    category, source_id, source_name, article_id, …)
    │   src/pipeline/cleaner.py   — strip HTML, chuẩn hoá Unicode, lang detect
    │   src/pipeline/schema.py    — Pandera validation
    │   src/pipeline/parquet_writer.py — PyArrow partitioned writer
    ▼
[ GOLD — cấp doanh nghiệp, đã aggregate, sẵn sàng cho ML/RAG ]
    │   data/gold/<YYYY-MM-DD>/articles.parquet
    │   • Union 4 nguồn, một schema canonical duy nhất
    │   • Đếm số bài theo nguồn + tổng
    │   • Tên cột snake_case, timestamp ISO-8601
    │   src/pipeline/orchestrator.py — điều phối chuỗi Bronze→Silver→Gold
    ▼
[ STORAGE SINKS — src/storage/cloud_sink.py + drive_puller.py ]
    │   ┌────────────────────┐    ┌────────────────────┐
    │   │  LocalJsonSink     │    │  GoogleDriveSink    │
    │   │  (luôn chạy)       │    │  (tuỳ chọn, bật/tắt) │
    │   └─────────┬──────────┘    └──────────┬──────────┘
    │             │                          │
    │             └────────────┬─────────────┘
    │                          ▼
    │              Google Drive folder theo từng nguồn:
    │              vnexpress-news/, tuoitre-news/, vietnamnet-news/, dantri-news/
    │              ↑ Retry với exponential backoff + dead-letter retry queue
    │              ↑ src/storage/retry_queue.py
    ▼
[ DATALAKE EXPORT — src/storage/databricks_sink.py ]
    │   Tuỳ chọn: đẩy Gold parquet lên Databricks (DBFS / S3) theo lịch
    ▼
[ TẦNG TIÊU THỤ — src/rag/ ]
    │   ┌────────────────────────────────────────────────────┐
    │   │  vector_store.py   — ChromaDB + sentence-transformers │
    │   │                     (paraphrase-multilingual-MiniLM)   │
    │   │  persistent_store.py — incremental upsert (không rebuild)│
    │   │  qa_chain.py       — Gemini 2.5 Flash RAG chain       │
    │   │  Gemini client     — tiếng Việt, top-k=5, có citation │
    │   └────────────────────────────────────────────────────┘
    │   ↳ Telegram /ask, /asklong — chat với kho tin tức
    ▼
[ TẦNG VẬN HÀNH ]
    │   • Telegram bot — /status, /crawl, /ask, /asklong, /logs, /testdrive
    │   • HTTP debug    — /debug/env, /debug/health, /testdrive, /crawl
    │   • Railway cron  — tự redeploy khi push, lịch 6h
    │   • Logs          — JSON-line structured, pipe ra /logs
    ▼
[ TRIỂN KHAI ]
        Railway.app — một Dockerfile, Volume persistent mount tại /app/data
        Secrets đổ qua env (không có credentials trong repo, .gitignore đã chặn)
```

---

## 3. Tech stack

| Tầng                | Công cụ                                              |
|---------------------|------------------------------------------------------|
| Ngôn ngữ            | Python 3.11                                          |
| Orchestration       | Apache Airflow (DAG) + aiohttp self-hosted scheduler|
| Đồng thời           | `concurrent.futures.ThreadPoolExecutor`              |
| Validation          | Pandera                                              |
| Storage (parquet)   | PyArrow                                              |
| Vector store        | ChromaDB (persistent) + sentence-transformers        |
| LLM                 | Google Gemini 2.5 Flash                              |
| Embedding           | `paraphrase-multilingual-MiniLM-L12-v2`              |
| Cloud               | Google Drive API v3, Databricks DBFS                 |
| Bot                 | python-telegram-bot (polling)                        |
| Triển khai          | Railway (Docker, persistent volume)                  |
| CI                  | GitHub Actions (lint + smoke test)                   |

Toàn bộ dependency khai trong `requirements.txt`; dùng torch CPU-only để image
dưới 1.5 GB.

---

## 4. Cấu trúc repo (nhìn từ GitHub)

```
data-platfrom/
├── dags/                    # Airflow DAG
├── src/
│   ├── crawlers/            # VNExpress, Tuổi Trẻ, VietnamNet, Dân Trí
│   ├── pipeline/            # Orchestrator Bronze→Silver→Gold
│   ├── storage/             # Local, Drive, Databricks sinks + retry queue
│   ├── rag/                 # Vector store + Gemini QA chain
│   ├── services/            # GoogleDriveService (auth, upload, folder)
│   └── utils/               # credentials resolver, logging
├── scripts/                 # telegram_digest, main_service, set_railway_secret
├── configs/                 # client_secret.json (OAuth), Drive creds
├── docs/                    # architecture/, pipelines/, runbooks/, adr/
├── data/                    # Lakehouse local (đã gitignore)
├── Dockerfile               # ← bản build production (CPU torch, cache-bust)
├── Dockerfile.crawler       # image Airflow dev local
├── docker-compose.yml       # stack local
├── railway.json             # config deploy
└── CHANGELOG.md             # postmortem sự cố theo version
```

---

## 5. Quyết định kỹ thuật đáng chú ý

### 5.1 Lakehouse Bronze / Silver / Gold trên một máy
- **Bronze** = raw, trung thành với nguồn. Nếu parser thay đổi, có thể suy
  ra lại Silver mà không cần crawl lại.
- **Silver** = đã làm sạch + đã validate. Một dòng / bài viết, schema được
  Pandera enforce.
- **Gold** = source-agnostic, một bảng union duy nhất. Tầng RAG chỉ đọc Gold.

Sao không ghi thẳng vào Gold? Vì khi VietnamNet đổi cấu trúc RSS (chuyện
này xảy ra), Bronze là nút rewind. Suy ra lại Silver từ Bronze mất vài
giây; crawl lại một tuần tin mất 6 ngày cron.

### 5.2 Hybrid event-driven + cron
Bot có lệnh `/crawl` để chạy theo yêu cầu (rất tiện khi debug parser), nhưng
lưu lượng production là lịch Airflow 6h/18h. Run lỗi không chặn run sau —
retry queue hấp thụ các lỗi Drive/DBFS thoáng qua.

### 5.3 PEP 562 — lazy `__getattr__` cho module init
Sau một lần partial-init crash trên Railway
(`ImportError: cannot import name 'X' from partially initialized module
'src.pipeline'`), tất cả package ở hot-path được refactor sang lazy
attribute resolution. Khởi động không còn fail vì lỗi submodule không
liên quan; lỗi surface ngay tại call site kèm traceback rõ ràng.

### 5.4 Cache-bust Docker trên Railway
BuildKit content-hash caching là một cái bẫy khi `git checkout` giữ
nguyên mtime. Dockerfile bây giờ `RUN rm -rf` thư mục nguồn trước
`COPY` và dùng `ARG BUILD_TAG` để invalidate cứng. Mỗi deploy được
tag `cache-bust-vN`.

### 5.5 Secrets chỉ qua môi trường
Google service-account JSON nằm trong `GOOGLE_DRIVE_CREDENTIALS_JSON`
(hoặc `GOOGLE_DRIVE_CREDENTIALS_PATH`), không bao giờ trong repo.
`.gitignore` đã chặn `gen-lang-client-*.json`; nếu lỡ lọt vào thì
`git filter-repo` history scrub là quy trình khôi phục tiêu chuẩn.

### 5.6 RAG stack: Chroma + multilingual MiniLM + Gemini 2.5 Flash
- MiniLM giữ embedder dưới 500 MB và chạy tốt với tiếng Việt.
- Chroma persistent nghĩa là re-deploy không mất index.
- Gemini 2.5 Flash đủ nhanh cho latency polling của Telegram.
- QA chain trích dẫn nguồn theo `source_name + url`, để người dùng
  verify được.

### 5.7 Thiết kế vận hành
- **Tự chẩn đoán**: `/debug/env` báo cáo secret nào đang có mà không in
  giá trị; `/testdrive` làm roundtrip Drive thật; `/status` báo số bài
  theo nguồn + tình trạng Drive.
- **Telegram digest**: một tin nhắn duy nhất mỗi cron run, có count,
  lỗi, link retry — không cần mở log Railway cho việc kiểm tra thường
  ngày.
- **Runbook**: `docs/runbooks/daily-checklist.md`, `troubleshooting.md`,
  `backup-recovery.md` — mỗi failure mode lặp lại đều có recovery
  document sẵn.

---

## 6. Mở rộng thực tế

1. **Thêm nguồn mới** (ví dụ Thanh Niên, Zing): viết
   `thanh_nien_crawler.py` extend `BaseCrawler` — orchestrator tự wire vào.
   Khoảng 80–150 dòng bao gồm cả test.
2. **Cải thiện cleaning**: sửa `src/pipeline/cleaner.py` — Bronze được giữ
   nguyên, suy ra lại Silver + Gold bằng một lệnh.
3. **Đổi LLM**: `src/rag/qa_chain.py` expose interface `GeminiClient`;
   thay bằng Claude hoặc GPT-4o trong một file.
4. **Chuyển khỏi Railway**: `Dockerfile` portable; chỉ cần mount persistent
   volume và inject cùng env var.

---

## 7. Bài học rút ra khi vận hành production

- **Cache invalidation là bài toán khó nhất trong thực tế.** BuildKit
  content-hash caching lặng lẽ trả về image cũ khi mtime không đổi sau
  `git checkout`. Fix là bust qua `ARG` hoặc `rm -rf` đích trước `COPY`.
  Tốn 4 deploy cycle mới học được.
- **Partial-init error là class lỗi tệ nhất của Python.** Một lỗi ở bất
  kỳ submodule nào giết luôn `from package import *`. PEP 562 lazy
  `__getattr__` là cách sạch nhất, nhưng phải viết boilerplate cho từng
  package.
- **RAG production bắt buộc có source citation, nếu không không ai tin.**
  Trả về câu trả lời 5 đoạn không kèm provenance thì trông rất tự tin
  và gần như chắc chắn là hallucination. QA chain bây giờ luôn trả về
  `(answer, [sources])`.
- **Cron không có heartbeat là hố đen.** Thêm Telegram digest biến lỗi
  im lặng thành thấy được trong vòng 30 phút, thay vì "tuần trước thấy
  dữ liệu hơi cũ".

---

## 8. Số liệu production gần nhất

- **4 nguồn** crawl đồng thời trong ~45 giây
- **282 bài** ingest, 0 trùng, 0 lỗi schema
- **~3.2 MB** Silver parquet, **~0.8 MB** Gold parquet
- **4 Drive push** thành công lần đầu
- **~9 giây** end-to-end từ cron trigger đến RAG-ready

---

## 9. Repo & liên hệ

- Repo: `github.com/<your-handle>/data-platfrom`
- License: MIT
- Stack: Python · Airflow · PyArrow · ChromaDB · Gemini · Telegram · Railway

Nếu bạn đang làm về NLP tiếng Việt, tổng hợp tin tức, hoặc đơn giản
muốn xem một Lakehouse + RAG system nhỏ nhưng chạy thật trên
production, mình sẵn sàng trao đổi.
