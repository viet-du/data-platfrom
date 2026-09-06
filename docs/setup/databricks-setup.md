# Databricks Setup Guide

## Overview

Hướng dẫn setup Databricks Community Edition (miễn phí vĩnh viễn) cho Data Platform.

## Step 1: Create Databricks Account

### 1.1 Đăng ký Databricks Community Edition

1. Truy cập: [https://community.cloud.databricks.com/](https://community.cloud.databricks.com/)
2. Click "Get Started"
3. Điền thông tin:
   - Email: your-email@gmail.com
   - Password: your-password
   - Full name: Your Name
4. Verify email

### 1.2 Create Workspace

1. Sau khi login, click "Create Workspace"
2. Workspace Name: `data-platform`
3. Region: Chọn region gần nhất (Singapore)
4. Click "Create Workspace"

## Step 2: Get Databricks Configuration

### 2.1 Get Workspace URL

```
https://dbc-xxxxx.cloud.databricks.com
```

Lưu lại phần `dbc-xxxxx.cloud.databricks.com` (không có https://)

### 2.2 Generate Personal Access Token

1. Click icon User (góc phải trên)
2. Chọn "User Settings"
3. Tab "Access tokens"
4. Click "Generate new token"
5. Token name: `data-platform-local`
6. Lifetime: 90 days (hoặc unlimited)
7. Click "Generate"
8. **Copy và lưu token ngay** (sẽ không hiện lại)

```
<YOUR-DATABRICKS-TOKEN>
```

### 2.3 Create SQL Warehouse

1. Menu sidebar → "SQL Warehouses"
2. Click "Create SQL Warehouse"
3. Configure:
   - Name: `data-platform-warehouse`
   - Size: 2X-Small (free tier)
   - Auto-stop: 10 minutes
   - Type: Serverless (nếu có) hoặc Pro
4. Click "Create"
5. Copy HTTP Path từ warehouse details

```
SQL warehouse → warehouse name → Connection details → HTTP Path
/sql/1.0/warehouses/your-warehouse-id
```

## Step 3: Configure Local Environment

### 3.1 Install Databricks CLI

```bash
pip install databricks-cli
```

### 3.2 Configure Databricks CLI

```bash
databricks configure --token
```

Nhập:
- Databricks Host: `https://dbc-xxxxx.cloud.databricks.com`
- Token: `dapi0123456789abcdef...`

### 3.3 Verify Connection

```bash
databricks workspace list
databricks clusters list
```

## Step 4: Configure Environment Variables

```bash
# Thêm vào .env
cat >> .env << 'EOF'

# Databricks (Community Edition)
DATABRICKS_HOST=https://dbc-xxxxx.cloud.databricks.com
DATABRICKS_TOKEN=<YOUR-DATABRICKS-TOKEN>
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_CLOUD=aws
EOF
```

## Step 5: Create Delta Lake Structure

### 5.1 Create Notebooks Folder

```bash
databricks workspace mkdirs /Repos/data-platform
databricks workspace mkdirs /Repos/data-platform/ingestion
databricks workspace mkdirs /Repos/data-platform/transformation
databricks workspace mkdirs /Repos/data-platform/analytics
```

### 5.2 Create Unity Catalog (nếu có quyền)

```python
# Chạy trong Databricks Notebook
%sql

-- Create catalog
CREATE CATALOG IF NOT EXISTS data_platform;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS data_platform.raw;
CREATE SCHEMA IF NOT EXISTS data_platform.bronze;
CREATE SCHEMA IF NOT EXISTS data_platform.silver;
CREATE SCHEMA IF NOT EXISTS data_platform.gold;
CREATE SCHEMA IF NOT EXISTS data_platform.staging;
```

## Step 6: Install Databricks Connect (Optional)

Cho phép chạy code local và execute trên Databricks:

```bash
pip install databricks-connect
```

```python
# test_connection.py
from databricks import sql

connection = sql.connect(
    host="https://dbc-xxxxx.cloud.databricks.com",
    token="dapi0123456789abcdef...",
    http_path="/sql/1.0/warehouses/your-warehouse-id"
)

with connection.cursor() as cursor:
    cursor.execute("SELECT 1 as test")
    result = cursor.fetchall()
    print(result)
```

## Step 7: Test Databricks Connection

### 7.1 Test với Python SDK

```python
# test_databricks.py
from databricks.sdk import WorkspaceClient
import os

wks = WorkspaceClient()

# List workspaces
for ws in wks.workspaces.list():
    print(ws.path)

# List clusters
for cluster in wks.clusters.list():
    print(f"{cluster.cluster_name}: {cluster.cluster_id}")
```

### 7.2 Test với SQL

```python
# test_sql.py
from databricks import sql
import os

connection = sql.connect(
    host=os.environ['DATABRICKS_HOST'],
    token=os.environ['DATABRICKS_TOKEN'],
    http_path=os.environ['DATABRICKS_HTTP_PATH']
)

with connection.cursor() as cursor:
    # Test query
    cursor.execute("SELECT current_timestamp as now")
    print(cursor.fetchall())
    
    # Create test table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_platform.gold.test_table (
            id INT,
            name STRING
        )
    """)
    
    # Insert data
    cursor.execute("INSERT INTO data_platform.gold.test_table VALUES (1, 'test')")
    
    # Query
    cursor.execute("SELECT * FROM data_platform.gold.test_table")
    for row in cursor.fetchall():
        print(row)
```

## Step 8: Create Databricks Jobs (Optional)

Tạo jobs để schedule pipeline:

1. Databricks UI → Workflows → Jobs
2. Click "Create job"
3. Configure:
   - Task name: `daily-ingestion`
   - Type: Notebook
   - Source: Workspace
   - Path: `/Repos/data-platform/ingestion/daily_ingestion`
4. Schedule: Daily at 2:00 AM
5. Click "Create"

## Troubleshooting

### Lỗi "Invalid token format"

```bash
# Kiểm tra token
echo $DATABRICKS_TOKEN

# Token phải bắt đầu bằng dapi
# Ví dụ: dapi0123456789abcdef...
```

### Lỗi "Cluster not found"

```bash
# List available clusters
databricks clusters list

# Kiểm tra HTTP path
# HTTP path phải match với cluster đang running
```

### Lỗi "Request timeout"

```python
# Tăng timeout
from databricks import sql

connection = sql.connect(
    host=host,
    token=token,
    http_path=http_path,
    timeout=60  # 60 seconds
)
```

### Community Edition Limits

| Resource | Limit | Workaround |
|----------|-------|------------|
| Clusters | 1 at a time | Stop current cluster before starting new |
| Runtime | 14 days max | Auto-stop after 2h inactivity |
| Storage | 20GB | Delete old data, compress |
| Workers | 4 cores | Optimize queries |

## Security Best Practices

### 1. Rotate Token Regularly

```bash
# Tạo token mới mỗi 90 ngày
# Xóa token cũ sau khi tạo token mới
```

### 2. Không commit credentials

```bash
# Thêm vào .gitignore
.env
*.env
configs/*.json
```

### 3. Use Secret Scope (nếu có)

```bash
# Tạo secret scope
databricks secrets create-scope --scope data-platform

# Store secret
databricks secrets put --scope data-platform --key databricks-token
```

## Next Steps

1. ✅ Setup Databricks → Xong
2. [Google Drive Setup](./google-drive-setup.md)
3. [Setup dbt-databricks](../tools/dbt-quickstart.md)
4. [Setup Metabase Dashboard](../dashboards/metabase-setup.md)
