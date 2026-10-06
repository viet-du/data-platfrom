# Multi-Source Vietnamese News Crawler — Project Overview

> LinkedIn-ready project description (English, long-form, end-to-end narrative).
> Tài liệu này dùng để paste lên LinkedIn (Featured / About / post). Phiên bản gốc
> tiếng Việt ở cuối file.

---

## TL;DR (60-second pitch)

A production-grade, event-driven data platform that automatically collects, dedupes,
cleans, and structures Vietnamese news from 4 major publishers (VNExpress, Tuổi Trẻ,
VietnamNet, Dân Trí), persists them through a Bronze → Silver → Gold Lakehouse, and
exposes a Vietnamese-language RAG assistant over the resulting corpus — all deployable
to Railway with one push, with a Telegram bot for ops and a debug HTTP endpoint for
incident triage.

---

## 1. What problem it solves

Vietnamese news is fragmented across 4+ major publishers, each with their own RSS
schema, HTML quirks, and paywall logic. Aggregating them into a queryable, deduplicated,
analytics-ready corpus normally takes weeks of glue code. This project does it on a
6-hour cron with zero human intervention, then lets you ask natural-language questions
against the result.

---

## 2. End-to-end architecture (the whole pipeline)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                  data-platfrom — END-TO-END ARCHITECTURE                      │
└──────────────────────────────────────────────────────────────────────────────┘

[ TRIGGER LAYER ]
    │   • Airflow DAG (dags/crawl_news_dag.py)  — cron 6h & 18h
    │   • Telegram bot polling                 — on-demand /crawl, /status
    │   • HTTP /crawl endpoint                 — manual kick-off
    ▼
[ INGESTION LAYER — src/crawlers/ ]
    │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐
    │   │  VNExpressCrawl │  │  TuoiTreCrawler │  │ VietnamNetCrawl │  │ DanTriCrawler│
    │   │  (RSS)          │  │  (RSS)          │  │  (RSS)          │  │ (HTML)       │
    │   └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └──────┬───────┘
    │            └────────────┬───────┴────────────┬───────┴─────────────────┘
    │                         ▼                    ▼
    │              ThreadPoolExecutor (4–8 workers) — concurrent fan-out
    ▼
[ BRONZE — raw, untransformed JSON, partitioned by source & crawl time ]
    │   data/bronze/<source>/<YYYY-MM-DD>/<HH>h.json
    │   schema: { url, raw_html, fetched_at }   ← intentionally minimal
    ▼
[ DEDUP — src/pipeline/deduplicator.py ]
    │   Hash(url) ∪ Hash(title_normalized) — both must miss to ingest
    │   State persisted to data/_state/seen_urls.parquet (crash-safe)
    ▼
[ SILVER — cleaned, schema-validated, deduped, source-tagged ]
    │   data/silver/<source>/<YYYY-MM-DD>/<HH>h.parquet
    │   schema: Article (url, title, description, content, author, published_at,
    │                    category, source_id, source_name, article_id, …)
    │   src/pipeline/cleaner.py   — HTML strip, unicode normalize, lang detect
    │   src/pipeline/schema.py    — Pandera validation
    │   src/pipeline/parquet_writer.py — PyArrow partitioned writer
    ▼
[ GOLD — business-grade, aggregated, ready for ML/RAG ]
    │   data/gold/<YYYY-MM-DD>/articles.parquet
    │   • 4-source union, single canonical schema
    │   • Per-source counts + total
    │   • snake_case column names, ISO-8601 timestamps
    │   src/pipeline/orchestrator.py — drives Bronze→Silver→Gold sequencing
    ▼
[ STORAGE SINKS — src/storage/cloud_sink.py + drive_puller.py ]
    │   ┌────────────────────┐    ┌────────────────────┐
    │   │  LocalJsonSink     │    │  GoogleDriveSink    │
    │   │  (always)          │    │  (optional, on)     │
    │   └─────────┬──────────┘    └──────────┬──────────┘
    │             │                          │
    │             └────────────┬─────────────┘
    │                          ▼
    │              Google Drive folder per source:
    │              vnexpress-news/, tuoitre-news/, vietnamnet-news/, dantri-news/
    │              ↑ Retries with exponential backoff + dead-letter retry queue
    │              ↑ src/storage/retry_queue.py
    ▼
[ DATALAKE EXPORT — src/storage/databricks_sink.py ]
    │   Optional: push Gold parquet to Databricks (DBFS / S3) on a schedule
    ▼
[ CONSUMPTION LAYER — src/rag/ ]
    │   ┌────────────────────────────────────────────────────┐
    │   │  vector_store.py   — ChromaDB over sentence-transformers│
    │   │                     (paraphrase-multilingual-MiniLM)    │
    │   │  persistent_store.py — incremental upserts (no rebuild)│
    │   │  qa_chain.py       — Gemini 2.5 Flash RAG chain       │
    │   │  Gemini client     — Vietnamese, top-k=5, source citation│
    │   └────────────────────────────────────────────────────┘
    │   ↳ Telegram /ask, /asklong — chat with the news
    ▼
[ OPS LAYER ]
    │   • Telegram bot — /status, /crawl, /ask, /asklong, /logs, /testdrive
    │   • HTTP debug    — /debug/env, /debug/health, /testdrive, /crawl
    │   • Railway cron  — auto-redeploy on push, 6h schedule
    │   • Logs          — JSON-line structured, piped to /logs endpoint
    ▼
[ DEPLOYMENT ]
        Railway.app — single Dockerfile, persistent Volume mounted at /app/data
        Environment-injected secrets (no creds in repo, .gitignore'd)
```

---

## 3. Tech stack

| Layer            | Tool                                                 |
|------------------|------------------------------------------------------|
| Language         | Python 3.11                                          |
| Orchestration    | Apache Airflow (DAG) + aiohttp self-hosted scheduler|
| Concurrency      | `concurrent.futures.ThreadPoolExecutor`              |
| Validation       | Pandera                                              |
| Storage (parquet)| PyArrow                                              |
| Vector store     | ChromaDB (persistent) + sentence-transformers        |
| LLM              | Google Gemini 2.5 Flash                              |
| Embedding        | `paraphrase-multilingual-MiniLM-L12-v2`              |
| Cloud            | Google Drive API v3, Databricks DBFS                 |
| Bot              | python-telegram-bot (polling)                        |
| Deploy           | Railway (Docker, persistent volume)                  |
| CI               | GitHub Actions (lint + smoke test)                   |

All deps in `requirements.txt`; CPU-only torch to keep the image under 1.5 GB.

---

## 4. Repo layout (the way you'd see it on GitHub)

```
data-platfrom/
├── dags/                    # Airflow DAG
├── src/
│   ├── crawlers/            # VNExpress, Tuổi Trẻ, VietnamNet, Dân Trí
│   ├── pipeline/            # Bronze→Silver→Gold orchestrator
│   ├── storage/             # Local, Drive, Databricks sinks + retry queue
│   ├── rag/                 # Vector store + Gemini QA chain
│   ├── services/            # GoogleDriveService (auth, upload, folder)
│   └── utils/               # credentials resolver, logging
├── scripts/                 # telegram_digest, main_service, set_railway_secret
├── configs/                 # client_secret.json (OAuth), Drive creds
├── docs/                    # architecture/, pipelines/, runbooks/, adr/
├── data/                    # local Lakehouse (gitignored)
├── Dockerfile               # ← production build (CPU torch, cache-bust)
├── Dockerfile.crawler       # local Airflow dev image
├── docker-compose.yml       # local stack
├── railway.json             # deploy config
└── CHANGELOG.md             # versioned incident postmortems
```

---

## 5. Notable engineering decisions

### 5.1 Bronze / Silver / Gold on a single box
- **Bronze** = raw, source-faithful. If a parser changes, you can re-derive Silver
  without re-fetching.
- **Silver** = cleaned + validated. One row per article, schema-enforced.
- **Gold** = source-agnostic, single unioned table. The RAG layer only reads Gold.

Why not just dump straight to Gold? Because when VietnamNet rotates their RSS
structure (it happens), Bronze is your rewind button. Re-deriving Silver from Bronze
takes seconds; re-crawling a week of news takes 6 days of cron cycles.

### 5.2 Event-driven + cron hybrid
The bot exposes `/crawl` for on-demand runs (useful when debugging a parser),
but production traffic is the Airflow 6h/18h schedule. Failed runs don't block
the next one — the retry queue absorbs transient Drive/DBFS failures.

### 5.3 PEP 562 lazy `__getattr__` for module init
After a partial-init crash on Railway (`ImportError: cannot import name 'X' from
partially initialized module 'src.pipeline'`), all hot-path packages were refactored
to lazy attribute resolution. Boot no longer fails on an unrelated submodule bug;
the failure surfaces at the actual call site with a clear traceback.

### 5.4 Build cache busting on Railway
BuildKit's content-hash caching is a footgun when `git checkout` preserves mtimes.
The Dockerfile now `RUN rm -rf` source dirs before `COPY` and uses an `ARG
BUILD_TAG` for hard invalidation. Tagged as `cache-bust-vN` per deploy.

### 5.5 Secrets are environment-only
Google service-account JSON lives in `GOOGLE_DRIVE_CREDENTIALS_JSON` (or
`GOOGLE_DRIVE_CREDENTIALS_PATH`), never in the repo. `.gitignore` blocks
`gen-lang-client-*.json`; a `git filter-repo` history scrub is the standard
recovery if one slips through.

### 5.6 RAG stack: Chroma + multilingual MiniLM + Gemini 2.5 Flash
- MiniLM keeps the embedder under 500 MB and works well for Vietnamese.
- Chroma persistent store means re-deploys don't lose the index.
- Gemini 2.5 Flash is fast enough for Telegram polling latency.
- The QA chain cites sources by `source_name + url`, so users can verify.

### 5.7 Operational design
- **Self-diagnostics**: `/debug/env` reports which secrets are present without
  printing their values; `/testdrive` does a real Drive roundtrip; `/status`
  reports per-source article counts + Drive health.
- **Telegram digest**: a single message per cron run with counts, errors, and a
  one-tap retry link — no need to open Railway logs for routine checks.
- **Runbooks**: `docs/runbooks/daily-checklist.md`, `troubleshooting.md`,
  `backup-recovery.md` — every recurring failure mode has a documented recovery.

---

## 6. What you'd actually do with it

1. **Add a new source** (e.g., Thanh Niên, Zing): write a `thanh_nien_crawler.py`
   extending `BaseCrawler` — the orchestrator wires it in automatically. Roughly
   80–150 lines including tests.
2. **Improve cleaning**: edit `src/pipeline/cleaner.py` — Bronze is preserved,
   re-derive Silver + Gold with a single command.
3. **Swap the LLM**: `src/rag/qa_chain.py` exposes a `GeminiClient` interface;
   drop in Claude or GPT-4o in one file.
4. **Move off Railway**: `Dockerfile` is portable; just mount a persistent volume
   and inject the same env vars.

---

## 7. What I learned shipping this

- **Cache invalidation is the hardest CS problem in practice.** BuildKit's
  content-hash caching silently returns stale images when mtimes don't change
  after `git checkout`. The fix is to either bust via `ARG` or `rm -rf` the
  destination before `COPY`. Cost me 4 deploy cycles to learn.
- **Partial-init errors are the worst error class in Python.** A failure in any
  submodule kills `from package import *`. PEP 562 lazy `__getattr__` is the
  cleanest fix, but you have to write the boilerplate per-package.
- **Production RAG needs source citation or nobody trusts it.** Returning a
  5-paragraph answer with no provenance looks confident and is almost always
  hallucinated. The QA chain now always returns `(answer, [sources])`.
- **Cron without a heartbeat is a black hole.** Adding the Telegram digest made
  silent failures visible within 30 minutes instead of "we noticed the data
  looked stale last week."

---

## 8. Quick numbers (last production run)

- **4 sources** crawled concurrently in ~45 s
- **282 articles** ingested, 0 dupes, 0 schema errors
- **~3.2 MB** Silver parquet, ~**0.8 MB** Gold parquet
- **4 Drive pushes** succeeded on first try
- **~9 s** end-to-end from cron trigger to RAG-ready

---

## 9. Repo & contact

- Repo: `github.com/<your-handle>/data-platfrom`
- License: MIT
- Stack: Python · Airflow · PyArrow · ChromaDB · Gemini · Telegram · Railway

If you're working on Vietnamese NLP, news aggregation, or just want to see a
small but real Lakehouse + RAG system in production, happy to chat.

---

# 🇻🇳 Bản tiếng Việt (rút gọn, dùng cho LinkedIn nếu thích)

## Tóm tắt

Hệ thống data platform tự động thu thập tin tức từ 4 báo lớn Việt Nam
(VNExpress, Tuổi Trẻ, VietnamNet, Dân Trí), chuẩn hoá theo Lakehouse
Bronze → Silver → Gold, và cung cấp chatbot RAG tiếng Việt để hỏi đáp
trên kho dữ liệu. Deploy một nút bấm lên Railway, có Telegram bot để
vận hành, có HTTP debug endpoint để sự cố.

## Pipeline

1. **Trigger**: Airflow cron 6h/18h, hoặc Telegram `/crawl`, hoặc HTTP `/crawl`
2. **Crawl đồng thời**: 4 crawler chạy song song qua ThreadPool, mỗi nguồn ~10–15s
3. **Bronze**: ghi JSON thô theo `data/bronze/<source>/<date>/<hour>.json`
4. **Dedup**: hash URL + title → bỏ trùng, có state file chống crash
5. **Silver**: chuẩn hoá schema, làm sạch HTML, ghi parquet theo ngày
6. **Gold**: union 4 nguồn, 1 bảng canonical cho RAG
7. **Storage**: ghi local + đẩy Google Drive theo folder riêng mỗi nguồn
8. **Vector store**: ChromaDB + multilingual MiniLM embedder
9. **RAG**: Gemini 2.5 Flash trả lời kèm citation
10. **Bot**: Telegram hỗ trợ `/ask`, `/asklong`, `/status`, `/logs`, `/testdrive`

## Quyết định kỹ thuật đáng chú ý

- **Lakehouse trên 1 máy**: Bronze giữ raw để re-derive khi parser thay đổi
- **Lazy `__getattr__` (PEP 562)**: tránh partial-init crash, surface lỗi đúng chỗ
- **Cache-bust Docker**: `ARG BUILD_TAG` + `rm -rf` trước `COPY` để tránh stale image
- **Secrets qua env only**: file JSON key đã được ignore khỏi git, rotate theo policy
- **Source citation trong RAG**: trả lời kèm `(url, source_name)` để verify
- **Telegram digest mỗi cron run**: 1 tin nhắn có counts + lỗi + nút retry

## Tech stack

Python 3.11 · Airflow · PyArrow · Pandera · ChromaDB · sentence-transformers ·
Google Gemini 2.5 Flash · python-telegram-bot · Railway · Docker

## Số liệu production gần nhất

- 4 nguồn crawl đồng thời trong ~45s
- 282 bài ingest, 0 trùng, 0 lỗi schema
- ~3.2 MB Silver parquet, ~0.8 MB Gold parquet
- 4 Drive push thành công lần đầu
- ~9s từ cron trigger đến RAG-ready
