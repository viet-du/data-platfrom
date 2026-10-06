# Multi-Source Vietnamese News Crawler — Mô tả dự án

> Tài liệu mô tả toàn bộ dự án dưới dạng văn xuôi, có dẫn dắt, phù hợp để
> trình bày trên LinkedIn (About / Featured / post dài) hoặc trong hồ sơ học
> thuật. Giọng văn: trung tính, kỹ thuật chính xác, không hoa mỹ, không bỏ
> biến số quan trọng.

---

## Bối cảnh và động cơ

Tin tức tiếng Việt phân tán trên nhiều nhà xuất bản độc lập. Mỗi tờ báo
duy trì một hệ thống cấp nội dung riêng — RSS, HTML tĩnh, hoặc kết hợp cả
hai — với những quy ước schema, cách đặt paywall, và cách giấu feed khác
nhau. Đối với người làm nghiên cứu hoặc kỹ sư dữ liệu, việc gom các nguồn
này thành một kho dữ liệu thống nhất — có thể truy vấn, có thể phân tích,
có thể dùng làm đầu vào cho một mô hình ngôn ngữ — vốn đòi hỏi hàng tuần
chỉ để viết glue code cho từng parser.

Dự án này ra đời từ một câu hỏi thực nghiệm: có thể xây một pipeline
hoàn chỉnh — từ thu thập đến truy vấn ngôn ngữ tự nhiên — chạy hoàn toàn
tự động trên hạ tầng nhẹ, và có khả năng tái sử dụng khi một trong các
nguồn thay đổi cấu trúc? Câu trả lời là có, và kết quả là hệ thống đang
chạy ổn định trên Railway, thu thập khoảng 280 bài viết mỗi chu kỳ 6 giờ
từ bốn tờ báo lớn nhất Việt Nam.

---

## Mục tiêu thiết kế

Trước khi đi vào kiến trúc, cần nói rõ bốn ràng buộc đã định hình mọi
quyết định sau này.

Thứ nhất, **tính tái dựng (reproducibility)**. Khi một nguồn thay đổi
schema, ta phải có khả năng suy ra lại dữ liệu đã qua xử lý mà không cần
crawl lại từ đầu. Ràng buộc này sinh ra quyết định lưu trữ dữ liệu thô ở
một tầng riêng, trước mọi phép biến đổi.

Thứ hai, **tính chịu lỗi (fault tolerance)**. Cron job chạy tự động không
có người giám sát, nên lỗi thoáng qua của một dịch vụ bên ngoài không được
phép làm hỏng toàn bộ pipeline. Ràng buộc này sinh ra cơ chế retry queue
và phân tách rõ ràng giữa các bước có thể bỏ qua.

Thứ ba, **tính quan sát được (observability)**. Khi hệ thống fail im
lặng, việc phát hiện có thể mất hàng tuần — và trong thời gian đó, mô
hình AI đang được train trên dữ liệu cũ. Ràng buộc này sinh ra Telegram
digest và các endpoint debug.

Thứ tư, **tính di động (portability)**. Toàn bộ hệ thống đóng gói trong
một Dockerfile duy nhất, có thể chuyển từ Railway sang bất kỳ nền tảng nào
khác bằng cách mount một persistent volume và inject cùng tập biến môi
trường.

---

## Lớp kích hoạt

Một pipeline không chạy được nếu không có cơ chế kích hoạt. Hệ thống
hiện hỗ trợ ba cách bắt đầu một lần crawl, đáp ứng các tình huống sử
dụng khác nhau.

Cách thứ nhất là **Airflow DAG** đặt tại `dags/crawl_news_dag.py`, lập
lịch cron vào lúc 6 giờ sáng và 18 giờ chiều mỗi ngày theo giờ Việt Nam.
Đây là đường chính trong production. DAG đảm nhận việc phân bổ tài nguyên,
retry tự động khi một task con thất bại, và ghi metadata về từng lần chạy
vào cơ sở dữ liệu metadata của Airflow.

Cách thứ hai là **lệnh Telegram** (`/crawl`). Đường này dùng khi cần
chạy thử ngay, ví dụ sau khi vừa sửa một parser và muốn xác nhận nó hoạt
động đúng trước khi đợi cron kế tiếp. Bot polling liên tục, độ trễ từ
lúc gõ lệnh đến khi pipeline bắt đầu thường dưới hai giây.

Cách thứ ba là **HTTP endpoint `/crawl`** dành cho tích hợp với hệ thống
bên ngoài — ví dụ một webhook từ GitHub Actions chạy sau khi merge.

Cả ba đường đều gọi chung một hàm `run_crawl()` ở tầng dưới, nên hành vi
không phụ thuộc vào cách kích hoạt.

---

## Lớp thu thập

Tại `src/crawlers/`, mỗi nguồn tin được đóng gói thành một class riêng
kế thừa từ một abstract base có tên `BaseCrawler`. Hệ thống hiện có bốn
triển khai cụ thể: `VNExpressCrawler`, `TuoiTreCrawler`,
`VietnamNetCrawler`, và `DanTriCrawler`. Ba nguồn đầu cung cấp RSS feed
có cấu trúc ổn định; nguồn thứ tư (Dân Trí) không có RSS, nên crawler
phải tải trang chủ HTML và tự dò liên kết bài viết.

Sự tách bạch này có hai ý nghĩa. Về mặt kỹ thuật, mỗi crawler chỉ phải
hiểu một nguồn, không phải hiểu cả bốn — việc thêm nguồn thứ năm chỉ tốn
khoảng 80 đến 150 dòng mã. Về mặt dữ liệu, lỗi ở một parser không ảnh
hưởng đến các parser khác; nếu VietnamNet đổi schema, ba nguồn còn lại vẫn
ghi dữ liệu bình thường.

Bốn crawler được gọi đồng thời qua `concurrent.futures.ThreadPoolExecutor`
với 4–8 worker. Phép đo thực nghiệm cho thấy thời gian end-to-end của cả
bốn nguồn vào khoảng 45 giây — nhanh hơn gần bốn lần so với chạy tuần tự,
và quan trọng hơn, thời gian chạy gần như không phụ thuộc vào việc thêm
nguồn mới.

---

## Mô hình Lakehouse ba tầng

Đây là điểm cốt lõi của kiến trúc, và cũng là nơi khác biệt rõ nhất so
với một crawler đơn giản. Thay vì đẩy thẳng dữ liệu thô vào một bảng
cuối cùng, hệ thống lưu trữ theo ba tầng có mục đích khác nhau.

**Tầng Bronze** ghi dữ liệu thô ngay khi nhận được từ crawler, trước mọi
phép biến đổi. Cấu trúc thư mục là `data/bronze/<source>/<YYYY-MM-DD>/<HH>h.json`,
và payload chỉ chứa những trường tối thiểu: URL, raw HTML, và timestamp
lấy. Tầng này trung thành với nguồn — nếu sau này phát hiện một parser
lọc bớt trường quan trọng, ta có thể quay lại Bronze và xử lý lại mà
không cần crawl thêm một lần nào.

**Tầng Silver** là kết quả sau khi làm sạch và chuẩn hoá. Strip HTML,
chuẩn hoá Unicode, phát hiện ngôn ngữ, validate schema bằng Pandera, và
loại bỏ trùng lặp. Khoá dedupe là kết hợp giữa hash URL và hash tiêu đề
đã chuẩn hoá — hai bài khác URL nhưng cùng tiêu đề vẫn được tính là trùng.
State của dedupe lưu vào `data/_state/seen_urls.parquet`, ghi incremental,
chống crash nhờ atomic write. Một dòng ở Silver là một bài viết hoàn
chỉnh, với schema Pandera enforce nghiêm ngặt.

**Tầng Gold** là tầng cuối cùng và là đầu vào duy nhất của mọi hệ thống
phía sau — phân tích, mô hình, hay RAG. Gold là sự kết hợp của cả bốn
nguồn, có một schema canonical duy nhất, tên cột snake_case, timestamp
ISO-8601, và kèm theo các trường aggregate như `article_count_per_source`.
File ghi theo ngày tại `data/gold/<YYYY-MM-DD>/articles.parquet`.

Lý do phải có ba tầng thay vì hai đã nói ở phần mục tiêu thiết kế:
Bronze là nút rewind khi parser thay đổi. Re-derive Silver từ Bronze mất
vài giây; crawl lại một tuần tin mất sáu ngày cron. Trong ngữ cảnh dữ
liệu tin tức, một tuần là cả một kho ngữ liệu có giá trị cho nghiên cứu.

---

## Lớp lưu trữ và đồng bộ hoá

Sau khi Gold được ghi local, một bước đồng bộ sẽ đẩy dữ liệu lên hai
nơi: Google Drive theo folder riêng cho từng nguồn, và tuỳ chọn đẩy
parquet lên Databricks DBFS hoặc S3 nếu cần cho Spark pipeline lớn hơn.

Sink Google Drive (`src/storage/cloud_sink.py`) được thiết kế để push
**một lần sau khi cả bốn nguồn đã xong**, không phải trong vòng lặp. Mỗi
folder trên Drive (`vnexpress-news/`, `tuoitre-news/`, `vietnamnet-news/`,
`dantri-news/`) nhận đúng những bài thuộc nguồn đó. Payload được bọc
thành một dict có metadata (`source`, `layer`, `crawled_at`,
`article_count`, `records`) để dễ truy vết.

Khi push Drive thất bại vì lý do thoáng qua — token hết hạn, network
flapping — hệ thống không dừng pipeline. Một retry queue
(`src/storage/retry_queue.py`) ghi lại payload vào dead-letter storage và
một job nền sẽ thử lại với exponential backoff. Đây là biện pháp giữ
cho pipeline vẫn chạy ngay cả khi Drive ngưng một giờ.

Tuỳ chọn Databricks sink (`src/storage/databricks_sink.py`) phục vụ
trường hợp muốn chạy Spark job trên Gold parquet. Sink này không bật
mặc định vì không phải deployment nào cũng cần.

---

## Lớp truy vấn — RAG tiếng Việt

Tầng RAG là phần mới nhất của hệ thống và là nơi giá trị dữ liệu được
"đổi thành" một sản phẩm người dùng cuối có thể chạm vào. Ý tưởng đơn
giản: người dùng đặt câu hỏi bằng tiếng Việt, hệ thống tìm những bài
viết liên quan nhất trong Gold, đưa vào context cho một LLM, và trả
lời kèm theo citation.

Embedder là `paraphrase-multilingual-MiniLM-L12-v2` — một model khoảng
500 MB, đủ nhỏ để chạy trong container Railway, đủ tốt để hiểu tiếng
Việt. Vector store là ChromaDB, persistent trên disk, có nghĩa là re-deploy
container không mất index — một yêu cầu quan trọng vì build lại index
từ đầu mất hàng phút.

LLM là Gemini 2.5 Flash của Google. Lý do chọn Flash thay vì bản Pro là
tốc độ: độ trễ từ lúc người dùng gửi câu hỏi đến khi nhận token đầu tiên
của Gemini 2.5 Flash thường dưới 800 ms, đủ nhanh cho cảm giác hội thoại
qua Telegram polling.

Một quyết định thiết kế quan trọng là **citation là bắt buộc**, không
phải tuỳ chọn. Mọi câu trả lời của QA chain đều kèm theo danh sách
`(source_name, url)` cho từng bài viết được tham chiếu. Lý do: trả lời
dài nhiều đoạn mà không kèm provenance thì trông rất tự tin nhưng gần
như chắc chắn chứa hallucination. Citation cho phép người dùng verify
trong một cú click.

---

## Lớp vận hành

Một hệ thống tự động không có nghĩa là không cần giám sát. Hệ thống có
ba cơ chế quan sát.

**Telegram digest** là một tin nhắn duy nhất gửi sau mỗi cron run, có
chứa số bài theo từng nguồn, số lỗi, và nút retry. Quan trọng nhất là
digest được gửi *cả khi thành công lẫn khi thất bại* — silent failure là
loại lỗi nguy hiểm nhất, vì nó không có cách nào tự phát tín hiệu. Trước
khi có digest, đã có lần hệ thống fail im lặng suốt ba ngày mà không ai
để ý.

**HTTP debug endpoint** (`/debug/env`, `/debug/health`, `/testdrive`)
dành cho lúc cần điều tra nhanh. `/debug/env` liệt kê biến môi trường nào
đang được set mà không in giá trị (tránh leak secret); `/testdrive` làm
một roundtrip upload thật lên Drive để xác nhận credentials còn hoạt
động. Các endpoint này là cách nhanh nhất để xác định "bot fail vì thiếu
env var hay vì code bug".

**Runbook** tại `docs/runbooks/` ghi chép lại từng failure mode đã gặp
và cách xử lý. `daily-checklist.md` cho tác vụ định kỳ;
`troubleshooting.md` cho sự cố runtime; `backup-recovery.md` cho disaster
recovery. Đây là tài liệu giúp người mới có thể on-call mà không cần
đào sâu vào codebase.

---

## Quản lý bí mật và bảo mật

Hệ thống giữ ba loại bí mật: Google service-account JSON (cho Drive),
OAuth client secret (cho OAuth flow nếu có), và Telegram bot token.
Cả ba được inject qua biến môi trường, không bao giờ nằm trong repo.

`.gitignore` chặn các file JSON key theo pattern `gen-lang-client-*.json`.
Nếu một bí mật lỡ lọt vào lịch sử git, quy trình khôi phục tiêu chuẩn là
`git filter-repo` để scrub history, kèm rotate key trên cloud console.
Một thực hành đã được áp dụng trong dự án: nếu một file JSON key từng
xuất hiện trong context của bất kỳ AI tool nào, key đó phải được rotate
ngay — vì không có cách nào đảm bảo key đã không bị đọc.

---

## Triển khai

Toàn bộ hệ thống đóng gói trong một Dockerfile đặt tại root repo. Image
này dùng `python:3.11-slim`, cài torch CPU-only để giữ kích thước dưới
1.5 GB, và mount một persistent volume tại `/app/data` để Lakehouse không
bị mất khi container restart.

Railway được chọn vì hai lý do: persistent volume tích hợp sẵn (không
cần thiết lập EBS riêng), và cron job native hỗ trợ lịch 6 giờ mà
không cần Airflow server chạy 24/7. Nếu chuyển sang nền tảng khác — ví
dụ chạy trên Kubernetes hoặc EC2 — chỉ cần mount volume tương ứng và
inject cùng tập env var.

Một bài học đáng nhớ khi deploy trên Railway là **vấn đề cache-bust**.
BuildKit content-hash caching có thể trả về image cũ khi `git checkout`
giữ nguyên mtime của file đã `COPY`. Cách fix: dùng `ARG BUILD_TAG` để
bump qua mỗi deploy, hoặc `RUN rm -rf` thư mục đích trước `COPY`. Chi
tiết này tốn bốn deploy cycle mới phát hiện ra, và đã được document
trong `CHANGELOG.md`.

---

## Những bài học rút ra

Thứ nhất, **partial-init error là class lỗi tệ nhất của Python** trong
ngữ cảnh package lớn. Một lỗi ở bất kỳ submodule nào có thể giết luôn
`from package import *` và không để lại traceback rõ ràng. PEP 562 lazy
`__getattr__` là cách sạch nhất để tránh, nhưng phải viết boilerplate
riêng cho từng package — không có decorator hay magic nào giúp được.

Thứ hai, **cron không có heartbeat là hố đen**. Một hệ thống chạy tự
động mà không có cơ chế báo "tôi vẫn sống" thì lỗi im lặng có thể kéo
dài hàng tuần. Telegram digest — một thông báo *kể cả khi thành công* —
biến silent failure thành thấy được trong vòng 30 phút.

Thứ ba, **cache invalidation không chỉ là vấn đề của CPU mà còn của
container build**. BuildKit cache theo content hash, và một file có nội
dung "không đổi" (chỉ đổi mtime) sẽ được phục vụ từ cache. Bài học:
trong Dockerfile production, luôn có cơ chế explicit cache bust.

Thứ tư, **RAG production bắt buộc phải có citation**. Trả lời tự tin
mà không kèm nguồn là con đường nhanh nhất để người dùng mất niềm tin
vào hệ thống. Citation không chỉ là tính năng, nó là yêu cầu kỹ thuật.

---

## Số liệu production

Trong chu kỳ 6 giờ gần nhất (đo ngày 3 tháng 10 năm 2026), hệ thống
ghi nhận: 4 nguồn crawl đồng thời trong khoảng 45 giây; 282 bài viết
được ingest, không có trùng lặp, không có lỗi schema; kích thước Silver
parquet khoảng 3.2 MB, Gold parquet khoảng 0.8 MB; bốn lần push Drive
đều thành công ở lần thử đầu tiên; thời gian từ cron trigger đến lúc
RAG-ready là khoảng 9 giây.

Những con số này không lớn về mặt tuyệt đối, nhưng phản ánh một hệ
thống có thể chạy thật trong thời gian dài mà không cần can thiệp —
đó mới là tiêu chí quan trọng nhất.

---

## Hướng mở rộng

Một vài hướng phát triển tiếp theo đã được xác định. Thêm nguồn thứ
năm (ví dụ Thanh Niên hoặc Zing) chỉ tốn 80–150 dòng mã cho một
crawler mới kế thừa `BaseCrawler`. Cải thiện chất lượng làm sạch có
thể thực hiện trong `src/pipeline/cleaner.py` mà không ảnh hưởng các
tầng khác, nhờ Bronze là nút rewind. Đổi Gemini sang Claude hoặc
GPT-4o là một thay đổi cục bộ trong `src/rag/qa_chain.py` — interface
`GeminiClient` được thiết kế để thay thế một-một.

Về lâu dài, có thể cân nhắc chuyển từ Railway sang Kubernetes để có
quyền kiểm soát chi tiết hơn về resource limit và tự động scale khi
số nguồn tăng lên. Nhưng ở giai đoạn hiện tại, Railway đáp ứng tốt
và đơn giản hơn nhiều trong vận hành.

---

## Liên hệ

Dự án mã nguồn mở theo giấy phép MIT. Repo đặt tại
`github.com/<your-handle>/data-platfrom`. Stack chính: Python 3.11,
Apache Airflow, PyArrow, ChromaDB, Google Gemini, python-telegram-bot,
Docker trên Railway. Mọi trao đổi về NLP tiếng Việt, tổng hợp tin tức,
hoặc thiết kế Lakehouse + RAG đều được hoan nghênh.