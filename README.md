# Multi-Source Vietnamese News Crawler

> Hệ thống data platform tự động thu thập, làm sạch, chuẩn hoá, và cung cấp
> khả năng truy vấn bằng ngôn ngữ tự nhiên trên kho tin tức tiếng Việt từ bốn
> tờ báo lớn nhất Việt Nam. Repo này là phiên bản showcase — phần showcase
> không chứa bí mật, dùng cho việc giới thiệu dự án, trình bày học thuật,
> và đánh giá kỹ thuật. Phiên bản đầy đủ (có credentials, triển khai trên
> Railway) được giữ ở nhánh `main` nội bộ.

---

## Tổng quan

Tin tức tiếng Việt phân tán trên nhiều nhà xuất bản độc lập. Mỗi tờ báo
duy trì một hệ thống cấp nội dung riêng — RSS, HTML tĩnh, hoặc kết hợp
cả hai — với những quy ước schema, cách đặt paywall, và cách giấu feed
khác nhau. Đối với người làm nghiên cứu hoặc kỹ sư dữ liệu, việc gom
các nguồn này thành một kho dữ liệu thống nhất — có thể truy vấn, có
thể phân tích, có thể dùng làm đầu vào cho một mô hình ngôn ngữ — vốn
đòi hỏi hàng tuần chỉ để viết glue code cho từng parser.

Dự án này ra đời từ một câu hỏi thực nghiệm: có thể xây một pipeline
hoàn chỉnh — từ thu thập đến truy vấn ngôn ngữ tự nhiên — chạy hoàn
toàn tự động trên hạ tầng nhẹ, và có khả năng tái sử dụng khi một
trong các nguồn thay đổi cấu trúc? Câu trả lời là có, và kết quả là
một hệ thống đang chạy ổn định, thu thập khoảng 280 bài viết mỗi
chu kỳ 6 giờ.

Kho dữ liệu kết quả được tổ chức theo mô hình **Lakehouse ba tầng**
(bronze / silver / gold), truy vấn thông qua một **RAG chatbot tiếng
Việt** chạy trên Gemini 2.5 Flash, và vận hành thông qua **Telegram
bot** cùng các HTTP debug endpoint. Toàn bộ được đóng gói trong một
Dockerfile duy nhất và triển khai trên Railway.

---

## Các nguồn tin được hỗ trọ

Hệ thống hiện thu thập từ bốn nguồn sau. Mỗi nguồn có một crawler
riêng trong `src/crawlers/`, kế thừa từ `BaseCrawler`. Ba nguồn đầu
cung cấp RSS feed có cấu trúc ổn định; nguồn thứ tư (Dân Trí) không
có RSS, nên crawler phải tải trang chủ HTML và tự dò liên kết bài
viết.

| # | Nguồn | URL | Cơ chế lấy | Drive folder |
|---|-------|-----|------------|--------------|
| 1 | VNExpress | vnexpress.net | RSS | `vnexpress-news` |
| 2 | Tuổi Trẻ | tuoitre.vn | RSS | `tuoitre-news` |
| 3 | VietnamNet | vietnamnet.vn | RSS | `vietnamnet-news` |
| 4 | Dân Trí | dantri.com.vn | HTML | `dantri-news` |

Việc tách bạch mỗi nguồn thành một class độc lập có hai ý nghĩa. Về
mặt kỹ thuật, mỗi crawler chỉ phải hiểu một nguồn, không phải hiểu cả
bốn — việc thêm nguồn thứ năm chỉ tốn khoảng 80 đến 150 dòng mã. Về
mặt dữ liệu, lỗi ở một parser không ảnh hưởng đến các parser khác;
nếu VietnamNet đổi schema, ba nguồn còn lại vẫn ghi dữ liệu bình
thường.

---

## Cách cài đặt nhanh (showcase / chạy local không cần cloud)

Phần này dành cho người đọc muốn chạy thử bản showcase. Nó dùng một
crawler mô phỏng (`MockCrawler`) thay cho 4 crawler thật, nên không
cần credentials Google Drive hay Telegram. Sau khi đánh giá xong,
người đọc có thể chuyển sang nhánh `main` để có bản đầy đủ.

```bash
# 1. Clone
git clone https://github.com/<your-handle>/data-platfrom.git
cd data-platfrom
git checkout intro/showcase   # bản showcase, không có credentials

# 2. Cài đặt (Python 3.11)
pip install -r requirements.txt

# 3. Chạy pipeline một lần với dữ liệu mô phỏng
python -m src.pipeline.orchestrator --mock

# 4. Kiểm tra kết quả
ls data/gold/
python -c "import pandas as pd; print(pd.read_parquet('data/gold/latest/articles.parquet').head())"
```

Nếu muốn chạy với credentials thật, copy `.env.example` thành `.env`
và điền giá trị vào. Tuyệt đối không commit file `.env` (đã có trong
`.gitignore`).

---

## Mục tiêu thiết kế

Trước khi đi vào kiến trúc, cần nói rõ bốn ràng buộc đã định hình mọi
quyết định sau này.

**Tính tái dựng (reproducibility)**. Khi một nguồn thay đổi schema, ta
phải có khả năng suy ra lại dữ liệu đã qua xử lý mà không cần crawl
lại từ đầu. Ràng buộc này sinh ra quyết định lưu trữ dữ liệu thô ở
một tầng riêng, trước mọi phép biến đổi.

**Tính chịu lỗi (fault tolerance)**. Cron job chạy tự động không có
người giám sát, nên lỗi thoáng qua của một dịch vụ bên ngoài không
được phép làm hỏng toàn bộ pipeline. Ràng buộc này sinh ra cơ chế
retry queue và phân tách rõ ràng giữa các bước có thể bỏ qua.

**Tính quan sát được (observability)**. Khi hệ thống fail im lặng,
việc phát hiện có thể mất hàng tuần — và trong thời gian đó, mô hình
AI đang được train trên dữ liệu cũ. Ràng buộc này sinh ra Telegram
digest và các endpoint debug.

**Tính di động (portability)**. Toàn bộ hệ thống đóng gói trong một
Dockerfile duy nhất, có thể chuyển từ Railway sang bất kỳ nền tảng nào
khác bằng cách mount một persistent volume và inject cùng tập biến
môi trường.

---

## Kiến trúc tổng quan

Hệ thống có bốn lớp chức năng, chảy theo một chiều từ kích hoạt đến
truy vấn.

Lớp kích hoạt chịu trách nhiệm bắt đầu một lần crawl. Có ba cách:
Apache Airflow DAG (cron 6h và 18h), lệnh Telegram (`/crawl`), và
HTTP endpoint `/crawl`. Cả ba đều gọi chung một hàm `run_crawl()`
nên hành vi không phụ thuộc vào cách kích hoạt.

Lớp thu thập gồm bốn crawler chạy đồng thời qua
`concurrent.futures.ThreadPoolExecutor` với 4–8 worker. Thời gian
end-to-end của cả bốn nguồn vào khoảng 45 giây — nhanh hơn gần bốn
lần so với chạy tuần tự.

Lớp xử lý tổ chức dữ liệu theo ba tầng Bronze / Silver / Gold, kèm
theo dedupe và validation. Đây là phần cốt lõi của kiến trúc và sẽ
được trình bày chi tiết ở phần sau.

Lớp tiêu thụ đẩy dữ liệu ra hai nơi: một folder Google Drive cho mỗi
nguồn (cho người dùng cuối xem), và một tầng RAG cho phép hỏi đáp
tiếng Việt qua Telegram. Lớp vận hành gồm Telegram digest, debug
endpoint, và runbook.

```
                  ┌──────────────────────────────────────────────────┐
                  │            LỚP KÍCH HOẠT                       │
                  │  Airflow cron • Telegram /crawl • HTTP /crawl   │
                  └────────────────────┬─────────────────────────────┘
                                       ▼
                  ┌──────────────────────────────────────────────────┐
                  │            LỚP THU THẬP                          │
                  │  VNExpressCrawler | TuoiTreCrawler               │
                  │  VietnamNetCrawler | DanTriCrawler               │
                  │  (ThreadPoolExecutor, 4–8 worker)                │
                  └────────────────────┬─────────────────────────────┘
                                       ▼
                  ┌──────────────────────────────────────────────────┐
                  │            LỚP XỬ LÝ (Lakehouse)                 │
                  │  Bronze → Dedupe → Silver → Validate → Gold     │
                  └────────────────────┬─────────────────────────────┘
                                       ▼
                  ┌──────────────────────────────────────────────────┐
                  │            LỚP TIÊU THỤ                          │
                  │  Google Drive (4 folder) | Databricks (optional)│
                  │  ChromaDB Vector Store | Gemini QA Chain         │
                  └──────────────────────────────────────────────────┘
```

---

## Mô hình Lakehouse ba tầng

Đây là điểm cốt lõi của kiến trúc, và cũng là nơi khác biệt rõ nhất
so với một crawler đơn giản. Thay vì đẩy thẳng dữ liệu thô vào một
bảng cuối cùng, hệ thống lưu trữ theo ba tầng có mục đích khác nhau.

**Tầng Bronze** ghi dữ liệu thô ngay khi nhận được từ crawler, trước
mọi phép biến đổi. Cấu trúc thư mục là
`data/bronze/<source>/<YYYY-MM-DD>/<HH>h.json`, và payload chỉ chứa
những trường tối thiểu: URL, raw HTML, và timestamp lấy. Tầng này
trung thành với nguồn — nếu sau này phát hiện một parser lọc bớt
trường quan trọng, ta có thể quay lại Bronze và xử lý lại mà không
cần crawl thêm một lần nào.

**Tầng Silver** là kết quả sau khi làm sạch và chuẩn hoá. Strip
HTML, chuẩn hoá Unicode, phát hiện ngôn ngữ, validate schema bằng
Pandera, và loại bỏ trùng lặp. Khoá dedupe là kết hợp giữa hash URL
và hash tiêu đề đã chuẩn hoá — hai bài khác URL nhưng cùng tiêu đề
vẫn được tính là trùng. State của dedupe lưu vào
`data/_state/seen_urls.parquet`, ghi incremental, chống crash nhờ
atomic write. Một dòng ở Silver là một bài viết hoàn chỉnh, với
schema Pandera enforce nghiêm ngặt.

**Tầng Gold** là tầng cuối cùng và là đầu vào duy nhất của mọi hệ
thống phía sau — phân tích, mô hình, hay RAG. Gold là sự kết hợp
của cả bốn nguồn, có một schema canonical duy nhất, tên cột
snake_case, timestamp ISO-8601, và kèm theo các trường aggregate
như `article_count_per_source`. File ghi theo ngày tại
`data/gold/<YYYY-MM-DD>/articles.parquet`.

Lý do phải có ba tầng thay vì hai đã nói ở phần mục tiêu thiết kế:
Bronze là nút rewind khi parser thay đổi. Re-derive Silver từ Bronze
mất vài giây; crawl lại một tuần tin mất sáu ngày cron. Trong ngữ
cảnh dữ liệu tin tức, một tuần là cả một kho ngữ liệu có giá trị
cho nghiên cứu.

---

## Tầng RAG — hỏi đáp tiếng Việt trên kho tin tức

Tầng RAG là phần mới nhất của hệ thống và là nơi giá trị dữ liệu
được "đổi thành" một sản phẩm người dùng cuối có thể chạm vào. Ý
tưởng đơn giản: người dùng đặt câu hỏi bằng tiếng Việt, hệ thống
tìm những bài viết liên quan nhất trong Gold, đưa vào context cho
một LLM, và trả lời kèm theo citation.

Embedder là `paraphrase-multilingual-MiniLM-L12-v2` — một model
khoảng 500 MB, đủ nhỏ để chạy trong container Railway, đủ tốt để
hiểu tiếng Việt. Vector store là ChromaDB, persistent trên disk,
có nghĩa là re-deploy container không mất index — một yêu cầu quan
trọng vì build lại index từ đầu mất hàng phút.

LLM là Gemini 2.5 Flash của Google. Lý do chọn Flash thay vì bản
Pro là tốc độ: độ trễ từ lúc người dùng gửi câu hỏi đến khi nhận
token đầu tiên của Gemini 2.5 Flash thường dưới 800 ms, đủ nhanh
cho cảm giác hội thoại qua Telegram.

Một quyết định thiết kế quan trọng là **citation là bắt buộc**, không
phải tuỳ chọn. Mọi câu trả lời của QA chain đều kèm theo danh sách
`(source_name, url)` cho từng bài viết được tham chiếu. Lý do: trả
lời dài nhiều đoạn mà không kèm provenance thì trông rất tự tin
nhưng gần như chắc chắn chứa hallucination. Citation cho phép người
dùng verify trong một cú click.

---

## Lớp vận hành

Một hệ thống tự động không có nghĩa là không cần giám sát. Hệ thống
có ba cơ chế quan sát.

**Telegram digest** là một tin nhắn duy nhất gửi sau mỗi cron run,
có chứa số bài theo từng nguồn, số lỗi, và nút retry. Quan trọng
nhất là digest được gửi *cả khi thành công lẫn khi thất bại* —
silent failure là loại lỗi nguy hiểm nhất, vì nó không có cách nào
tự phát tín hiệu. Trước khi có digest, đã có lần hệ thống fail im
lặng suốt ba ngày mà không ai để ý.

**HTTP debug endpoint** (`/debug/env`, `/debug/health`, `/testdrive`)
dành cho lúc cần điều tra nhanh. `/debug/env` liệt kê biến môi
trường nào đang được set mà không in giá trị (tránh leak secret);
`/testdrive` làm một roundtrip upload thật lên Drive để xác nhận
credentials còn hoạt động.

**Runbook** tại `docs/runbooks/` ghi chép lại từng failure mode đã
gặp và cách xử lý. `daily-checklist.md` cho tác vụ định kỳ;
`troubleshooting.md` cho sự cố runtime; `backup-recovery.md` cho
disaster recovery.

---

## Quản lý bí mật

Repo này là phiên bản showcase và không chứa bí mật. Tất cả các
file nhạy cảm (`.env`, OAuth client secret, OAuth refresh token,
Google service account key) đã được untrack khỏi nhánh này. Nhánh
`main` (nội bộ) mới chứa credentials thật để chạy production trên
Railway.

Đối với người muốn chạy bản đầy đủ:

1. Tạo file `.env` từ `.env.example` và điền giá trị
2. Service account key đặt vào `configs/google-drive-credentials.json`
   hoặc set trực tiếp biến `GOOGLE_DRIVE_CREDENTIALS_JSON` trên Railway
3. OAuth credentials (nếu dùng user OAuth) đặt vào `configs/client_secret.json`
4. Telegram bot token set qua `TELEGRAM_BOT_TOKEN`
5. **Không bao giờ** commit các file trên vào git

Một thực hành đã được áp dụng trong dự án: nếu một file JSON key
từng xuất hiện trong context của bất kỳ AI tool nào, key đó phải
được rotate ngay — vì không có cách nào đảm bảo key đã không bị
đọc.

---

## Cấu trúc repo

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
├── configs/                 # client_secret.json (OAuth), Drive creds (main only)
├── docs/                    # architecture/, pipelines/, runbooks/, adr/
├── data/                    # Lakehouse local (đã gitignore)
├── Dockerfile               # bản build production (CPU torch, cache-bust)
├── docker-compose.yml       # stack local
├── railway.json             # config deploy (main only)
├── .env.example             # biến môi trường mẫu
└── README.md                # file này
```

---

## Triển khai

Bản đầy đủ chạy trên Railway. Lý do chọn Railway là vì persistent
volume tích hợp sẵn (không cần thiết lập EBS riêng), và cron job
native hỗ trợ lịch 6 giờ mà không cần Airflow server chạy 24/7.

Image build từ Dockerfile ở root, dùng `python:3.11-slim` với torch
CPU-only để giữ kích thước dưới 1.5 GB. Volume persistent mount tại
`/app/data` để Lakehouse không bị mất khi container restart.

Nếu muốn chuyển sang nền tảng khác — ví dụ chạy trên Kubernetes
hoặc EC2 — chỉ cần mount volume tương ứng và inject cùng tập env
var. Dockerfile đã được thiết kế portable.

Một bài học đáng nhớ khi deploy là **vấn đề cache-bust**. BuildKit
content-hash caching có thể trả về image cũ khi `git checkout` giữ
nguyên mtime của file đã `COPY`. Cách fix: dùng `ARG BUILD_TAG` để
bump qua mỗi deploy, hoặc `RUN rm -rf` thư mục đích trước `COPY`.
Chi tiết này tốn bốn deploy cycle mới phát hiện ra.

---

## Tech stack

| Tầng                | Công cụ                                              |
|---------------------|--------------------------------------------------|
| Ngôn ngữ            | Python 3.11                                        |
| Orchestration       | Apache Airflow + aiohttp self-hosted scheduler    |
| Đồng thời           | `concurrent.futures.ThreadPoolExecutor`           |
| Validation          | Pandera                                            |
| Storage (parquet)   | PyArrow                                            |
| Vector store        | ChromaDB (persistent) + sentence-transformers     |
| LLM                 | Google Gemini 2.5 Flash                           |
| Embedding           | `paraphrase-multilingual-MiniLM-L12-v2`           |
| Cloud               | Google Drive API v3, Databricks DBFS              |
| Bot                 | python-telegram-bot (polling)                     |
| Triển khai          | Railway (Docker, persistent volume)               |
| CI                  | GitHub Actions (lint + smoke test)                |

---

## Những bài học rút ra

**Partial-init error là class lỗi tệ nhất của Python** trong ngữ
cảnh package lớn. Một lỗi ở bất kỳ submodule nào có thể giết luôn
`from package import *` và không để lại traceback rõ ràng. PEP 562
lazy `__getattr__` là cách sạch nhất để tránh, nhưng phải viết
boilerplate riêng cho từng package.

**Cron không có heartbeat là hố đen**. Một hệ thống chạy tự động mà
không có cơ chế báo "tôi vẫn sống" thì lỗi im lặng có thể kéo dài
hàng tuần. Telegram digest — một thông báo *kể cả khi thành công* —
biến silent failure thành thấy được trong vòng 30 phút.

**Cache invalidation không chỉ là vấn đề của CPU mà còn của container
build**. BuildKit cache theo content hash, và một file có nội dung
"không đổi" (chỉ đổi mtime) sẽ được phục vụ từ cache. Trong
Dockerfile production, luôn cần có cơ chế explicit cache bust.

**RAG production bắt buộc phải có citation**. Trả lời tự tin mà
không kèm nguồn là con đường nhanh nhất để người dùng mất niềm tin
vào hệ thống. Citation không chỉ là tính năng, nó là yêu cầu kỹ thuật.

---

## Số liệu production

Trong chu kỳ 6 giờ gần nhất, hệ thống ghi nhận: 4 nguồn crawl đồng
thời trong khoảng 45 giây; 282 bài viết được ingest, không có trùng
lặp, không có lỗi schema; kích thước Silver parquet khoảng 3.2 MB,
Gold parquet khoảng 0.8 MB; bốn lần push Drive đều thành công ở lần
thử đầu tiên; thời gian từ cron trigger đến lúc RAG-ready là khoảng
9 giây.

Những con số này không lớn về mặt tuyệt đối, nhưng phản ánh một hệ
thống có thể chạy thật trong thời gian dài mà không cần can thiệp
— đó mới là tiêu chí quan trọng nhất.

---

## Hướng mở rộng

Thêm nguồn thứ năm (ví dụ Thanh Niên hoặc Zing) chỉ tốn 80–150
dòng mã cho một crawler mới kế thừa `BaseCrawler`. Cải thiện chất
lượng làm sạch có thể thực hiện trong `src/pipeline/cleaner.py` mà
không ảnh hưởng các tầng khác, nhờ Bronze là nút rewind. Đổi Gemini
sang Claude hoặc GPT-4o là một thay đổi cục bộ trong
`src/rag/qa_chain.py` — interface `GeminiClient` được thiết kế để
thay thế một-một.

Về lâu dài, có thể cân nhắc chuyển từ Railway sang Kubernetes để
có quyền kiểm soát chi tiết hơn về resource limit và tự động scale
khi số nguồn tăng lên.

---

## Tài liệu kèm theo

Repo này đi kèm một số tài liệu bổ sung trong thư mục `docs/`:

- `docs/PROJECT_OVERVIEW.md` — mô tả narrative dài hơn, dùng cho
  LinkedIn hoặc hồ sơ học thuật
- `docs/architecture/` — sơ đồ kiến trúc chi tiết từng tầng
- `docs/pipelines/` — quy trình Bronze → Silver → Gold
- `docs/runbooks/` — daily-checklist, troubleshooting,
  backup-recovery
- `docs/adr/` — Architecture Decision Records (lý do chọn công nghệ)

---

## Liên hệ

Dự án mã nguồn mở theo giấy phép MIT. Stack chính: Python 3.11,
Apache Airflow, PyArrow, ChromaDB, Google Gemini, python-telegram-bot,
Docker trên Railway.

Mọi trao đổi về NLP tiếng Việt, tổng hợp tin tức, hoặc thiết kế
Lakehouse + RAG đều được hoan nghênh qua issue tracker của repo
này.