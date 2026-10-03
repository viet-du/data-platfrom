#!/usr/bin/env python3
"""
Main Service - Railway Deployment
- Telegram Bot + Crawler Scheduler + Auto Reporter
"""
import os, sys, time, logging, threading, schedule, json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the digest wrapper. TelegramService.send() stays the same
# (immediate delivery for errors / user replies). TelegramService.buffer()
# records low-importance events into an in-memory queue; flush_digest()
# sends them as a single daily summary at 20:00 instead of one-by-one.
from scripts.telegram_digest import TelegramDigest

# ============== TELEGRAM SERVICE ==============
class TelegramService:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.enabled = os.getenv("TELEGRAM_ENABLED", "true").lower() == "true"
        if self.enabled and not self.token:
            logger.error("Telegram is enabled but TELEGRAM_BOT_TOKEN is not configured.")
        if self.enabled and not self.chat_id:
            logger.error("Telegram is enabled but TELEGRAM_CHAT_ID is not configured.")
    
    def send(self, text: str, parse_mode: str = "HTML") -> bool:
        if not self.enabled or not self.token:
            return False
        if not self.chat_id:
            logger.error("Cannot send Telegram message: TELEGRAM_CHAT_ID is not configured.")
            return False
        try:
            import requests
            url = f"{self.api_url}/sendMessage"
            payload = {"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode}
            resp = requests.post(url, json=payload, timeout=10)
            result = resp.json()
            if resp.status_code != 200 or not result.get("ok"):
                logger.error(
                    "Telegram sendMessage failed (HTTP %s): %s",
                    resp.status_code,
                    result.get("description", "Unknown Telegram API error"),
                )
                return False
            return True
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False

    # ----- digest buffer (low-importance events) -----

    # Lazily initialised digest wrapper — kept as an attribute on the
    # TelegramService so callers can do `telegram.buffer(...)` without
    # changing every function signature in main_service.py.
    _digest: "TelegramDigest | None" = None

    @property
    def digest(self) -> "TelegramDigest":
        if self._digest is None:
            self._digest = TelegramDigest(self.send, chat_id=self.chat_id)
        return self._digest

    def buffer(self, event: str, level: str = "info", detail: str = "") -> None:
        """Append a low-importance event for the daily digest (no send)."""
        self.digest.buffer(event, level=level, detail=detail)

    def flush_digest(self) -> bool:
        """Send the buffered digest. Returns True if anything was sent."""
        return self.digest.flush_digest()

    def digest_stats(self) -> dict:
        return self.digest.stats()

# ============== CRAWLER SERVICE ==============
class CrawlerService:
    def __init__(self, telegram: TelegramService):
        self.telegram = telegram
        self.is_running = False
        self.last_run = None
        self.last_result = None
        self.data_path = Path(os.environ.get("DATA_DIR", "/app/data"))
    
    def run_crawl_news(self) -> dict:
        """Crawl from each source → chạy pipeline 3 lớp → flush lên Drive.

        Flow (Bronze/Silver/Gold):
          1. Crawler 4 nguồn → ArticleSchema list
          2. Pipeline.process_batch() cho từng nguồn → Bronze+Silver+Gold+Parquet
          3. SAU KHI tất cả 4 nguồn xong → push Gold JSON lên Drive
             (chia theo source, mỗi nguồn 1 file riêng đúng folder của nó)

        Why push sau cùng:
          - Gold file là append-only theo ngày → cuối crawl mới đầy đủ.
          - Nếu push trong loop, mỗi source upload nguyên file (chứa cả 4
            nguồn) vào folder riêng → spam Drive trùng nội dung 4 lần.
          - Cách mới: cuối loop, đọc Gold, chia record theo source_name,
            upload mỗi phần vào folder đúng nguồn.

        Why health_check trước:
          Nếu credentials sai / token hết hạn, health_check() trả False
          → toàn bộ crawl vẫn chạy + lưu local (Bronze/Silver/Gold), chỉ
          skip Drive upload. User nhận được thông báo rõ ràng trong digest.
        """
        logger.info("Starting news crawl (Bronze→Silver→Gold)...")
        start = time.time()
        try:
            sys.path.insert(0, '/app')
            from src.crawlers import VNExpressCrawler, DanTriCrawler, TuoiTreCrawler, VietnamNetCrawler
            from src.storage import build_sink_from_env
            from src.pipeline import get_pipeline

            sink = build_sink_from_env()
            sink_ok = sink.health_check()
            logger.info("Cloud sink=%s healthy=%s", sink.name, sink_ok)
            if not sink_ok:
                logger.warning(
                    "Sink %s health check failed — crawl vẫn chạy nhưng sẽ "
                    "không push lên %s. Check GOOGLE_DRIVE_CREDENTIALS_PATH "
                    "và GOOGLE_DRIVE_FOLDER_ID trên Railway.",
                    sink.name, sink.name,
                )

            pipeline = get_pipeline()
            totals = {
                'crawled': 0,       # số bài crawler trả về
                'bronze': 0,        # số bài ghi vào Bronze
                'silver': 0,        # số bài ghi vào Silver (sau dedup)
                'gold': 0,          # số bài ghi vào Gold
                'parquet': 0,       # số bài ghi vào Parquet
                'duplicates': 0,    # số bài crawler trùng → skip
                'rejected': 0,      # số bài bị lọc (quảng cáo, rác)
                'uploaded': 0,      # số nguồn upload Drive thành công
                'upload_failed': 0, # số nguồn upload Drive fail
            }
            per_source: List[Dict] = []

            for name, cls in [
                ('VNExpress', VNExpressCrawler),
                ('DanTri', DanTriCrawler),
                ('TuoiTre', TuoiTreCrawler),
                ('VietnamNet', VietnamNetCrawler)
            ]:
                try:
                    instance = cls()
                    results = instance.crawl_all(today_only=True)
                    logger.info("%s: crawled %d articles", name, len(results))
                    totals['crawled'] += len(results)

                    if not results:
                        per_source.append({'source': name, 'articles': 0})
                        continue

                    # Bronze → Silver → Gold → Parquet
                    p_result = pipeline.process_batch(source=name, articles=results)
                    if not p_result.ok:
                        logger.error("Pipeline failed for %s: %s", name, p_result.error)
                        per_source.append({'source': name, 'error': p_result.error})
                        continue

                    totals['bronze'] += p_result.bronze.written
                    totals['silver'] += p_result.silver.written
                    totals['gold'] += p_result.gold.written
                    totals['parquet'] += p_result.parquet.written
                    totals['duplicates'] += p_result.silver.duplicates
                    totals['rejected'] += p_result.silver.rejected

                    per_source.append({
                        'source': name,
                        'crawled': len(results),
                        'bronze': p_result.bronze.written,
                        'silver': p_result.silver.written,
                        'gold': p_result.gold.written,
                        'duplicates': p_result.silver.duplicates,
                    })
                except Exception as e:
                    logger.exception(f"{name} error: {e}")
                    per_source.append({'source': name, 'error': str(e)})

            # ---- Drive push SAU CÙNG: chia Gold theo source_name ----
            if sink_ok and totals['gold'] > 0:
                today_str = datetime.now(timezone.utc).strftime('%Y%m%d')
                gold_path = pipeline.gold_dir / f"gold_{today_str}.json"
                if not gold_path.exists():
                    logger.error("Gold file %s missing — skip Drive push", gold_path)
                else:
                    try:
                        all_gold = json.loads(gold_path.read_text(encoding="utf-8"))
                        # Group records by source_name để push đúng folder.
                        by_source: Dict[str, List[Dict]] = {}
                        for rec in all_gold:
                            by_source.setdefault(rec.get("source_name", "Unknown"), []).append(rec)

                        ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                        for source_name, records in by_source.items():
                            payload = {
                                "source": source_name,
                                "layer": "gold",
                                "crawled_at": datetime.now(timezone.utc).isoformat(),
                                "article_count": len(records),
                                "records": records,
                            }
                            file_id = sink.write_payload(
                                source=source_name,
                                payload=payload,
                                filename=f"gold_{source_name}_{today_str}_{ts}.json",
                            )
                            if file_id:
                                totals['uploaded'] += 1
                                logger.info(
                                    "Drive push OK: %s (%d records, file_id=%s)",
                                    source_name, len(records), file_id,
                                )
                            else:
                                totals['upload_failed'] += 1
                                logger.error(
                                    "Drive push FAILED: %s (%d records)",
                                    source_name, len(records),
                                )
                    except Exception as e:
                        logger.exception("Drive push batch failed: %s", e)
                        # Toàn bộ upload tính là fail để user biết.
                        totals['upload_failed'] += len(by_source) if 'by_source' in dir() else 1

            elapsed = time.time() - start
            self.last_run = datetime.now()
            self.last_result = {
                'success': True,
                'totals': totals,
                'sink': sink.name,
                'sink_ok': sink_ok,
                'per_source': per_source,
                'time': elapsed,
            }
            return self.last_result
        except Exception as e:
            logger.exception(f"Crawl error: {e}")
            self.last_result = {'success': False, 'error': str(e)}
            return self.last_result
    
    def run_crawl_raw(self) -> dict:
        logger.info("Starting raw crawl...")
        start = time.time()
        try:
            sys.path.insert(0, '/app')
            from src.services.google_drive_service import GoogleDriveService

            creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
            if not creds_path or not os.path.exists(creds_path):
                logger.warning("Raw crawl skipped: GOOGLE_CREDENTIALS_PATH not configured.")
                return {'success': False, 'error': 'No credentials configured', 'files': 0}

            drive = GoogleDriveService(credentials_path=creds_path, use_oauth=False)
            files = drive.download_new_files() if hasattr(drive, 'download_new_files') else []
            elapsed = time.time() - start
            return {'success': True, 'files': len(files), 'time': elapsed}
        except Exception as e:
            logger.error(f"Raw crawl error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_data_stats(self) -> dict:
        stats = {'raw': 0, 'silver': 0, 'gold': 0}
        for folder, key in [('raw', 'raw'), ('silver', 'silver'), ('gold', 'gold')]:
            try:
                stats[key] = len(list((self.data_path / folder).glob('*.json')))
            except:
                pass
        return stats

    def get_layer_stats(self) -> dict:
        """Đếm file Bronze/Silver/Gold/Parquet — dùng cho /status, /layerstats.

        Bronze: tất cả raw_crawl_*.json (mỗi batch 1 file).
        Silver: silver_*.json (mỗi ngày 1 file + _hashes).
        Gold:   gold_*.json (mỗi ngày 1 file + _hashes).
        Parquet: đếm số part-*.parquet qua các partition.
        """
        out = {"bronze": 0, "silver": 0, "gold": 0, "parquet": 0}
        try:
            out["bronze"] = len(list((self.data_path / "raw").glob("raw_crawl_*.json")))
        except Exception:
            pass
        try:
            out["silver"] = len([p for p in (self.data_path / "silver").glob("silver_*.json")
                                 if not p.name.endswith("_hashes.json")])
        except Exception:
            pass
        try:
            out["gold"] = len([p for p in (self.data_path / "gold").glob("gold_*.json")
                               if not p.name.endswith("_hashes.json")])
        except Exception:
            pass
        try:
            out["parquet"] = len(list((self.data_path / "parquet").rglob("part-*.parquet")))
        except Exception:
            pass
        return out

    def get_folder_size(self, folder: str) -> float:
        total = 0
        try:
            for f in (self.data_path / folder).rglob('*'):
                if f.is_file():
                    total += f.stat().st_size
        except:
            pass
        return total / (1024 * 1024)

# ============== BOT COMMANDS ==============
class BotCommands:
    def __init__(self, crawler: CrawlerService, telegram: TelegramService):
        self.crawler = crawler
        self.telegram = telegram
        self.offset = 0
        self.running = True
        # Cached RAG chain + last init error so /ask can surface the real
        # cause instead of a generic "RAG chưa khả dụng" line.
        self._rag_chain = None
        self._rag_last_error: str | None = None
    
    def cmd_start(self) -> str:
        return """🤖 <b>Data Platform Bot - Online!</b>

✅ Hệ thống đang chạy tự động với pipeline <b>Bronze/Silver/Gold</b>
⏰ Auto-crawl: 7h sáng, 19h chiều
📊 Daily report: 23h
🗑️ Auto-cleanup: 4h sáng (xoá data > 7 ngày)
📋 Daily digest: 20h (1 tin nhắn tổng hợp)

<b>📥 Data Commands:</b>
/crawl - Chạy crawl ngay (Bronze→Silver→Gold)
/raw - Crawl Google Drive
/status - Trạng thái hệ thống (3 lớp)
/layerstats - Chi tiết Bronze/Silver/Gold hôm nay
/drives - Thống kê file trên Drive
/report - Báo cáo hôm nay
/dashboard - Thống kê chi tiết
/testdrive - Test Drive credentials + write_payload thật

<b>🔮 RAG Chatbot (Q&A về tin tức):</b>
/index - Build vector index từ Gold layer
/ragstats - Thống kê vector store
/news - Bản tin thời sự (digest 48h)
/ask &lt;câu hỏi&gt; - Hỏi AI về tin tức
/snapshot - Push RAG index snapshot → Drive (24/7)

<b>💾 Backup & Storage:</b>
/backup - Backup data → Drive
/cleanup [days] - Xoá data cũ (mặc định 7 ngày)
/pull_today - Kéo Gold từ Drive → Bronze→Silver→Gold + reindex RAG
/prune_local - Xoá local JSON+parquet cũ (Drive vẫn giữ)
/logs - Xem 30 dòng log cuối

<b>📋 Notifications:</b>
/digest - Xem tổng hợp events đã buffer
/digeststats - Bao nhiêu event đang chờ digest

<b>⚙️ System:</b>
/restart - Khởi động lại bot"""
    
    def cmd_status(self) -> str:
        data = self.crawler.get_data_stats()
        layers = self.crawler.get_layer_stats()
        last = self.crawler.last_run.strftime('%H:%M:%S') if self.crawler.last_run else "Chưa chạy"
        last_res = self.crawler.last_result or {}
        totals = last_res.get('totals', {}) if last_res.get('success') else {}

        return f"""📊 <b>System Status</b>

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔄 Last crawl: {last}
🏷 Build: <code>import-fix-v2</code>

📁 <b>Data Layers (3-tier):</b>
🥉 Bronze:  <code>{layers.get('bronze', 0)}</code> files
🥈 Silver:  <code>{layers.get('silver', 0)}</code> files
🥇 Gold:    <code>{layers.get('gold', 0)}</code> files
📦 Parquet: <code>{layers.get('parquet', 0)}</code> files

🔄 <b>Last crawl breakdown:</b>
• Crawled: {totals.get('crawled', 0)}
• Bronze:  {totals.get('bronze', 0)}
• Silver:  {totals.get('silver', 0)} (dups: {totals.get('duplicates', 0)})
• Gold:    {totals.get('gold', 0)}
• Parquet: {totals.get('parquet', 0)}
• Drive upload: {totals.get('uploaded', 0)}/{totals.get('uploaded', 0) + totals.get('upload_failed', 0)}
• Drive healthy: {last_res.get('sink_ok', '?')} (sink={last_res.get('sink', '?')})

🔄 <b>Auto Schedule:</b>
• 07:00 - Morning crawl
• 07:30 - Pull sáng (Drive → RAG)
• 19:00 - Evening crawl
• 19:30 - Pull tối (Drive → RAG)
• 23:00 - Daily report
• 23:15 - Prune local (giải phóng volume)
• 23:30 - Backup → Drive
• 04:00 - Daily cleanup (TTL 7d)"""

    def cmd_layerstats(self) -> str:
        """Hiển thị chi tiết Bronze/Silver/Gold/Parquet files hôm nay."""
        try:
            from src.pipeline import get_pipeline
            pipeline = get_pipeline()
            today = datetime.now(timezone.utc).strftime("%Y%m%d")
            lines = [f"📊 <b>Bronze/Silver/Gold — {today}</b>\n"]
            # Bronze files today
            bronze_today = sorted(pipeline.bronze_dir.glob("raw_crawl_*.json"))
            if bronze_today:
                lines.append(f"🥉 <b>Bronze</b> ({len(bronze_today)} files):")
                for p in bronze_today[-5:]:
                    lines.append(f"   • <code>{p.name}</code> ({p.stat().st_size // 1024} KB)")
                if len(bronze_today) > 5:
                    lines.append(f"   ... +{len(bronze_today) - 5} more")
            else:
                lines.append("🥉 <b>Bronze</b>: (empty)")

            silver_today = pipeline.silver_dir / f"silver_{today}.json"
            if silver_today.exists():
                import json
                data = json.loads(silver_today.read_text())
                lines.append(f"\n🥈 <b>Silver</b>: <code>{silver_today.name}</code> ({len(data)} records)")
            else:
                lines.append("\n🥈 <b>Silver</b>: (no file today)")

            gold_today = pipeline.gold_dir / f"gold_{today}.json"
            if gold_today.exists():
                import json
                data = json.loads(gold_today.read_text())
                lines.append(f"🥇 <b>Gold</b>: <code>{gold_today.name}</code> ({len(data)} records)")
            else:
                lines.append("🥇 <b>Gold</b>: (no file today)")

            # Parquet partitions
            parq = list(pipeline.parquet_dir.glob("source=*/year=*/month=*/day=*/*.parquet"))
            if parq:
                lines.append(f"\n📦 <b>Parquet</b>: {len(parq)} part files")
                # Count by source
                from collections import Counter
                src_counts = Counter(p.parts[-5].split("=")[1] for p in parq)
                for s, n in sorted(src_counts.items()):
                    lines.append(f"   • <b>{s}</b>: {n} parts")
            return "\n".join(lines)
        except Exception as e:
            logger.error("cmd_layerstats: %s", e)
            return f"❌ Lỗi: {str(e)[:200]}"
    
    def cmd_crawl(self) -> str:
        if self.crawler.is_running:
            return "⚠️ <b>Đang crawl...</b>\nVui lòng đợi hoàn thành."
        self.telegram.send("🔄 <b>Đang crawl tin tức...</b>")
        def run():
            self.crawler.is_running = True
            result = self.crawler.run_crawl_news()
            self.crawler.is_running = False
            if result['success']:
                self.telegram.send(f"✅ <b>Crawl hoàn thành!</b>\n📰 {result['articles']} bài viết\n⏱️ {result['time']:.1f}s")
            else:
                self.telegram.send(f"❌ <b>Lỗi:</b> {result.get('error', 'Unknown')}")
        threading.Thread(target=run, daemon=True).start()
        return "🚀 <b>Đã khởi động crawl!</b>\nBạn sẽ nhận thông báo khi xong."
    
    def cmd_raw(self) -> str:
        if self.crawler.is_running:
            return "⚠️ <b>Đang crawl...</b>\nVui lòng đợi."
        self.telegram.send("🔄 <b>Đang crawl Google Drive...</b>")
        def run():
            result = self.crawler.run_crawl_raw()
            if result['success']:
                self.telegram.send(f"✅ <b>Raw crawl hoàn thành!</b>\n📁 {result['files']} files\n⏱️ {result['time']:.1f}s")
            else:
                self.telegram.send(f"❌ <b>Lỗi:</b> {result.get('error', 'Unknown')}")
        threading.Thread(target=run, daemon=True).start()
        return "🚀 <b>Đã khởi động raw crawl!</b>"
    
    def cmd_report(self) -> str:
        data = self.crawler.get_data_stats()
        last_result = self.crawler.last_result
        return f"""📊 <b>Daily Report - {datetime.now().strftime('%Y-%m-%d')}</b>

📁 <b>Tổng quan data:</b>
• Raw: {data['raw']} files
• Silver: {data['silver']} files
• Gold: {data['gold']} files

🔄 <b>Last crawl:</b>
• Time: {self.crawler.last_run.strftime('%H:%M:%S') if self.crawler.last_run else 'N/A'}
• Status: {'✅ Thành công' if last_result and last_result.get('success') else '❌ Thất bại'}

⏰ Report generated: {datetime.now().strftime('%H:%M:%S')}"""
    
    def cmd_dashboard(self) -> str:
        data = self.crawler.get_data_stats()
        raw_size = self.crawler.get_folder_size('raw')
        silver_size = self.crawler.get_folder_size('silver')
        gold_size = self.crawler.get_folder_size('gold')
        return f"""📈 <b>Dashboard</b>

📦 <b>Storage:</b>
• Raw: {raw_size:.1f} MB
• Silver: {silver_size:.1f} MB
• Gold: {gold_size:.1f} MB
• Total: {raw_size + silver_size + gold_size:.1f} MB

📁 <b>Files:</b>
• Raw: {data['raw']}
• Silver: {data['silver']}
• Gold: {data['gold']}

🔄 <b>Uptime:</b>
• Bot started: {datetime.now().strftime('%Y-%m-%d %H:%M')}
• Last crawl: {self.crawler.last_run.strftime('%H:%M:%S') if self.crawler.last_run else 'N/A'}"""
    
    def cmd_drivestats(self) -> str:
        """Read statistics from Google Drive"""
        try:
            from src.services.google_drive_service import get_drive_service

            drive = get_drive_service()

            if not drive.service:
                return (
                    "❌ <b>Drive không khả dụng</b>\n\n"
                    "Lý do: thiếu credentials hoặc token hết hạn.\n"
                    "Trên Railway cần upload credentials để đọc Drive."
                )

            self.telegram.send("📁 <b>Đang quét Google Drive...</b>")

            stats = drive.get_drive_stats()

            if 'error' in stats:
                return f"❌ Lỗi đọc Drive: {stats['error']}"

            msg = f"""📁 <b>Thống kê Google Drive</b>

<b>Tổng quan:</b>
• Tổng file: <b>{stats['total_files']}</b>
• File dữ liệu (JSON): <b>{stats['total_articles']}</b>

<b>Chi tiết theo nguồn:</b>"""

            for src in sorted(stats['sources_detail'], key=lambda x: x['name']):
                latest = src['latest'][:10] if src['latest'] else 'N/A'
                msg += f"\n• <b>{src['name']}</b>: {src['file_count']} files ({src['json_count']} bài) - {latest}"

            if stats['last_updated']:
                msg += f"\n\n<i>🕐 Cập nhật cuối: {stats['last_updated'][:19].replace('T', ' ')}</i>"

            return msg

        except Exception as e:
            logger.error(f"cmd_drivestats error: {e}")
            return f"❌ Lỗi: {str(e)[:200]}"

    def cmd_testdrive(self) -> str:
        """Diagnostic: test Drive credentials + thử push 1 payload thật.

        Dùng khi crawl xong mà Drive trống — giúp tách lỗi giữa:
          1. credentials path sai
          2. parent_folder_id sai / không có quyền share
          3. Service Account hết hạn / sai scopes
          4. write_payload bug
        """
        try:
            import os as _os
            from datetime import datetime, timezone
            from src.storage import build_sink_from_env

            creds = (
                _os.environ.get("GOOGLE_DRIVE_CREDENTIALS")
                or _os.environ.get("GOOGLE_DRIVE_CREDENTIALS_PATH")
                or _os.environ.get("GOOGLE_CREDENTIALS_PATH")
            )
            folder_id = _os.environ.get("GOOGLE_DRIVE_FOLDER_ID")

            creds_exists = bool(creds) and Path(creds).exists()
            lines = ["🧪 <b>Drive diagnostic</b>\n"]
            lines.append(f"• GOOGLE_DRIVE_CREDENTIALS: <code>{creds or '(unset)'}</code>")
            lines.append(f"• File exists: <b>{creds_exists}</b>")
            lines.append(f"• GOOGLE_DRIVE_FOLDER_ID: <code>{folder_id or '(unset)'}</code>")

            if not creds_exists:
                return "\n".join(lines) + "\n\n❌ Credentials file KHÔNG tồn tại trong container."
            if not folder_id:
                return "\n".join(lines) + "\n\n❌ Thiếu GOOGLE_DRIVE_FOLDER_ID."

            sink = build_sink_from_env()
            lines.append(f"• Sink type: <b>{sink.name}</b>")
            sink_ok = sink.health_check()
            lines.append(f"• health_check(): <b>{sink_ok}</b>")
            if not sink_ok:
                return "\n".join(lines) + "\n\n❌ Sink không khởi tạo được — check Service Account."

            # Thử push 1 payload test nhỏ.
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            test_payload = {
                "source": "TEST",
                "layer": "test",
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "article_count": 1,
                "records": [{
                    "test": True,
                    "ts": ts,
                    "msg": "Hello from data-platform bot — safe to remove this file.",
                }],
            }
            file_id = sink.write_payload(
                source="TEST",
                payload=test_payload,
                filename=f"drive_test_{ts}.json",
            )
            if file_id:
                lines.append(f"• write_payload(): <b>✅ OK</b> (file_id=<code>{file_id}</code>)")
                lines.append("\n🎉 Drive hoạt động bình thường. /crawl sẽ push lên được.")
            else:
                lines.append("• write_payload(): <b>❌ FAILED</b>")
                lines.append("\n❌ Upload thật fail. Check quyền Service Account trên folder.")
            return "\n".join(lines)
        except Exception as e:
            logger.exception("cmd_testdrive: %s", e)
            return f"❌ Lỗi diagnostic: {str(e)[:200]}"

    def cmd_restart(self) -> str:
        self.telegram.send("🔄 <b>Đang khởi động lại...</b>")
        time.sleep(2)
        self.telegram.send("✅ <b>Bot đã restart!</b>")
        time.sleep(1)
        os.execv(sys.executable, [sys.executable] + sys.argv)

    # ----- RAG commands (lazy loaded) -----
    _rag_chain = None
    _rag_indexed = False

    def _get_rag(self):
        """Lazily construct RAGChain around a PersistentVectorStore.

        On the very first call we attempt to restore the index from
        Drive if the local chroma dir is empty — that way a fresh
        container can answer /ask immediately after boot, even if the
        volume was wiped.

        Failures used to be silently swallowed with just a one-liner
        "RAG chưa khả dụng", which made it impossible to tell from the
        bot whether the issue was:
          - a missing module (chromadb/sentence-transformers not installed),
          - a Drive credentials problem,
          - an OOM during model load,
          - a corrupt chroma sqlite file,
        so we now capture the full traceback and send it to Telegram.
        """
        if self._rag_chain is not None:
            return self._rag_chain
        logger.info("RAG: _get_rag called for the first time; initialising chain...")
        t0 = time.time()
        try:
            import traceback

            from src.rag import RAGChain, GeminiClient
            from src.rag.persistent_store import get_persistent_store

            logger.info("RAG: constructing PersistentVectorStore...")
            store = get_persistent_store()
            logger.info("RAG: estimating local count at %s", store.persist_dir)
            local = store._estimate_local_count()
            logger.info("RAG: local chroma has %s embeddings", local)

            # Auto-restore from Drive only the first time we touch the
            # store on this container, not on every query.
            if store._restored_from is None and local == 0:
                logger.info("RAG: store empty, attempting Drive restore...")
                self.telegram.send(
                    "♻️ <b>Local index trống, đang restore từ Drive snapshot...</b>\n"
                    "⏳ Có thể mất 1-2 phút lần đầu."
                )
                try:
                    restored = store.restore_from_drive()
                except Exception as restore_err:
                    logger.error("Drive restore failed: %s", restore_err)
                    restored = False
                if restored:
                    logger.info(
                        "RAG boot: restored index from Drive snapshot %s",
                        store._restored_from,
                    )
                    self.telegram.send(
                        f"♻️ <b>RAG index restored từ Drive snapshot</b>\n"
                        f"📦 Snapshot: <code>{store._restored_from}</code>"
                    )
                else:
                    logger.warning("RAG: no Drive snapshot restored; will run empty")
                    self.telegram.send(
                        "⚠️ <b>Không restore được từ Drive</b>\n"
                        "Có thể chưa có snapshot, hoặc Drive credentials chưa config.\n"
                        "Gửi <code>/index</code> để build từ parquet."
                    )

            logger.info("RAG: constructing RAGChain (this loads sentence-transformers)...")
            chain = RAGChain(store, GeminiClient())
            self._rag_chain = chain
            self._rag_last_error = None
            logger.info("RAG: chain ready in %.1fs", time.time() - t0)
            return chain
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Failed to init RAG chain: {e}\n{tb}")
            # Stash the error so /ask can return it directly without
            # relying on a second telegram.send that may itself fail.
            self._rag_last_error = f"{type(e).__name__}: {e}"
            try:
                short_tb = tb[-1200:] if len(tb) > 1200 else tb
                self.telegram.send(
                    "❌ <b>RAG init failed</b>\n\n"
                    f"<code>{str(e)[:300]}</code>\n\n"
                    "<b>Traceback:</b>\n"
                    f"<pre><code>{short_tb}</code></pre>"
                )
            except Exception:
                pass
            return None

    def cmd_ask(self, question: str) -> str:
        """RAG: answer a question using crawled articles.

        Routing:
          - Vague questions ("tin gì mới", "có gì hot") -> news_digest mode,
            which synthesizes the latest crawled batch across sources.
          - Specific questions ("Bộ trưởng X nói gì") -> standard semantic QA.
        """
        # Instant "thinking" feedback so /ask never silently hangs.
        self.telegram.send(
            f"🔮 <b>Đang tra cứu...</b>\n"
            f"❓ Câu hỏi: <i>{question[:200]}</i>\n"
            f"⏳ Model cold-start có thể mất 30-60s lần đầu."
        )
        chain = self._get_rag()
        if chain is None:
            err = self._rag_last_error or "unknown error"
            return (
                "❌ <b>RAG chưa khả dụng.</b>\n\n"
                f"<b>Lỗi:</b> <code>{err[:300]}</code>\n\n"
                "Kiểm tra log (`/logs`) để xem traceback đầy đủ, "
                "hoặc gửi <code>/index</code> để retry."
            )

        if chain.store.count == 0:
            return (
                "⚠️ Vector store trống.\n"
                "Chạy /index trước để build embeddings từ dữ liệu đã crawl."
            )

        try:
            result = chain.ask(question, top_k=3)  # 3 chunks fits comfortably in 512 MB
        except Exception as e:
            logger.error("RAG ask failed: %s", e)
            return f"❌ RAG ask failed: {e}"

        mode_emoji = "📰" if result.get("mode") == "digest" else "🔎"
        mode_label = (
            "News Digest" if result.get("mode") == "digest" else "RAG Answer"
        )

        return (
            f"{mode_emoji} <b>{mode_label}</b>\n\n"
            f"{result['answer']}\n\n"
            f"<b>📚 Nguồn tham khảo:</b>\n{result['sources']}"
        )

    def cmd_news(self) -> str:
        """Force a news digest (bypasses the question-routing heuristic)."""
        # Send an instant "I'm working on it" message so the user
        # always sees feedback, even if the embedding/model load
        # takes 30+ seconds on a cold start.
        self.telegram.send("📰 <b>Đang tổng hợp bản tin...</b>\n⏳ Lần đầu có thể mất 30-60s (đang load model).")
        chain = self._get_rag()
        if chain is None:
            err = self._rag_last_error or "unknown error"
            return f"❌ RAG chưa khả dụng.\n<code>{err[:200]}</code>"
        if chain.store.count == 0:
            return (
                "⚠️ <b>Vector store trống.</b>\n"
                "Gửi <code>/index</code> trước để build embeddings từ dữ liệu đã crawl."
            )
        try:
            result = chain.ask_digest("Tổng hợp tin tức mới nhất trong 48h qua", top_k=12)
        except Exception as e:
            logger.error("ask_digest failed: %s", e)
            return f"❌ Digest failed: {e}"
        if not result.get("answer"):
            return "📭 Không tìm được bài nào để tổng hợp."
        return (
            f"📰 <b>Bản tin thời sự</b>\n\n"
            f"{result['answer']}\n\n"
            f"<b>📚 Nguồn:</b>\n{result['sources']}"
        )

    def cmd_index(self) -> str:
        """Build / rebuild the vector index từ Gold layer.

        Gold là single source of truth cho RAG — đã dedup, đã join content.
        Reset Chroma rồi re-embed từ /app/data/gold/gold_*.json.
        """
        try:
            from src.pipeline import get_pipeline
            chain = self._get_rag()
            if chain is None:
                err = self._rag_last_error or "unknown error"
                return f"❌ RAG chưa khả dụng.\n<code>{err[:200]}</code>"

            self.telegram.send(
                "📥 <b>Đang build vector index từ Gold layer...</b>\n"
                "⏳ Có thể mất 1-2 phút lần đầu (tải model)."
            )
            # Reset Chroma trước khi rebuild.
            chain.store.reset()

            pipeline = get_pipeline()
            stats = pipeline.rebuild_index()

            # Re-init chain để pick up collection mới.
            self._rag_chain = None
            chain = self._get_rag()

            # Sau khi index xong, snapshot lên Drive để container sau restore được.
            try:
                chain.store.snapshot_to_drive()
            except Exception as e:
                logger.warning("Auto-snapshot after /index failed: %s", e)

            return (
                f"✅ <b>Index hoàn thành!</b>\n\n"
                f"📊 Indexed: <b>{stats.get('indexed', 0)}</b> vectors "
                f"từ {stats.get('files', 0)} gold files\n"
                f"🥇 Source: <code>/app/data/gold/gold_*.json</code>\n"
                f"☁️ Auto-snapshot pushed → Drive"
            )
        except Exception as e:
            logger.error(f"Index error: {e}")
            return f"❌ Lỗi index: {str(e)[:200]}"

    def cmd_ragstats(self) -> str:
        """Show RAG vector store stats + persistence status."""
        chain = self._get_rag()
        if chain is None:
            err = self._rag_last_error or "unknown error"
            return f"❌ RAG chưa khả dụng.\n<code>{err[:200]}</code>"
        store = chain.store
        gemini_status = "✅ Ready" if chain.gemini.is_available() else "⚠️ Chưa có API key (extractive mode)"

        snap_at = (
            store._last_snapshot_at.isoformat() if getattr(store, "_last_snapshot_at", None) else "—"
        )
        restored_from = getattr(store, "_restored_from", None) or "—"

        return (
            f"🔮 <b>RAG Stats</b>\n\n"
            f"📦 Articles indexed: <b>{chain.store.count}</b>\n"
            f"🤖 Gemini: {gemini_status}\n"
            f"📐 Embedding: all-MiniLM-L6-v2 (lightweight, ~80 MB RAM)\n\n"
            f"<b>💾 Persistence (24/7):</b>\n"
            f"📁 Local: <code>{store.persist_dir}</code>\n"
            f"☁️ Drive folder: <b>{store.snapshot_folder}</b>\n"
            f"🕐 Last Drive snapshot: {snap_at}\n"
            f"♻️ Restored from: <code>{restored_from}</code>"
        )

    def cmd_snapshot(self) -> str:
        """Push a Drive snapshot of the current chroma dir manually."""
        chain = self._get_rag()
        if chain is None:
            err = self._rag_last_error or "unknown error"
            return f"❌ RAG chưa khả dụng.\n<code>{err[:200]}</code>"
        self.telegram.send("📤 <b>Đang snapshot RAG index → Drive...</b>")
        try:
            file_id = chain.store.snapshot_to_drive()
            if file_id:
                return f"✅ Snapshot uploaded → Drive/<b>{chain.store.snapshot_folder}</b>\n🆔 <code>{file_id}</code>"
            return "⚠️ Snapshot skipped (no Drive credentials configured)."
        except Exception as e:
            logger.error(f"snapshot error: {e}")
            return f"❌ Snapshot lỗi: {str(e)[:200]}"

    def cmd_cleanup(self, days: str = "") -> str:
        """Manually trigger data cleanup. Args: <days> (default 7)."""
        try:
            from scripts.cleanup import cleanup_old_data, format_cleanup_summary
            n = int(days) if days.strip().isdigit() else 7
            self.telegram.send(f"🗑️ <b>Cleanup đang chạy (max_age={n}d)...</b>")
            result = cleanup_old_data(max_age_days=n)
            return format_cleanup_summary(result)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return f"❌ Lỗi cleanup: {str(e)[:200]}"

    def cmd_pull_today(self) -> str:
        """Pull Drive JSON batches (last 24h) → Bronze/Silver/Gold pipeline.

        Sau khi pull xong thì rebuild vector index để /ask dùng được ngay.

        Lý do tồn tại:
          Crawler đẩy thẳng lên Drive để tránh OOM. Nhưng RAG cần gold
          cục bộ để build embeddings. Pull-and-Use lấp khoảng trống đó:
          sáng tải về, tối xoá local (Drive vẫn giữ bản gốc).
        """
        try:
            from src.storage import get_drive_puller
        except ImportError as e:
            return f"❌ Không import được helper: {e}"

        self.telegram.send(
            "📥 <b>Pulling data từ Drive về pipeline...</b>\n"
            "⏳ Có thể mất 30-60s tuỳ số file."
        )

        try:
            puller = get_drive_puller()
            sources = ["VNExpress", "DanTri", "TuoiTre", "VietnamNet"]
            result = puller.sync_today(sources, reindex=True)
        except Exception as e:
            logger.error("pull_today: %s", e)
            return f"❌ Pull lỗi: {str(e)[:200]}"

        if not result.get("ok"):
            reason = result.get("reason", "unknown")
            return (
                f"⚠️ <b>Pull bị skip:</b> <code>{reason}</code>\n\n"
                "Kiểm tra GOOGLE_DRIVE_CREDENTIALS_PATH và "
                "GOOGLE_DRIVE_FOLDER_ID trên Railway."
            )

        per_source = result.get("per_source", {})
        lines = ["✅ <b>Pull + pipeline done!</b>\n"]
        for src, info in per_source.items():
            if info["files"] == 0 and info["articles"] == 0:
                continue
            pipeline_info = info.get("pipeline", {}) or {}
            gold = pipeline_info.get("gold", {}).get("written", 0)
            silver = pipeline_info.get("silver", {}).get("written", 0)
            lines.append(
                f"  • <b>{src}</b>: {info['files']} files, "
                f"{info['articles']} articles ({info['mb']} MB)\n"
                f"     🥈 Silver +{silver} | 🥇 Gold +{gold}"
            )
        lines.append(
            f"\n📦 Downloaded: {result['downloaded']}, "
            f"⏭️ Skipped (cached): {result['skipped']}"
        )
        lines.append(f"🔮 RAG reindexed: +{result.get('indexed', 0)} vectors")
        return "\n".join(lines)

    def cmd_prune_local(self) -> str:
        """Xoá local JSON + parquet cũ hơn PULL_TODAY_KEEP_LOCAL_HOURS.

        Drive snapshot vẫn giữ — chỉ giải phóng volume. Sau lệnh này
        /ask sẽ trả "no relevant articles" cho đến khi gọi /pull_today
        hoặc /index lại.
        """
        try:
            from src.storage import get_drive_puller
            puller = get_drive_puller()
            result = puller.prune_local()
        except Exception as e:
            logger.error("prune_local: %s", e)
            return f"❌ Lỗi prune: {str(e)[:200]}"

        chroma_note = (
            "🧹 Chroma cleared (cần /index để khôi phục)."
            if result.get("chroma_cleared")
            else "✓ Chroma giữ nguyên (còn trong keep_hours)."
        )
        return (
            f"🧹 <b>Pruned local data</b> (> {result['keep_hours']}h)\n\n"
            f"📄 Files deleted: <b>{result['deleted_files']}</b>\n"
            f"💾 MB freed: <b>{result['bytes_freed_mb']}</b>\n"
            f"{chroma_note}\n\n"
            f"<i>Drive bản gốc vẫn còn. Gọi <code>/pull_today</code> "
            "để tải lại.</i>"
        )

    def cmd_backup(self) -> str:
        """Create a backup archive and push to Drive if available."""
        try:
            from src.backup import run_backup
            self.telegram.send("💾 <b>Đang tạo backup...</b>")
            result = run_backup(upload_to_drive=True, keep_local=7)
            if not result.get("ok"):
                return f"⚠️ Không có data để backup: {result.get('reason', '?')}"
            msg = (
                f"✅ <b>Backup hoàn thành!</b>\n\n"
                f"📦 File: <code>{Path(result['archive']).name}</code>\n"
                f"💽 Size: {result['size_mb']} MB\n"
            )
            if "drive_file_id" in result:
                msg += "☁️ Uploaded to Drive folder: <b>data-backups</b>"
            elif "drive_error" in result:
                msg += f"⚠️ Drive upload: {result['drive_error']}"
            if result.get("pruned_local"):
                msg += f"\n🗑️ Pruned {result['pruned_local']} old local archives"
            return msg
        except Exception as e:
            logger.error(f"Backup error: {e}")
            return f"❌ Backup lỗi: {str(e)[:200]}"

    def cmd_logs(self) -> str:
        """Show the last 30 lines of bot.log inline (no Drive round-trip).

        Why change from the old upload-logs-to-Drive behaviour:
          The old `/logs` command uploaded a file to Google Drive and pinged
          the user every hour. That both spammed the chat and required
          network setup. Now `/logs` is a pull-only command — the user
          asks, the bot sends back the tail of the file. Same data, less
          noise.
        """
        try:
            log_path = Path(os.environ.get("DATA_DIR", "/app/data")) / "logs" / "bot.log"
            if not log_path.exists():
                return "ℹ️  Chưa có log file (bot mới khởi động)."
            # Read last ~30 lines without loading the whole file.
            try:
                from collections import deque
                tail = deque(maxlen=30)
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        tail.append(line.rstrip())
            except OSError as e:
                return f"⚠️ Không đọc được log: {e}"
            body = "\n".join(tail)
            # Telegram hard limit is 4096 chars — trim the body to fit.
            head = f"📜 <b>bot.log</b> — last 30 lines\n<code>"
            tail_max = "</code>"
            max_body = 4096 - len(head) - len(tail_max) - 5
            if len(body) > max_body:
                body = "…\n" + body[-(max_body - 5):]
            return head + body + tail_max
        except Exception as e:
            logger.error("logs cmd: %s", e)
            return f"❌ Lỗi: {str(e)[:150]}"

    def cmd_digest(self) -> str:
        """Manually flush the buffered events. Same content the bot will
        ship automatically at 20:00, just on-demand."""
        msg = self.telegram.digest.format_digest()
        if msg is None:
            return "📋 <b>Digest</b>\nKhông có sự kiện nào được buffer hôm nay."
        # Send immediately AND clear the buffer.
        self.telegram.flush_digest()
        return msg

    def cmd_digeststats(self) -> str:
        stats = self.telegram.digest_stats()
        return (
            f"📋 <b>Digest buffer</b>\n"
            f"Buffered events: <b>{stats['buffered']}</b>\n"
            f"Capacity: {stats['cap']}\n\n"
            f"Auto-flush: <code>20:00</code> mỗi ngày\n"
            f"Hoặc gọi <code>/digest</code> để xem ngay."
        )
    
    def poll(self):
        import requests
        if not self.telegram.enabled or not self.telegram.token:
            logger.error("Telegram polling cannot start: bot is disabled or TELEGRAM_BOT_TOKEN is missing.")
            return
        api_url = f"{self.telegram.api_url}/getUpdates"

        # Delete any webhook (in case it was set) and drop pending updates
        # to avoid 409 Conflict with stale sessions
        try:
            requests.post(f"{self.telegram.api_url}/deleteWebhook", json={"drop_pending_updates": True}, timeout=10)
            logger.info("Webhook cleared (drop_pending_updates=True)")
        except Exception as e:
            logger.warning(f"Could not clear webhook: {e}")

        # Verify no other instance is polling the same token (PID lock)
        lock_path = Path(os.environ.get("DATA_DIR", "/app/data")) / ".bot.lock"
        if not acquire_singleton_lock(lock_path):
            logger.error("Exiting to prevent duplicate Telegram polling.")
            return

        # Wait longer (was 3s) to let any old container fully release the
        # long-poll connection. Railway zero-downtime deploys start the new
        # container before fully killing the old one.
        time.sleep(15)

        logger.info("Bot polling started!")
        self.telegram.send("🤖 <b>Bot Online!</b>\nHệ thống đang chạy 24/7")
        while self.running:
            try:
                params = {"offset": self.offset, "timeout": 30, "limit": 5}
                resp = requests.get(api_url, params=params, timeout=35)
                if resp.status_code != 200:
                    try:
                        description = resp.json().get("description", "Unknown Telegram API error")
                    except ValueError:
                        description = resp.text[:300]
                    logger.error(
                        "Telegram getUpdates failed (HTTP %s): %s",
                        resp.status_code,
                        description,
                    )
                    time.sleep(5)
                    continue
                data = resp.json()
                if not data.get('ok'):
                    logger.error("Telegram getUpdates returned an error: %s", data.get("description", "Unknown Telegram API error"))
                    time.sleep(5)
                    continue
                for update in data.get('result', []):
                    self.offset = update['update_id'] + 1
                    if 'message' not in update:
                        continue
                    msg = update['message']
                    if 'text' not in msg:
                        continue
                    text = msg['text'].strip()
                    text_lower = text.lower()
                    if not text_lower:
                        continue
                    command = text_lower.split(maxsplit=1)[0].split("@", 1)[0]
                    logger.info(f"Command: {text}")
                    response = None
                    if command in ['/start', '/help']:
                        response = self.cmd_start()
                    elif command == '/status':
                        response = self.cmd_status()
                    elif command == '/testdrive':
                        response = self.cmd_testdrive()
                    elif command == '/layerstats':
                        response = self.cmd_layerstats()
                    elif command in ['/drivestats', '/drives']:
                        response = self.cmd_drivestats()
                    elif command == '/crawl':
                        response = self.cmd_crawl()
                    elif command == '/raw':
                        response = self.cmd_raw()
                    elif command == '/report':
                        response = self.cmd_report()
                    elif command == '/index':
                        response = self.cmd_index()
                    elif command == '/ragstats':
                        response = self.cmd_ragstats()
                    elif command == '/snapshot':
                        response = self.cmd_snapshot()
                    elif command == '/news':
                        response = self.cmd_news()
                    elif command == '/backup':
                        response = self.cmd_backup()
                    elif command == '/cleanup':
                        arg = text[len(command):].strip() if text_lower.startswith(command) else ""
                        response = self.cmd_cleanup(arg)
                    elif command == '/pull_today':
                        response = self.cmd_pull_today()
                    elif command == '/prune_local':
                        response = self.cmd_prune_local()
                    elif command == '/logs':
                        response = self.cmd_logs()
                    elif command == '/digest':
                        response = self.cmd_digest()
                    elif command == '/digeststats':
                        response = self.cmd_digeststats()
                    elif command == '/ask':
                        question = text[len(command):].strip() if text_lower.startswith(command) else ""
                        if not question:
                            response = "💡 <b>Cách dùng:</b>\n<code>/ask Có tin gì về Hà Nội?</code>"
                        else:
                            response = self.cmd_ask(question)
                    elif command == '/restart':
                        response = self.cmd_restart()
                    else:
                        # Free-form message, no slash command. Treat it as
                        # a question for the RAG chatbot so the bot feels
                        # chatty instead of command-only.
                        if text.startswith('/'):
                            response = (
                                "❓ <b>Lệnh không hợp lệ:</b> "
                                f"<code>{command}</code>\n\n"
                                "Gõ <code>/help</code> để xem danh sách lệnh, "
                                "hoặc gửi câu hỏi bất kỳ để hỏi AI về tin tức."
                            )
                        else:
                            response = self.cmd_ask(text)
                    if response:
                        self.telegram.send(response)
            except requests.exceptions.ReadTimeout:
                continue
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Telegram connection reset (will retry): {e}")
                time.sleep(3)
                continue
            except Exception as e:
                logger.error(f"Poll error: {e}")
                time.sleep(5)

# ============== SCHEDULER ==============
def run_scheduler(telegram: TelegramService, crawler: CrawlerService):
    def job(hour: str, emoji: str, title: str):
        # Crawl start: low-importance, buffer instead of send. The
        # user sees a single "crawl done at 7:04" entry in the digest,
        # not a "crawl started" then "crawl done" pair.
        telegram.buffer(f"{emoji} Auto crawl — {hour}", "INFO")
        result = crawler.run_crawl_news()
        if result['success']:
            telegram.buffer(
                f"✅ Crawl OK — {result['articles']} bài",
                "OK",
                detail=f"{result['time']:.1f}s",
            )
        else:
            # Errors are still immediate — the user needs to know.
            err = result.get("error", "Unknown")
            telegram.send(f"❌ <b>Lỗi crawl:</b> <code>{err[:200]}</code>")
            telegram.buffer(f"❌ Crawl FAIL — {err[:80]}", "ERR")

    # News doesn't change minute-to-minute like weather, so 2 crawls
    # per day is enough to keep the index fresh without burning CPU.
    # Schedule: 07:00 morning briefing, 19:00 evening roundup.
    schedule.every().day.at("07:00").do(job, "7h Sáng", "🌅", "Morning")
    schedule.every().day.at("19:00").do(job, "19h Chiều", "🌆", "Evening")

    # ----- Pull-and-Use: sáng tải về, tối dọn local -----
    # Sau khi crawler 7h đẩy xong lên Drive, pull ngay về local để build
    # vector index cho /ask, /news trong ngày.
    def morning_pull():
        """Sau auto-crawl 7h: pull Drive về Bronze→Silver→Gold + reindex RAG."""
        try:
            from src.storage import get_drive_puller
            puller = get_drive_puller()
            sources = ["VNExpress", "DanTri", "TuoiTre", "VietnamNet"]
            result = puller.sync_today(sources, reindex=True)
            if not result.get("ok"):
                telegram.buffer(
                    f"⚠️ Pull sáng skipped — {result.get('reason', '?')}",
                    "WARN",
                )
                return
            total_files = sum(s["files"] for s in result["per_source"].values())
            total_articles = sum(s["articles"] for s in result["per_source"].values())
            telegram.buffer(
                f"📥 Pull sáng — {total_files} files, "
                f"{total_articles} articles, RAG +{result.get('indexed', 0)}",
                "OK",
                detail=f"dl={result['downloaded']}, skip={result['skipped']}",
            )
        except Exception as e:
            logger.error("morning_pull: %s", e)
            telegram.send(f"⚠️ Pull sáng lỗi: <code>{str(e)[:150]}</code>")

    # Sau khi crawler 19h đẩy xong, pull batch tối về local + reindex.
    def evening_pull():
        """Sau auto-crawl 19h: pull thêm batch tối + reindex RAG."""
        morning_pull()  # same logic: pull → pipeline → reindex

    # Sau khi daily report 23h chạy xong, dọn local để giải phóng volume.
    # Drive snapshot vẫn còn, nên lần sau pull về là có lại.
    def nightly_local_prune():
        """Cuối ngày: xoá local JSON+parquet cũ + reset chroma index."""
        try:
            from src.storage import get_drive_puller
            puller = get_drive_puller()
            result = puller.prune_local()
            telegram.buffer(
                f"🧹 Prune local — {result['deleted_files']} files, "
                f"{result['bytes_freed_mb']} MB freed",
                "OK",
                detail=("chroma cleared" if result.get("chroma_cleared")
                        else "chroma kept"),
            )
        except Exception as e:
            logger.error("nightly_local_prune: %s", e)
            telegram.send(
                f"⚠️ Prune local lỗi: <code>{str(e)[:150]}</code>"
            )

    # 07:30 — sau job 07:00 (buffer 30s cho crawler flush xong lên Drive).
    schedule.every().day.at("07:30").do(morning_pull)
    # 19:30 — sau job 19:00.
    schedule.every().day.at("19:30").do(evening_pull)
    # 23:15 — sau daily_report 23:00, trước nightly_backup 23:30.
    schedule.every().day.at("23:15").do(nightly_local_prune)

    def daily_cleanup():
        """Sweep old data every night so the volume doesn't grow forever.

        The crawler is append-only by default — without a TTL the volume
        fills with hundreds of MBs of articles nobody will ever query
        again. We keep 7 days: enough buffer for natural drops and
        still small enough that the Railway free tier never trips.
        """
        try:
            from scripts.cleanup import cleanup_old_data, format_cleanup_summary
            result = cleanup_old_data(max_age_days=7)
            total = result["total_deleted"]
            mb_freed = result["total_bytes"] / 1024 / 1024
            if total > 0:
                telegram.buffer(
                    f"🗑️ Cleanup — {total} files ({mb_freed:.2f} MB)",
                    "OK",
                    detail=", ".join(
                            f"{l}={s['deleted']}" for l, s in result["layers"].items() if s["deleted"]
                        ),
                    )
            else:
                telegram.buffer("🗑️ Cleanup — nothing to delete", "INFO")
        except Exception as e:
            logger.error("Daily cleanup failed: %s", e)
            telegram.send(f"⚠️ Cleanup lỗi: <code>{str(e)[:200]}</code>")

    # Run cleanup at 04:00 — well before the morning crawl so the
    # 7-day window doesn't include data the bot is about to index.
    schedule.every().day.at("04:00").do(daily_cleanup)

    def daily_report():
        stats = crawler.get_data_stats()
        total = stats["raw"] + stats["silver"] + stats["gold"]
        telegram.buffer(
            f"📊 Daily report — {total} files total",
            "INFO",
            detail=f"raw={stats['raw']}, silver={stats['silver']}, gold={stats['gold']}",
        )

    def nightly_backup():
        try:
            from src.backup import run_backup
            result = run_backup(upload_to_drive=True, keep_local=7)
            if result.get("ok"):
                telegram.buffer(
                    f"💾 Backup OK — {Path(result['archive']).name} ({result['size_mb']} MB)",
                    "OK",
                    detail="→ Drive" if "drive_file_id" in result else "local-only",
                )
        except Exception as e:
            # Errors are still immediate.
            telegram.send(f"⚠️ Backup lỗi: {str(e)[:150]}")

    schedule.every().day.at("23:00").do(daily_report)
    schedule.every().day.at("23:30").do(nightly_backup)

    def six_hourly_rag_snapshot():
        """Push RAG index snapshot to Drive every 6 hours.

        Why 6h and not nightly: if the volume dies during the day, the
        user can still answer /ask by restoring from the most recent
        snapshot, which is at most 6 hours stale.

        Success is silent (buffer only); failures are immediate.
        """
        try:
            from src.rag.persistent_store import get_persistent_store
            store = get_persistent_store()
            file_id = store.snapshot_to_drive()
            if file_id:
                telegram.buffer("📦 RAG snapshot → Drive OK", "OK")
        except Exception as e:
            logger.error("6h RAG snapshot error: %s", e)
            telegram.send(f"⚠️ RAG snapshot lỗi: <code>{str(e)[:150]}</code>")

    def daily_digest():
        """Send the buffered digest at 20:00 — one summary message
        covering everything that happened today. Anything not flushed
        here would sit in the buffer until the next 20:00, so we also
        flush on demand via /digest."""
        sent = telegram.flush_digest()
        if not sent:
            logger.info("Daily digest: nothing buffered today.")

    # RAG snapshots continue every 6h — they don't ping the user.
    schedule.every(6).hours.do(six_hourly_rag_snapshot)
    # Daily digest at 20:00 covers every buffered event in one message.
    schedule.every().day.at("20:00").do(daily_digest)

    # Removed: hourly_log_upload (was spamming /logs uploads every
    # 60 min). /logs is still available as an on-demand command.

    logger.info("Scheduler started!")
    while True:
        schedule.run_pending()
        time.sleep(60)

# ============== HEALTH SERVER ==============
def start_health_server():
    from flask import Flask, jsonify
    import threading
    app = Flask(__name__)
    @app.route('/health')
    def health():
        return jsonify({"status": "ok", "time": datetime.now().isoformat()})
    @app.route('/')
    def index():
        return jsonify({"service": "Data Platform Crawler", "status": "running"})
    def run():
        app.run(host='0.0.0.0', port=8080)
    threading.Thread(target=run, daemon=True).start()

# ============== MAIN ==============
def ensure_data_dirs():
    """Ensure all data subdirectories exist (volume mount point)."""
    base = Path(os.environ.get("DATA_DIR", "/app/data"))
    for sub in ["raw", "silver", "gold", "logs", "summary", "parquet", "chroma", "backups"]:
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base


def acquire_singleton_lock(pidfile: Path) -> bool:
    """Acquire an exclusive PID lock to prevent two pollers running at once."""
    import fcntl
    # Stale-lock recovery: if the previous holder's PID is no longer
    # alive, the fcntl lock is gone but the file still references the
    # dead PID. Remove it so we can re-acquire. This handles the case
    # where Railway's old container died hard (SIGKILL) without
    # releasing the lock cleanly.
    if pidfile.exists():
        try:
            old_pid = int(pidfile.read_text().strip() or "0")
        except ValueError:
            old_pid = 0
        if old_pid and old_pid != os.getpid():
            try:
                os.kill(old_pid, 0)  # signal 0 = check existence only
            except (OSError, ProcessLookupError):
                logger.warning(
                    "Stale .bot.lock (pid=%s) — old process is dead, removing.",
                    old_pid,
                )
                try:
                    pidfile.unlink()
                except OSError as e:
                    logger.warning("Could not remove stale lock: %s", e)
    fp = open(pidfile, "w")
    try:
        fcntl.lockf(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fp.write(str(os.getpid()))
        fp.flush()
        return True
    except (IOError, OSError):
        existing_pid = "?"
        try:
            existing_pid = pidfile.read_text().strip() or "?"
        except OSError:
            pass
        logger.error(
            "Another bot instance holds the singleton lock (pid=%s). "
            "Likely two containers polling the same Telegram token.",
            existing_pid,
        )
        return False


def main():
    logger.info("=" * 50)
    logger.info("Data Platform Service - Starting...")
    # Build identifier so we can confirm the latest code is actually
    # running, not a stale container that survived a deploy.
    # Bump this string every time we deploy; if /status still shows
    # the old value, Railway is still serving the previous image.
    logger.info("BUILD_TAG: import-fix-v2")
    logger.info("=" * 50)
    data_root = ensure_data_dirs()
    logger.info(f"Data root: {data_root}")
    # Volume diagnostic: check whether /app/data is writable and persistent
    probe = data_root / ".startup_probe"
    probe.write_text(datetime.now().isoformat())
    logger.info(f"Volume write probe OK: {probe.read_text()}")
    start_health_server()
    telegram = TelegramService()
    crawler = CrawlerService(telegram)
    bot = BotCommands(crawler, telegram)

    # Auto-build RAG index on every boot so /ask works immediately.
    # This replaces the previous silent failure where the user saw
    # "RAG chưa khả dụng" because the store was empty and the
    # model had never been downloaded.
    def _auto_index():
        logger.info("RAG auto-index: starting background index on boot...")
        telegram.send("🔄 <b>Bot đang khởi động...</b>\n⏳ Đang build RAG index lần đầu (tải model, có thể mất 2-5 phút).")
        try:
            result = bot.cmd_index()
            logger.info("RAG auto-index: done — %s", result)
            telegram.send(f"✅ <b>RAG index ready!</b>\n{result}")
        except Exception as e:
            logger.error("RAG auto-index failed: %s", e)
            telegram.send(f"⚠️ <b>RAG index failed:</b>\n<code>{str(e)[:200]}</code>\n\nGửi <code>/index</code> thủ công để thử lại.")

    threading.Thread(target=_auto_index, daemon=True).start()
    threading.Thread(target=run_scheduler, args=(telegram, crawler), daemon=True).start()
    logger.info("All services started!")
    bot.poll()

if __name__ == "__main__":
    main()
