# Railway Volume Setup

Data của bot cần **persist qua các lần redeploy**. Railway Volume là ổ đĩa persistent.

## Setup trên Railway Dashboard

1. Vào https://railway.app/dashboard
2. Mở project **data-platfrom**
3. Click **"+ New"** → **"Volume"**
4. Configure:
   - **Name**: `data-volume`
   - **Mount Path**: `/app/data`
   - **Size**: `2 GB` (~$0.50/tháng)
5. Click **"Add"**

## Verification

Sau khi tạo:
- Volume sẽ auto-mount vào `/app/data` của container
- Container khởi động → `ensure_data_dirs()` tạo subdirs nếu thiếu
- Data persist ngay cả khi redeploy/restart

## Backup thêm lên Google Drive

Ngoài Volume, code đã có sẵn:
- **Auto backup** lúc **23:30** hàng ngày
- Upload file `.tar.gz` lên folder `data-backups` trong Drive của bạn
- Manual trigger: gửi `/backup` cho bot

## Telegram Commands

| Command | Chức năng |
|---------|-----------|
| `/backup` | Backup thủ công → Drive |
| `/status` | Xem storage stats |
| `/dashboard` | Storage size breakdown |

## Disaster Recovery

Nếu mất data (volume corrupted):

1. **Từ Drive backup**: download `.tar.gz` từ folder `data-backups`
2. **Extract local**:
   ```bash
   tar -xzf backup_20261001.tar.gz
   ```
3. **Restore**: copy `parquet/` + `chroma/` vào `/app/data/`
4. **Restart bot**

## Cost

| Item | Cost |
|------|------|
| Volume 2GB | ~$0.50/tháng |
| Bandwidth | Free in/out |
| Drive storage | Free (15GB) |
| **Total backup** | **~$0.50/tháng** |