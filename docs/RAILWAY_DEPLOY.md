# Railway Deploy - Hướng dẫn chi tiết

## Tổng quan
Chạy 24/7 trên Railway, điều khiển qua Telegram.

## Deploy qua GitHub

### 1. Push lên GitHub
```bash
git add .
git commit -m "Add Railway deployment"
git push origin main
```

### 2. Kết nối Railway
1. Mở [railway.app](https://railway.app)
2. New Project → Deploy from GitHub
3. Chọn repo

### 3. Set Environment Variables
```
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
```

## Telegram Commands
| Lệnh | Mô tả |
|------|--------|
| /start | Bắt đầu |
| /crawl | Chạy crawl ngay |
| /raw | Crawl Google Drive |
| /status | Trạng thái |
| /report | Báo cáo |
| /dashboard | Thống kê |

## Auto Schedule
- 06:00, 12:00, 18:00, 22:00 - Auto crawl
- 23:00 - Daily report
