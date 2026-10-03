# Changelog

## [2.4.0] - 2026-10-03

### Fixed — Railway không rebuild image sau push (Dockerfile root bị cache stale)

**Triệu chứng:** Sau 3 commit fix liên tiếp (lazy import `src.pipeline`, lazy `src.rag` + `src.storage`, sync root Dockerfile), container Railway vẫn dùng image build trước đó. Bot fail với traceback cũ, lazy-import code mới không bao giờ tới runtime.

**Root cause:**
1. `railway.json` trỏ `dockerfilePath: "Dockerfile"` (file ở repo root) chứ không phải `Dockerfile.railway`. Vì vậy mọi patch trên `Dockerfile.railway` không bao giờ tới Railway build.
2. `Dockerfile` (root) build tag `2026-10-02-rag-error-surfacing-v2` — quá cũ, thiếu cache-bust, thiếu CPU-only torch, thiếu `/app/data/{parquet,chroma,backups,raw_pulled}`.
3. Khi đã sync `Dockerfile`, Railway vẫn serve cached `COPY src/` layer vì `git checkout` giữ nguyên mtime → BuildKit xem source "không đổi" → trả image cũ.

**Sau fix (`cache-bust-v4`):**
- `Dockerfile` (root) ← đồng bộ với `Dockerfile.railway`: thêm CPU-only torch, cache-bust `ARG BUILD_TAG`, đủ data dirs, `ENV DATA_DIR=/app/data`
- Thêm `RUN rm -rf /app/src /app/scripts /app/configs /app/dags` ngay trước các lệnh `COPY` — đảm bảo file cũ bị xóa trước khi copy file mới. Đây là cách duy nhất invalidate COPY layer khi BuildKit xem source "không đổi"
- Bump build tag → `cache-bust-v4`

### Fixed — `ImportError: cannot import name 'Deduplicator' from partially initialized module 'src.pipeline'`

**Root cause:** `src.pipeline.__init__.py` eager-load `Deduplicator`, `Pipeline`, `get_pipeline` ngay tại import time. Khi Python đang init module mà bất kỳ submodule nào fail, toàn bộ module bị đánh dấu "partially initialized".

**Sau fix (`import-fix-v2`):**
- `src/pipeline/__init__.py`: PEP 562 lazy `__getattr__` — chỉ load submodule khi caller thực sự dùng tới attr đó
- `src/pipeline/orchestrator.py`: `try/except ImportError` quanh `from .deduplicator import ...` — graceful degradation

### Fixed — `ImportError: cannot import name 'build_store_from_gold' from 'src.rag'`

**Root cause:** `src.rag.__init__.py` và `src.storage.__init__.py` eager-load submodules tại import time → partial-init khi boot.

**Sau fix (`cache-bust-v3`):**
- `src/rag/__init__.py`: PEP 562 lazy `__getattr__` cho `VectorStore`, `build_store_from_parquet`, `build_store_from_gold`, `RAGChain`, `GeminiClient`. Chỉ giữ constant `DEFAULT_EMBED_MODEL` eager
- `src/storage/__init__.py`: cùng pattern lazy cho `CloudSink`, `GoogleDriveSink`, `LocalJsonSink`, `build_sink_from_env`, `DrivePuller`, `get_drive_puller`

## [2.3.0] - 2026-10-03

### Fixed — Drive push Gold JSON bị trống trên Drive folder

**Triệu chứng:** Crawl báo OK 282 bài, Bronze/Silver/Gold đầy đủ local, nhưng Google Drive folder từng nguồn trống trơn, không có file nào của ngày hôm nay.

**Root cause:** Code cũ (`bsg-refactor-v1`) gọi `sink.write_payload(source='VNExpress', payload=<full gold list>)` trong loop — mỗi source upload **nguyên file Gold (chứa cả 4 nguồn)** vào folder riêng của source đó. Hai vấn đề:
1. `write_payload` lúc đó gọi `_upload_json` không bọc payload thành dict, làm Drive API nhận nhầm format
2. Container Railway chưa rebuild image sau khi refactor → vẫn chạy code cũ (build tag `pull-and-use-v1`) chỉ gọi `write_batch` cũ, không phải `write_payload`

**Sau fix (`drive-push-fix-v1`):**
- Drive push chuyển **ra khỏi loop** — chỉ chạy SAU KHI cả 4 source xong
- Đọc Gold file một lần, **chia record theo `source_name`**, mỗi nguồn 1 file đúng folder
- Bọc payload thành dict `{source, layer, crawled_at, article_count, records}` cho rõ ràng
- Thêm diagnostic command `/testdrive` — kiểm tra credentials, folder_id, health_check và thử `write_payload` thật
- `/status` hiển thị thêm `Drive healthy: True/False` để biết push có khả thi không
- Log lỗi lên cả 2 channel (Python logger + digest Telegram) nếu push fail

### Added
- **`/testdrive` command** — 1 lệnh duy nhất xác định:
  - `GOOGLE_DRIVE_CREDENTIALS`/`GOOGLE_DRIVE_CREDENTIALS_PATH` có tồn tại trong container không
  - `GOOGLE_DRIVE_FOLDER_ID` có được set không
  - Sink `health_check()` có pass không
  - `write_payload()` thật sự upload được không
- Nếu `sink_ok=False` (credentials sai/token hết hạn), crawl vẫn chạy bình thường, chỉ skip Drive push + cảnh báo rõ trong log
- **Build tag**: `drive-push-fix-v1`

## [2.2.0] - 2026-10-02

### Refactor — Bronze/Silver/Gold pipeline chuẩn hoá đồng bộ

**Trước đây:** Schema classes (ArticleSchema, CrawlBatchSchema) tồn tại, 3 thư mục raw/silver/gold có sẵn, nhưng KHÔNG có orchestrator nối chúng. Mỗi entry point (crawl, pull, /index) tự gọi từng class rời rạc → dễ lệch schema, dễ quên dedup, dễ quên RAG reindex.

**Sau:** Single source of truth — `Pipeline.process_batch(source, articles)` chạy Bronze→Silver→Gold→Parquet tuần tự, idempotent, có stats cho từng layer.

### Added
- **`src/pipeline/orchestrator.py`** — class `Pipeline` + `PipelineResult` + `LayerStats` + `get_pipeline()` singleton
  - `write_bronze()` → `data/raw/raw_crawl_<ts>.json` (giữ full ArticleSchema)
  - `write_silver()` → `data/silver/silver_<YYYYMMDD>.json` (dedup theo `article_id` + content fingerprint + URL normalize; lọc quảng cáo/word_count<5)
  - `write_gold()` → `data/gold/gold_<YYYYMMDD>.json` (RAG-ready, content join title+desc+content, dedup theo `article_hash`)
  - `write_parquet()` → `data/parquet/source=X/year=Y/month=M/day=D/part-*.parquet` (skip gracefully nếu pandas không có sẵn)
  - `rebuild_index()` → /index command — build Chroma từ TẤT CẢ gold files
- **`build_store_from_gold()`** trong RAG — đọc thẳng `gold_*.json` thay vì parquet
- **CloudSink.write_payload()** — abstract method mới, cho phép push Gold JSON đã build sẵn lên Drive/Databricks
- **Telegram commands**:
  - `/status` — hiển thị Bronze/Silver/Gold/Parquet counts + breakdown crawl gần nhất
  - `/layerstats` — chi tiết file Bronze files, Silver/Gold size theo ngày, Parquet partitions theo nguồn
- **Build tag**: `bsg-refactor-v1`

### Changed
- **`CrawlerService.run_crawl_news()`** — refactor gọi `Pipeline.process_batch()` thay vì `sink.write_batch()` trực tiếp
  - Stats giờ trả về: `crawled/bronze/silver/gold/parquet/duplicates/rejected` thay vì chỉ `articles/uploaded`
  - Drive push giờ đẩy **Gold JSON** (đã dedup) thay vì raw batch
- **`DrivePuller.sync_today()`** — pull Gold batch từ Drive, parse thành ArticleSchema, đẩy qua Pipeline (cùng flow với crawl) — không còn `convert_raw_json_to_parquet` riêng lẻ
- **`cmd_index`** — reset + rebuild Chroma từ Gold layer (single source of truth) thay vì parquet
- **`src/pipeline/__init__.py`** — `parquet_writer` import lazy (môi trường không có pandas vẫn dùng được Schema/Cleaner/Dedup/Orchestrator)
- **`src/storage/cloud_sink.py`** + `databricks_sink.py` — tách `_upload_json()` private helper, dùng chung cho `write_batch` (cũ) + `write_payload` (mới)

### Verified
- ✅ Test: `Pipeline.process_batch` end-to-end: 4 articles → 4 bronze, 2 silver, 1 dedup, 1 ad-rejected, 2 gold
- ✅ Idempotency: re-run same day → 0 new silver/gold (chỉ append bronze)
- ✅ Multi-source: VNExpress + DanTri cùng ngày → gold có 3 records
- ✅ write_gold() standalone cũng idempotent

## [2.1.0] - 2026-10-02

### Added
- **DrivePuller** (`src/storage/drive_puller.py`) — kéo JSON batch từ Drive về local theo cửa sổ thời gian
- **Pull-and-Use flow** — sáng pull về dùng trong ngày, tối prune local (Drive vẫn giữ)
- Telegram command `/pull_today` — pull thủ công + reindex RAG
- Telegram command `/prune_local` — xoá local data cũ (giải phóng volume)
- Scheduled jobs: `morning_pull` (07:30), `evening_pull` (19:30), `nightly_local_prune` (23:15)

### Fixed
- Auto-crawl không đẩy data lên Drive: thêm `GOOGLE_DRIVE_CREDENTIALS_PATH` / `GOOGLE_DRIVE_CREDENTIALS` vào `.env.railway` (thiếu → fallback `LocalJsonSink`, data mất khi redeploy)
- Thêm build tag `pull-and-use-v1` để verify deploy

## [2.0.0] - 2026-10-01

### Added
- Railway deployment support
- Telegram Bot integration
- Auto-crawl scheduler
- Main service orchestrator
- Health check server

### Features
- Crawl news from 4 sources: Vnexpress, Dantri, Tuoitre, Vietnamnet
- Google Drive raw data sync
- Telegram commands for manual control
- Auto daily reports
- 24/7 cloud deployment
