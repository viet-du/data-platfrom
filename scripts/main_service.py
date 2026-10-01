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
        self.data_path = Path('/app/data')
    
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

<b>Commands:</b>
/crawl - Chạy crawl ngay
/raw - Crawl Google Drive
/status - Trạng thái hệ thống
/report - Báo cáo hôm nay
/dashboard - Thống kê chi tiết
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
    
    def cmd_restart(self) -> str:
        self.telegram.send("🔄 <b>Đang khởi động lại...</b>")
        time.sleep(2)
        self.telegram.send("✅ <b>Bot đã restart!</b>")
        time.sleep(1)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    
    def poll(self):
        import requests
        if not self.telegram.enabled or not self.telegram.token:
            logger.error("Telegram polling cannot start: bot is disabled or TELEGRAM_BOT_TOKEN is missing.")
            return
        api_url = f"{self.telegram.api_url}/getUpdates"
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
                    text = msg['text'].strip().lower()
                    if not text:
                        continue
                    command = text.split(maxsplit=1)[0].split("@", 1)[0]
                    logger.info(f"Command: {text}")
                    response = None
                    if command in ['/start', '/help']:
                        response = self.cmd_start()
                    elif command == '/status':
                        response = self.cmd_status()
                    elif command == '/crawl':
                        response = self.cmd_crawl()
                    elif command == '/raw':
                        response = self.cmd_raw()
                    elif command == '/report':
                        response = self.cmd_report()
                    elif command == '/dashboard':
                        response = self.cmd_dashboard()
                    elif command == '/restart':
                        response = self.cmd_restart()
                    if response:
                        self.telegram.send(response)
            except requests.exceptions.ReadTimeout:
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
    
    schedule.every().day.at("23:00").do(daily_report)
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
def main():
    logger.info("=" * 50)
    logger.info("Data Platform Service - Starting...")
    logger.info("=" * 50)
    start_health_server()
    telegram = TelegramService()
    crawler = CrawlerService(telegram)
    bot = BotCommands(crawler, telegram)
    threading.Thread(target=run_scheduler, args=(telegram, crawler), daemon=True).start()
    logger.info("All services started!")
    bot.poll()

if __name__ == "__main__":
    main()
