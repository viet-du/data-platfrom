# Troubleshooting Guide

## Overview

Hướng dẫn xử lý các lỗi thường gặp trong Data Platform.

## Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| Airflow not starting | `docker-compose restart` |
| Databricks connection | Check token expiration |
| Missing files | Check Google Drive sync |
| Slow dashboard | Clear Metabase cache |
| Pipeline failing | Check logs first |

---

## Issue 1: Airflow Problems

### Airflow Webserver Won't Start

**Symptoms:**
```
Error: Cannot start webserver
```

**Diagnosis:**
```bash
# Check Docker status
docker-compose ps

# Check logs
docker-compose logs airflow-webserver

# Check port
lsof -i :8080
```

**Solutions:**

```bash
# Solution 1: Restart
docker-compose down
docker-compose up -d

# Solution 2: Clear cache
docker exec airflow-webserver airflow db clean

# Solution 3: Reinitialize DB
docker exec airflow-webserver airflow initdb
```

### DAG Not Showing in UI

**Symptoms:**
- DAG not visible in Airflow UI

**Diagnosis:**
```bash
# Check DAG file syntax
python -m py_compile airflow/dags/my_dag.py

# Check DAG import
docker exec airflow-webserver python -c "from airflow import DAG"
```

**Solutions:**
```bash
# Solution 1: Refresh DAGs
docker exec airflow-webserver airflow dags reserialize

# Solution 2: Clear DAG processor
docker-compose restart

# Solution 3: Check DAG folder
ls -la airflow/dags/
```

### Task Stuck in Running State

**Symptoms:**
- Task never completes, stays "running"

**Diagnosis:**
```bash
# Check task logs
docker-compose logs airflow-worker --tail 100

# Check worker process
docker exec airflow-worker ps aux
```

**Solutions:**
```bash
# Clear task
docker exec airflow-webserver airflow tasks clear dag_id task_id -f -y

# Or kill via UI
# Airflow UI → DAG → Task → Clear
```

---

## Issue 2: Databricks Problems

### Connection Refused

**Symptoms:**
```
Error: Connection refused to https://dbc-xxx.cloud.databricks.com
```

**Diagnosis:**
```bash
# Check Databricks is accessible
curl -I https://dbc-xxx.cloud.databricks.com

# Verify credentials
echo $DATABRICKS_TOKEN
echo $DATABRICKS_HOST
```

**Solutions:**
```bash
# Solution 1: Test connection
databricks workspace list

# Solution 2: Regenerate token
# Go to Databricks → User Settings → Access Tokens → Generate new

# Solution 3: Update .env
vim .env
source .env
```

### Query Timeout

**Symptoms:**
```
Error: Query timeout after 60s
```

**Diagnosis:**
```sql
-- Check query performance in Databricks
EXPLAIN FORMATTED
SELECT ... FROM table
WHERE ...
```

**Solutions:**
```python
# Solution 1: Increase timeout
conn = sql.connect(
    host=host,
    token=token,
    http_path=http_path,
    timeout=300  # 5 minutes
)

# Solution 2: Optimize query
# Add partition filters
# Add indexes

# Solution 3: Reduce data volume
WHERE order_date >= '2024-01-01'  -- Limit date range
```

### Cluster Not Starting

**Symptoms:**
```
Error: No active cluster
```

**Diagnosis:**
```bash
# Check cluster status
databricks clusters list

# Check if cluster is stopped
```

**Solutions:**
```bash
# Start cluster via UI
# Databricks → Compute → Start cluster

# Or via API
databricks clusters start <cluster-id>
```

---

## Issue 3: Google Drive Issues

### Authentication Error

**Symptoms:**
```
Error: insufficientPermission
```

**Diagnosis:**
```bash
# Check service account email
cat configs/google-drive-credentials.json | jq .client_email

# Verify folder sharing
# Go to Google Drive → Right-click folder → Share
```

**Solutions:**
```bash
# Solution 1: Re-share folder
# Open Google Drive
# Right-click "data-platform" folder
# Share with: data-platform-uploader@project.iam.gserviceaccount.com
# Role: Editor

# Solution 2: Verify credentials
python -c "
from google.oauth2 import service_account
creds = service_account.Credentials.from_service_account_file(
    'configs/google-drive-credentials.json',
    scopes=['https://www.googleapis.com/auth/drive.readonly']
)
print('Credentials OK')
"
```

### Rate Limit Exceeded

**Symptoms:**
```
Error: Rate limit exceeded
```

**Diagnosis:**
```bash
# Check API usage
# Google Cloud Console → APIs & Services → Quotas
```

**Solutions:**
```python
# Solution 1: Add delay between requests
import time
for file in files:
    time.sleep(1)  # Rate limiting
    
# Solution 2: Use batch requests
# Implement exponential backoff

# Solution 3: Request quota increase
# Google Cloud Console → Request increase
```

### File Not Found

**Symptoms:**
```
Error: File not found: sales_2024.csv
```

**Diagnosis:**
```bash
# List available files
python -c "
from src.ingestion.google_drive_sync import GoogleDriveSync
gd = GoogleDriveSync(credentials_path='...', folder_id='...')
files = gd.list_files()
for f in files:
    print(f['name'])
"
```

**Solutions:**
```python
# Solution 1: Verify file name
# Check exact spelling

# Solution 2: Check folder ID
# Verify correct folder_id

# Solution 3: Check if file is in trashed
# Can add filter: trashed=false
```

---

## Issue 4: Metabase Issues

### Slow Dashboard Loading

**Symptoms:**
- Dashboard takes > 30 seconds to load

**Diagnosis:**
```sql
-- Check query performance in Metabase
-- Admin → Troubleshooting → Logs
```

**Solutions:**
```sql
-- Solution 1: Optimize query
-- Create summary tables

-- Solution 2: Add caching
-- Admin → Caching
-- Set cache duration

-- Solution 3: Clear Metabase cache
docker exec metabase bash -c "rm -rf /metabase-data/db/*"
docker restart metabase
```

### Data Not Showing

**Symptoms:**
- Dashboard shows "No results"

**Diagnosis:**
```sql
-- Run query in Databricks directly
SELECT * FROM data_platform.gold.fct_orders LIMIT 10
```

**Solutions:**
```sql
-- Solution 1: Sync database
-- Metabase Admin → Databases → Sync

-- Solution 2: Refresh field values
-- Metabase Admin → Databases → → Rescan

-- Solution 3: Check data timestamp
SELECT MAX(_etl_loaded_at) FROM data_platform.gold.fct_orders
```

### Login Issues

**Symptoms:**
- Can't login to Metabase

**Solutions:**
```bash
# Reset admin password
docker exec -it metabase metabase reset-password
# Follow prompts

# Or create new admin
docker exec -it metabase metabase create-admin
```

---

## Issue 5: Python Script Issues

### Module Not Found

**Symptoms:**
```
ModuleNotFoundError: No module named 'src'
```

**Solutions:**
```bash
# Solution 1: Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Solution 2: Install package
pip install -e .

# Solution 3: Run from project root
cd /path/to/project
python src/ingestion/run.py
```

### Virtual Environment Issues

**Symptoms:**
```
Python version mismatch
```

**Solutions:**
```bash
# Solution 1: Recreate venv
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Solution 2: Check Python version
python --version
```

---

## Issue 6: Docker Issues

### Out of Memory

**Symptoms:**
```
Error: Cannot allocate memory
```

**Solutions:**
```bash
# Solution 1: Increase Docker memory
# Docker Desktop → Settings → Resources → Memory: 8GB

# Solution 2: Clear unused containers
docker system prune -a

# Solution 3: Increase swap
# Docker Desktop → Settings → Resources → Swap: 2GB
```

### Port Already in Use

**Symptoms:**
```
Error: Ports are not available
```

**Solutions:**
```bash
# Find what's using the port
lsof -i :8080

# Kill the process
kill -9 <PID>

# Or use different port
# docker-compose.yml
ports:
  - "8081:8080"  # Changed
```

---

## Error Code Reference

| Error Code | Meaning | Quick Fix |
|------------|---------|-----------|
| `E001` | Databricks token expired | Regenerate token |
| `E002` | Google Drive rate limit | Add delay |
| `E003` | Schema mismatch | Check column names |
| `E004` | Cluster not running | Start cluster |
| `E005` | File not found | Verify file name |
| `E006` | Memory exceeded | Increase Docker RAM |
| `E007` | Port conflict | Change port |
| `E008` | Permission denied | Check permissions |
| `E009` | Timeout | Increase timeout |
| `E010` | Null value | Check data quality |

## Emergency Contacts

| Component | Owner | Contact |
|-----------|-------|---------|
| Databricks | DevOps | #databricks-support |
| Airflow | DevOps | #airflow-support |
| Google Drive | IT | IT Helpdesk |
| Metabase | Analytics | #analytics-team |

## Related Documentation

- [Daily Checklist](./daily-checklist.md)
- [Backup & Recovery](./backup-recovery.md)
- [Log Analysis Guide](../logging/log-analysis.md)
