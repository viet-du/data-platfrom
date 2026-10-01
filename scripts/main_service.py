#!/usr/bin/env python3
"""
Main Service - Railway Deployment
- Telegram Bot + Crawler Scheduler + Auto Reporter
"""
import os, sys, time, logging, threading, schedule
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

# ============== CRAWLER SERVICE ==============
class CrawlerService:
    def __init__(self, telegram: TelegramService):
        self.telegram = telegram
        self.is_running = False
        self.last_run = None
        self.last_result = None
        self.data_path = Path(os.environ.get("DATA_DIR", "/app/data"))
    
    def run_crawl_news(self) -> dict:
        logger.info("Starting news crawl...")
        start = time.time()
        try:
            sys.path.insert(0, '/app')
            from src.crawlers import VNExpressCrawler, DanTriCrawler, TuoiTreCrawler, VietnamNetCrawler
            articles = []
            for name, cls in [
                ('Vnexpress', VNExpressCrawler),
                ('Dantri', DanTriCrawler),
                ('Tuoitre', TuoiTreCrawler),
                ('Vietnamnet', VietnamNetCrawler)
            ]:
                try:
                    instance = cls()
                    results = instance.crawl_all(today_only=True)
                    articles.extend(results)
                    logger.info(f"{name}: {len(results)} articles")
                except Exception as e:
                    logger.error(f"{name} error: {e}")
            elapsed = time.time() - start
            self.last_run = datetime.now()
            self.last_result = {'success': True, 'articles': len(articles), 'time': elapsed}
            return self.last_result
        except Exception as e:
            logger.error(f"Crawl error: {e}")
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
    
    def cmd_start(self) -> str:
        return """🤖 <b>Data Platform Bot - Online!</b>

✅ Hệ thống đang chạy tự động
⏰ Auto-crawl: 6h, 12h, 18h, 22h
📊 Daily report: 23h

<b>📥 Data Commands:</b>
/crawl - Chạy crawl ngay
/raw - Crawl Google Drive
/status - Trạng thái hệ thống
/drives - Thống kê file trên Drive
/report - Báo cáo hôm nay
/dashboard - Thống kê chi tiết

<b>🔮 RAG Chatbot (Q&A về tin tức):</b>
/index - Build vector index từ data
/ragstats - Thống kê vector store
/ask &lt;câu hỏi&gt; - Hỏi AI về tin tức

<b>💾 Backup & Storage:</b>
/backup - Backup data → Drive

<b>⚙️ System:</b>
/restart - Khởi động lại bot"""
    
    def cmd_status(self) -> str:
        data = self.crawler.get_data_stats()
        last = self.crawler.last_run.strftime('%H:%M:%S') if self.crawler.last_run else "Chưa chạy"
        return f"""📊 <b>System Status</b>

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔄 Last crawl: {last}

📁 <b>Data Stats:</b>
• Raw files: {data['raw']}
• Silver files: {data['silver']}
• Gold files: {data['gold']}

🔄 <b>Auto Schedule:</b>
• 06:00 - Morning crawl
• 12:00 - Noon crawl  
• 18:00 - Evening crawl
• 22:00 - Night crawl
• 23:00 - Daily report"""
    
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
        if self._rag_chain is not None:
            return self._rag_chain
        try:
            from src.rag import RAGChain, VectorStore, GeminiClient
            store = VectorStore()
            chain = RAGChain(store, GeminiClient())
            self._rag_chain = chain
            return chain
        except Exception as e:
            logger.error(f"Failed to init RAG chain: {e}")
            return None

    def cmd_ask(self, question: str) -> str:
        """RAG: answer a question using crawled articles."""
        chain = self._get_rag()
        if chain is None:
            return "❌ RAG chưa khả dụng. Kiểm tra dependencies (chromadb, sentence-transformers)."

        if chain.store.count == 0:
            return (
                "⚠️ Vector store trống.\n"
                "Chạy /index trước để build embeddings từ dữ liệu đã crawl."
            )

        result = chain.ask(question, top_k=3)  # 3 chunks fits comfortably in 512 MB
        return (
            f"🤖 <b>RAG Answer</b>\n\n"
            f"{result['answer']}\n\n"
            f"<b>📚 Sources:</b>\n{result['sources']}"
        )

    def cmd_index(self) -> str:
        """Build / rebuild the vector index from parquet."""
        chain = self._get_rag()
        if chain is None:
            return "❌ RAG chưa khả dụng."

        self.telegram.send("📥 <b>Đang build vector index...</b>\nCó thể mất 1-2 phút lần đầu (tải model).")
        try:
            from src.rag import build_store_from_parquet
            # Reset and rebuild
            chain.store.reset()
            store, stats = build_store_from_parquet()
            self._rag_chain = None  # re-init
            chain = self._get_rag()
            return (
                f"✅ <b>Index hoàn thành!</b>\n\n"
                f"📊 Indexed: {stats.get('added', 0)} bài\n"
                f"⏭️ Skipped (đã có): {stats.get('skipped', 0)}\n"
                f"🗑️ Dedup removed: {stats.get('duplicates_removed', 0)}\n"
                f"💾 Total in store: {chain.store.count if chain else '?'}"
            )
        except Exception as e:
            logger.error(f"Index error: {e}")
            return f"❌ Lỗi index: {str(e)[:200]}"

    def cmd_ragstats(self) -> str:
        """Show RAG vector store stats."""
        chain = self._get_rag()
        if chain is None:
            return "❌ RAG chưa khả dụng."
        gemini_status = "✅ Ready" if chain.gemini.is_available() else "⚠️ Chưa có API key (extractive mode)"
        return (
            f"🔮 <b>RAG Stats</b>\n\n"
            f"📦 Articles indexed: <b>{chain.store.count}</b>\n"
            f"🤖 Gemini: {gemini_status}\n"
            f"📐 Embedding: all-MiniLM-L6-v2 (lightweight, ~80 MB RAM)"
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
                elif command == '/backup':
                    response = self.cmd_backup()
                elif command == '/ask':
                    question = text[len(command):].strip() if text_lower.startswith(command) else ""
                    if not question:
                        response = "💡 <b>Cách dùng:</b>\n<code>/ask Có tin gì về Hà Nội?</code>"
                    else:
                        response = self.cmd_ask(question)
                elif command == '/restart':
                    response = self.cmd_restart()
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
        telegram.send(f"{emoji} <b>Auto Crawl - {hour}</b>")
        result = crawler.run_crawl_news()
        if result['success']:
            telegram.send(f"✅ Hoàn thành! 📰 {result['articles']} bài")
    
    schedule.every().day.at("06:00").do(job, "6h Sáng", "🌅", "Morning")
    schedule.every().day.at("12:00").do(job, "12h Trưa", "☀️", "Noon")
    schedule.every().day.at("18:00").do(job, "18h Chiều", "🌆", "Evening")
    schedule.every().day.at("22:00").do(job, "22h Tối", "🌙", "Night")
    
    def daily_report():
        stats = crawler.get_data_stats()
        telegram.send(f"📊 <b>Daily Report - {datetime.now().strftime('%Y-%m-%d')}</b>\n\n📁 Total files: {stats['raw'] + stats['silver'] + stats['gold']}")

    def nightly_backup():
        try:
            from src.backup import run_backup
            result = run_backup(upload_to_drive=True, keep_local=7)
            if result.get("ok"):
                telegram.send(
                    f"💾 <b>Nightly backup OK</b>\n"
                    f"📦 {Path(result['archive']).name} ({result['size_mb']} MB)"
                )
        except Exception as e:
            telegram.send(f"⚠️ Backup lỗi: {str(e)[:150]}")

    schedule.every().day.at("23:00").do(daily_report)
    schedule.every().day.at("23:30").do(nightly_backup)
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
    threading.Thread(target=run_scheduler, args=(telegram, crawler), daemon=True).start()
    logger.info("All services started!")
    bot.poll()

if __name__ == "__main__":
    main()
