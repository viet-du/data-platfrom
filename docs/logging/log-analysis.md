# Log Analysis Guide

## Overview

Hướng dẫn phân tích và debug logs để troubleshoot issues khi agent chạy.

## Quick Log Commands

### View Recent Logs

```bash
# View last 100 lines
tail -n 100 logs/data_platform_20240115.log

# Follow logs in real-time
tail -f logs/data_platform_20240115.log

# View only errors
grep "ERROR" logs/data_platform_20240115.log

# View errors with context (5 lines before/after)
grep -C 5 "ERROR" logs/data_platform_20240115.log
```

### Search Patterns

```bash
# Find all logs for a specific file
grep "sales_2024.csv" logs/data_platform_20240115.log

# Find all logs for a specific function
grep "download_file" logs/data_platform_20240115.log

# Find all logs for a specific request
grep "req-12345" logs/data_platform_20240115.log

# Count errors by type
grep "ERROR" logs/data_platform_*.log | cut -d'|' -f4 | sort | uniq -c
```

## Common Issues & Solutions

### Issue 1: Connection Failed

**Log Pattern:**
```
ERROR | databricks.connection | Connection failed: Invalid token
```

**Investigation Steps:**
```bash
# 1. Check the full error context
grep -C 10 "Connection failed" logs/data_platform_*.log

# 2. Verify credentials are set
grep "DATABRICKS" .env

# 3. Test connection manually
databricks workspace list

# 4. Check token expiration
# Token có thể hết hạn → Generate new token
```

**Solution:**
```bash
# Generate new Databricks token
# 1. Go to Databricks → User Settings → Access tokens
# 2. Generate new token
# 3. Update .env
# 4. Restart application
```

---

### Issue 2: File Not Found

**Log Pattern:**
```
WARNING | google_drive.sync | File not found: sales_missing.csv
```

**Investigation Steps:**
```bash
# 1. List available files
python -c "
from src.ingestion.google_drive_sync import GoogleDriveSync
gd = GoogleDriveSync(credentials_path='./configs/...', folder_id='...')
files = gd.list_files()
for f in files:
    print(f['name'])
"

# 2. Check if file was deleted
grep "sales_missing" logs/data_platform_*.log | head -20

# 3. Verify folder ID
grep "FOLDER_ID" .env
```

**Solution:**
```python
# Option 1: Skip missing files gracefully
def download_files(self, file_ids):
    for file_id in file_ids:
        try:
            self.download_file(file_id)
        except FileNotFoundError:
            logger.warning(f"Skipping missing file: {file_id}")
            continue

# Option 2: Create file if missing (for testing)
# Create dummy file in Google Drive
```

---

### Issue 3: Query Timeout

**Log Pattern:**
```
ERROR | databricks.query | Query timeout after 60s
```

**Investigation Steps:**
```bash
# 1. Check query performance
# Run the query directly in Databricks

# 2. Check table size
python -c "
from databricks import sql
conn = sql.connect(host='...', token='...', http_path='...')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM table_name')
print(cursor.fetchone())
"

# 3. Check execution plan
# In Databricks: EXPLAIN FORMATTED SELECT ...
```

**Solution:**
```python
# Option 1: Increase timeout
connection = sql.connect(
    host=host,
    token=token,
    http_path=http_path,
    timeout=300  # 5 minutes
)

# Option 2: Optimize query
# Add indexes, partition by date, etc.

# Option 3: Process in batches
for batch in chunks(large_dataset, 10000):
    process(batch)
```

---

### Issue 4: Memory Error

**Log Pattern:**
```
CRITICAL | ingestion.process | MemoryError: Cannot allocate 8GB
```

**Investigation Steps:**
```bash
# 1. Check available memory
free -h

# 2. Check current process memory
ps aux | grep python

# 3. Check file size
ls -lh data/raw/large_file.csv
```

**Solution:**
```python
# Option 1: Read file in chunks
import pandas as pd

for chunk in pd.read_csv('large_file.csv', chunksize=10000):
    process(chunk)

# Option 2: Use streaming
def stream_csv(filepath):
    with open(filepath) as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row

# Option 3: Use Spark instead of pandas
spark = SparkSession.builder.getOrCreate()
df = spark.read.csv('large_file.csv')
```

---

### Issue 5: Schema Mismatch

**Log Pattern:**
```
ERROR | transformation.dbt | Compilation error: 'order_id' does not exist
```

**Investigation Steps:**
```bash
# 1. Check actual columns in source table
python -c "
from databricks import sql
conn = sql.connect(host='...', token='...', http_path='...')
cursor = conn.cursor()
cursor.execute('DESCRIBE table_name')
for row in cursor.fetchall():
    print(row)
"

# 2. Check dbt model
cat models/silver/int_orders_base.sql

# 3. Check if model was compiled
dbt compile --select int_orders_base
```

**Solution:**
```sql
-- Check column names in source
DESCRIBE data_platform.bronze.sales_raw;

-- Update model if column name is different
-- FROM order_id TO order_number
SELECT order_number AS order_id FROM ...
```

## Log Analysis Scripts

### Script 1: Error Summary

```python
# scripts/analyze_errors.py
"""
Analyze errors from log files
"""
import re
from collections import Counter
from pathlib import Path


def analyze_errors(log_file: str):
    """Generate error summary from log file"""
    
    errors = []
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?\| (ERROR|CRITICAL) \| (.+?) \| (.+?)(?:\n|$)'
    
    with open(log_file, 'r') as f:
        for match in re.finditer(pattern, f.read()):
            timestamp, level, logger, message = match.groups()
            errors.append({
                'timestamp': timestamp,
                'level': level,
                'logger': logger,
                'message': message.strip()
            })
    
    # Generate summary
    print("=" * 60)
    print("ERROR SUMMARY")
    print("=" * 60)
    print(f"Total errors: {len(errors)}")
    print()
    
    # By logger
    print("Errors by logger:")
    for logger, count in Counter(e['logger'] for e in errors).most_common(10):
        print(f"  {logger}: {count}")
    print()
    
    # By message
    print("Most common errors:")
    for msg, count in Counter(e['message'] for e in errors).most_common(5):
        print(f"  {count}x: {msg[:60]}...")
    print()
    
    # Recent errors
    print("Recent 5 errors:")
    for error in errors[-5:]:
        print(f"  [{error['timestamp']}] {error['message']}")


if __name__ == '__main__':
    import sys
    log_file = sys.argv[1] if len(sys.argv) > 1 else 'logs/data_platform_today.log'
    analyze_errors(log_file)
```

### Script 2: Performance Analysis

```python
# scripts/analyze_performance.py
"""
Analyze performance from logs
"""
import re
from datetime import datetime


def analyze_performance(log_file: str):
    """Generate performance summary from log file"""
    
    durations = []
    pattern = r'duration_ms=(\d+)'
    
    with open(log_file, 'r') as f:
        for line in f:
            matches = re.findall(pattern, line)
            durations.extend(int(m) for m in matches)
    
    if not durations:
        print("No duration data found")
        return
    
    durations.sort()
    
    print("=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Total operations: {len(durations)}")
    print(f"Min: {min(durations)}ms")
    print(f"Max: {max(durations)}ms")
    print(f"Avg: {sum(durations) // len(durations)}ms")
    print(f"P50: {durations[len(durations) // 2]}ms")
    print(f"P95: {durations[int(len(durations) * 0.95)]}ms")
    print(f"P99: {durations[int(len(durations) * 0.99)]}ms")
```

### Script 3: Pipeline Trace

```python
# scripts/trace_pipeline.py
"""
Trace a specific pipeline execution
"""
import re
import sys


def trace_pipeline(log_file: str, pipeline_id: str):
    """Trace all logs for a specific pipeline run"""
    
    print(f"Tracing pipeline: {pipeline_id}")
    print("=" * 60)
    
    with open(log_file, 'r') as f:
        for line in f:
            if pipeline_id in line:
                print(line.strip())


if __name__ == '__main__':
    pipeline_id = sys.argv[1] if len(sys.argv) > 1 else 'pipeline-20240115'
    log_file = 'logs/data_platform_today.log'
    trace_pipeline(log_file, pipeline_id)
```

## Debugging Tips

### Tip 1: Enable Debug Logging

```bash
# Temporarily enable DEBUG logging
export LOG_LEVEL=DEBUG
python src/main.py
```

### Tip 2: Add Temporary Logs

```python
# Add debug logs to understand flow
logger.debug(f"Variable values: {locals()}")
logger.debug(f"DataFrame shape: {df.shape}")
logger.debug(f"Query result: {cursor.fetchall()}")
```

### Tip 3: Use Breakpoints

```python
# Add breakpoint in code
import pdb
pdb.set_trace()

# Or use ipdb
import ipdb
ipdb.set_trace()
```

### Tip 4: Isolate the Issue

```python
# Test just the failing part
def test_issue():
    try:
        # Reproduce the issue
        result = failing_function()
        logger.info(f"Success: {result}")
    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
        raise

test_issue()
```

## Log Monitoring

### Real-time Monitoring

```bash
# Watch for errors
tail -f logs/data_platform_*.log | grep ERROR

# Watch for specific logger
tail -f logs/data_platform_*.log | grep "ingestion.google_drive"

# Watch for specific request
tail -f logs/data_platform_*.log | grep "req-12345"
```

### Alerting on Errors

```python
# scripts/error_alert.py
"""
Send alerts when errors are detected
"""
import re
from pathlib import Path
import requests
import time


def monitor_logs(slack_webhook: str = None):
    """Monitor logs and send alerts for errors"""
    
    log_file = Path('logs/data_platform_today.log')
    last_position = 0
    
    while True:
        # Read new lines
        with open(log_file, 'r') as f:
            f.seek(last_position)
            new_lines = f.readlines()
            last_position = f.tell()
        
        # Check for errors
        for line in new_lines:
            if 'ERROR' in line or 'CRITICAL' in line:
                # Send alert
                if slack_webhook:
                    requests.post(slack_webhook, json={
                        'text': f"Error detected:\n{line}"
                    })
        
        time.sleep(10)  # Check every 10 seconds


if __name__ == '__main__':
    import os
    webhook = os.environ.get('SLACK_WEBHOOK')
    monitor_logs(slack_webhook=webhook)
```

## Common Log Patterns

| Pattern | Meaning | Action |
|---------|---------|--------|
| `Connection refused` | Service not reachable | Check service is running |
| `Timeout after 60s` | Operation took too long | Increase timeout or optimize |
| `File not found` | Missing file | Check file path |
| `Permission denied` | Access issue | Check permissions |
| `Out of memory` | Memory exhausted | Reduce batch size |
| `Schema mismatch` | Column name changed | Update model |
| `Duplicate key` | Primary key conflict | Check deduplication logic |
| `Null value` | Missing required field | Check data quality |

## Related Documentation

- [Logging Architecture](./architecture.md)
- [Logging Setup Guide](./setup-guide.md)
- [Troubleshooting Runbook](../runbooks/troubleshooting.md)
