# Google Drive Setup Guide

## Overview

Hướng dẫn setup Google Drive API để đọc/ghi files (CSV, Excel) từ Data Platform.

## Step 1: Create Google Cloud Project

### 1.1 Create Project

1. Truy cập: [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Configure:
   - Project name: `data-platform`
   - Organization: Your organization (hoặc "No organization")
   - Location: Your organization
4. Click "Create"

### 1.2 Enable Google Drive API

1. Trong project, đi đến "APIs & Services" → "Library"
2. Search "Google Drive API"
3. Click "Google Drive API"
4. Click "Enable"

### 1.3 Enable Google Sheets API

1. Search "Google Sheets API"
2. Click "Google Sheets API"
3. Click "Enable"

## Step 2: Create Service Account

### 2.1 Create Service Account

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Configure:
   - Service account name: `data-platform-uploader`
   - Service account ID: `data-platform-uploader@your-project.iam.gserviceaccount.com`
   - Description: `Service account for data platform to access Google Drive`
4. Click "Create and continue"
5. Skip optional steps, click "Done"

### 2.2 Generate Service Account Key

1. Click vào service account vừa tạo
2. Tab "Keys"
3. Click "Add Key" → "Create new key"
4. Select: JSON
5. Click "Create"
6. **File sẽ download tự động** → Lưu vào `./configs/google-drive-credentials.json`

### 2.3 Key Structure

```json
{
  "type": "service_account",
  "project_id": "data-platform-123456",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "data-platform-uploader@data-platform-123456.iam.gserviceaccount.com",
  "client_id": "123456789012345678901",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  ...
}
```

## Step 3: Share Google Drive Folder

### 3.1 Create Shared Drive

1. Truy cập [Google Drive](https://drive.google.com)
2. Click "+ New" → "Shared drive"
3. Name: `data-platform`
4. Click "Create"

### 3.2 Create Folder Structure

Trong Shared Drive, tạo:

```
data-platform/
├── raw/
│   ├── sources/
│   │   ├── sales/
│   │   ├── customers/
│   │   └── products/
│   ├── api_responses/
│   └── manual_uploads/
├── staging/
└── processed/
```

### 3.3 Share Folder với Service Account

1. Right-click folder `data-platform` → "Share"
2. Add email: `data-platform-uploader@data-platform-123456.iam.gserviceaccount.com`
3. Role: "Editor"
4. Click "Send" (hoặc "Share")

### 3.4 Get Folder ID

1. Open folder `data-platform`
2. Copy folder ID từ URL:

```
https://drive.google.com/drive/folders/1ABCDEFGHIJKLMNOPQRSTUVWXYZ
                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                        Đây là Folder ID
```

Lưu lại:
- Main Folder ID: `1ABCDEFGHIJKLMNOPQRSTUVWXYZ`
- Raw Folder ID: `1ABCDEFGHIJKLMNOPQRSTUVWXYZ` (thay thế nếu khác)

## Step 4: Install Google Client Library

```bash
pip install google-api-python-client google-auth
```

## Step 5: Configure Environment Variables

```bash
# Thêm vào .env
cat >> .env << 'EOF'

# Google Drive
GOOGLE_DRIVE_CREDENTIALS_PATH=./configs/google-drive-credentials.json
GOOGLE_DRIVE_FOLDER_ID=1ABCDEFGHIJKLMNOPQRSTUVWXYZ
GOOGLE_DRIVE_RAW_FOLDER_ID=1ABCDEFGHIJKLMNOPQRSTUVWXYZ
EOF
```

## Step 6: Test Google Drive Connection

### 6.1 Test Authentication

```python
# test_gdrive_auth.py
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

creds = service_account.Credentials.from_service_account_file(
    './configs/google-drive-credentials.json',
    scopes=SCOPES
)

service = build('drive', 'v3', credentials=creds)

# Test: List files
results = service.files().list(
    pageSize=10,
    fields="files(id, name, mimeType)"
).execute()

files = results.get('files', [])
print(f"Found {len(files)} files:")
for f in files:
    print(f"  - {f['name']} ({f['mimeType']})")
```

### 6.2 Test List Files in Folder

```python
# test_list_files.py
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')

creds = service_account.Credentials.from_service_account_file(
    os.environ.get('GOOGLE_DRIVE_CREDENTIALS_PATH'),
    scopes=SCOPES
)

service = build('drive', 'v3', credentials=creds)

# List all files in folder
query = f"'{FOLDER_ID}' in parents and trashed=false"
results = service.files().list(
    q=query,
    pageSize=100,
    fields="files(id, name, mimeType, createdTime, modifiedTime)"
).execute()

files = results.get('files', [])
print(f"Found {len(files)} files in folder:")
for f in files:
    print(f"  - {f['name']} | {f['mimeType']} | Modified: {f['modifiedTime']}")
```

## Step 7: Create Python Utility Module

### 7.1 Create google_drive_utils.py

```python
# src/utils/google_drive_utils.py
"""
Google Drive Utilities for Data Platform
"""
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from googleapiclient.errors import HttpError
import io

# Logger
logger = logging.getLogger(__name__)

# Constants
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SCOPES_WRITE = ['https://www.googleapis.com/auth/drive']


class GoogleDriveClient:
    """Google Drive API Client"""
    
    def __init__(self, credentials_path: str, folder_id: str):
        """
        Initialize Google Drive client
        
        Args:
            credentials_path: Path to service account JSON file
            folder_id: Google Drive folder ID
        """
        self.folder_id = folder_id
        self.creds = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=SCOPES
        )
        self.service = build('drive', 'v3', credentials=self.creds)
        logger.info(f"GoogleDriveClient initialized for folder: {folder_id}")
    
    def list_files(
        self, 
        folder_id: Optional[str] = None,
        file_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        List files in folder
        
        Args:
            folder_id: Override folder ID (optional)
            file_type: Filter by mime type (e.g., 'text/csv', 'application/vnd.ms-excel')
            limit: Max number of files to return
            
        Returns:
            List of file metadata dicts
        """
        parent_id = folder_id or self.folder_id
        query = f"'{parent_id}' in parents and trashed=false"
        
        if file_type:
            if file_type == 'csv':
                query += " and mimeType='text/csv'"
            elif file_type == 'excel':
                query += " and (mimeType='application/vnd.ms-excel' or mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')"
        
        try:
            results = self.service.files().list(
                q=query,
                pageSize=limit,
                fields="files(id, name, mimeType, createdTime, modifiedTime, size)"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Listed {len(files)} files from folder {parent_id}")
            return files
            
        except HttpError as e:
            logger.error(f"Error listing files: {e}")
            raise
    
    def download_file(self, file_id: str, destination: str) -> str:
        """
        Download file from Google Drive
        
        Args:
            file_id: Google Drive file ID
            destination: Local destination path
            
        Returns:
            Destination path
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.FileIO(destination, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                logger.info(f"Download {int(status.progress() * 100)}%")
            
            logger.info(f"Downloaded file to: {destination}")
            return destination
            
        except HttpError as e:
            logger.error(f"Error downloading file: {e}")
            raise
    
    def upload_file(
        self, 
        local_path: str, 
        folder_id: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Dict:
        """
        Upload file to Google Drive
        
        Args:
            local_path: Local file path
            folder_id: Target folder ID (optional)
            filename: Override filename (optional)
            
        Returns:
            Created file metadata
        """
        folder = folder_id or self.folder_id
        name = filename or os.path.basename(local_path)
        
        try:
            file_metadata = {
                'name': name,
                'parents': [folder]
            }
            
            media = MediaFileUpload(local_path)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, mimeType, createdTime, webViewLink'
            ).execute()
            
            logger.info(f"Uploaded file: {file.get('name')} (ID: {file.get('id')})")
            return file
            
        except HttpError as e:
            logger.error(f"Error uploading file: {e}")
            raise
    
    def get_latest_file(self, name_pattern: str, folder_id: Optional[str] = None) -> Optional[Dict]:
        """
        Get latest file matching name pattern
        
        Args:
            name_pattern: Filename pattern (supports *)
            folder_id: Override folder ID
            
        Returns:
            Latest file metadata or None
        """
        files = self.list_files(folder_id)
        
        # Filter by name pattern
        import fnmatch
        matching = [f for f in files if fnmatch.fnmatch(f['name'], name_pattern)]
        
        if not matching:
            logger.warning(f"No files matching pattern: {name_pattern}")
            return None
        
        # Sort by modified time
        matching.sort(key=lambda x: x.get('modifiedTime', ''), reverse=True)
        
        return matching[0]
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete file from Google Drive
        
        Args:
            file_id: File ID to delete
            
        Returns:
            True if successful
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted file: {file_id}")
            return True
        except HttpError as e:
            logger.error(f"Error deleting file: {e}")
            raise
```

### 7.2 Create __init__.py

```python
# src/utils/__init__.py
from .google_drive_utils import GoogleDriveClient

__all__ = ['GoogleDriveClient']
```

## Step 8: Example Usage

```python
# example_usage.py
import os
from src.utils import GoogleDriveClient

# Initialize client
client = GoogleDriveClient(
    credentials_path='./configs/google-drive-credentials.json',
    folder_id='1ABCDEFGHIJKLMNOPQRSTUVWXYZ'
)

# List all CSV files
files = client.list_files(file_type='csv')
print(files)

# Download latest file
latest = client.get_latest_file('sales_*.csv')
if latest:
    client.download_file(latest['id'], './data/raw/sales_latest.csv')

# Upload processed file
client.upload_file(
    local_path='./data/analytics/report.csv',
    filename='report_2024-01-15.csv'
)
```

## Troubleshooting

### Lỗi "insufficient permissions"

```python
# Nguyên nhân: Service account chưa được share folder
# Giải pháp: 
# 1. Mở Google Drive
# 2. Right-click folder → Share
# 3. Thêm email: data-platform-uploader@...
# 4. Role: Editor
```

### Lỗi "quota exceeded"

```python
# Giải pháp: 
# 1. Kiểm tra Google Cloud Console → IAM → Quotas
# 2. Request quota increase
# 3. Hoặc implement rate limiting trong code
```

### Lỗi "file not found"

```python
# Nguyên nhân: File đã bị xóa hoặc move
# Giải pháp:
# 1. Kiểm tra file trong Google Drive
# 2. Verify folder_id đúng
# 3. Check trashed=false trong query
```

## Rate Limits

| API | Limit | Notes |
|-----|-------|-------|
| List files | 1,000 requests/day | Per project |
| Download | 10 GB/day | Per project |
| Upload | 750 GB/day | Per project |

## Security Best Practices

### 1. Restrict API Scopes

```python
# Chỉ dùng read-only scope khi không cần upload
SCOPES_READONLY = ['https://www.googleapis.com/auth/drive.readonly']
```

### 2. Rotate Service Account Key

```bash
# Tạo key mới mỗi 6 tháng
# Xóa key cũ sau khi tạo key mới
```

### 3. Monitor API Usage

```python
# Check quota in Google Cloud Console
# APIs & Services → Quotas
```

## Next Steps

1. ✅ Setup Google Drive → Xong
2. [Setup Databricks](./databricks-setup.md)
3. [Setup dbt-databricks](../tools/dbt-quickstart.md)
4. [Setup Ingestion Pipeline](../pipelines/ingestion-guide.md)
