# Backup & Recovery Guide

## Overview

Hướng dẫn backup và recovery cho Data Platform.

## Backup Strategy

### What to Backup

| Component | Frequency | Retention | Location |
|-----------|-----------|-----------|----------|
| Configuration files | Weekly | 90 days | Git + Local |
| Environment (.env) | Weekly | 90 days | Encrypted USB |
| Airflow DAGs | Weekly | 90 days | Git |
| dbt models | On change | Forever | Git |
| Metabase data | Weekly | 30 days | Local |
| Databricks notebooks | Weekly | 90 days | Export |
| Log files | Daily | 30 days | Local |
| Google Drive raw data | Daily | 7 days | Version history |

## Backup Procedures

### 1. Configuration Backup

```bash
# scripts/backup_config.sh
#!/bin/bash
set -e

BACKUP_DIR="./backups/config/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup .env (encrypted)
openssl enc -aes-256-cbc -salt -in .env -out $BACKUP_DIR/env.enc
cp -r configs/ $BACKUP_DIR/configs

# Backup docker-compose.yml
cp docker-compose.yml $BACKUP_DIR/

# Backup Airflow DAGs
cp -r airflow/dags/ $BACKUP_DIR/dags/

# Backup dbt project
cp -r data_platform_dbt/models/ $BACKUP_DIR/dbt_models/

# Compress
tar -czf backups/config_$(date +%Y%m%d).tar.gz $BACKUP_DIR

# Upload to cloud (optional)
# aws s3 cp backups/config_$(date +%Y%m%d).tar.gz s3://bucket/backups/

echo "Backup complete: $BACKUP_DIR"
```

### 2. Metabase Backup

```bash
# scripts/backup_metabase.sh
#!/bin/bash
set -e

BACKUP_DIR="./backups/metabase/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup Metabase database (if using external DB)
docker exec postgres pg_dump -U metabase metabase > $BACKUP_DIR/metabase_db.sql

# Export Metabase questions and dashboards
# Admin → Settings → Export
# Save to $BACKUP_DIR/

# Backup Metabase application data
docker run --rm \
  -v metabase-data:/data \
  -v $(pwd)/$BACKUP_DIR:/backup \
  alpine tar czf /backup/metabase_app.tar.gz -C /data .

echo "Metabase backup complete"
```

### 3. Databricks Export

```bash
# scripts/backup_databricks.sh
#!/bin/bash
set -e

BACKUP_DIR="./backups/databricks/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Export notebooks
databricks workspace export_dir /Repos /$(pwd)/$BACKUP_DIR/notebooks

# Export secrets (if using secret scope)
databricks secrets list-scopes

# Export job definitions
databricks jobs list > $BACKUP_DIR/jobs.json

# Export cluster configurations
databricks clusters list > $BACKUP_DIR/clusters.json

# Export SQL warehouses
databricks sql warehouses list > $BACKUP_DIR/warehouses.json

echo "Databricks backup complete"
```

### 4. Google Drive Data

```bash
# scripts/backup_gdrive.sh
#!/bin/bash
set -e

BACKUP_DIR="./backups/gdrive/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Note: Google Drive has built-in versioning
# This script backs up file list and metadata

python << 'EOF'
import os
from dotenv import load_dotenv
from src.ingestion.google_drive_sync import GoogleDriveSync
import json

load_dotenv()

gd = GoogleDriveSync(
    credentials_path=os.environ.get('GOOGLE_DRIVE_CREDENTIALS_PATH'),
    folder_id=os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
)

# List all files
files = gd.list_files(limit=1000)

# Save metadata
with open('backups/gdrive/files_metadata.json', 'w') as f:
    json.dump(files, f, indent=2)

print(f"Backed up {len(files)} file metadata")
EOF

echo "Google Drive metadata backup complete"
```

## Automated Backup Schedule

```yaml
# docker-compose.backup.yml
version: '3.8'

services:
  backup:
    image: data-platform:latest
    volumes:
      - ./backups:/backups
    environment:
      - BACKUP_SCHEDULE=0 2 * * *  # 2 AM daily
    command: python scripts/backup_all.py
    restart: unless-stopped
```

## Recovery Procedures

### 1. Recover Configuration

```bash
# scripts/restore_config.sh
#!/bin/bash

BACKUP_DATE=$1
BACKUP_FILE="./backups/config/config_${BACKUP_DATE}.tar.gz"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup not found: $BACKUP_FILE"
    exit 1
fi

# Extract backup
tar -xzf $BACKUP_FILE -C ./backups/

# Restore .env (decrypt)
openssl enc -d -aes-256-cbc -in ./backups/config/env.enc -out .env
source .env

# Restore configs
cp -r ./backups/config/configs/* configs/

# Restore Airflow DAGs
cp -r ./backups/config/dags/* airflow/dags/

echo "Configuration restored from $BACKUP_DATE"
```

### 2. Recover Metabase

```bash
# scripts/restore_metabase.sh
#!/bin/bash

BACKUP_DIR="./backups/metabase/$1"

# Stop Metabase
docker-compose stop metabase

# Restore database
cat $BACKUP_DIR/metabase_db.sql | docker exec -i postgres psql -U metabase

# Restore application data
docker run --rm \
  -v metabase-data:/data \
  -v $(pwd)/$BACKUP_DIR:/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/metabase_app.tar.gz -C /data"

# Start Metabase
docker-compose start metabase

echo "Metabase restored"
```

### 3. Recover Databricks

```bash
# scripts/restore_databricks.sh
#!/bin/bash

BACKUP_DIR="./backups/databricks/$1"

# Import notebooks
databricks workspace import_dir $BACKUP_DIR/notebooks /Repos/data-platform

# Recreate jobs (if needed)
# databricks jobs create --json-file $BACKUP_DIR/jobs.json

echo "Databricks restored"
```

## Disaster Recovery

### Scenario 1: Full System Loss

```bash
# 1. Rebuild infrastructure
docker-compose up -d

# 2. Restore configurations
./scripts/restore_config.sh 20240115

# 3. Restart services
docker-compose restart

# 4. Restore Metabase
./scripts/restore_metabase.sh 20240115

# 5. Verify Databricks
databricks workspace list

# 6. Run test pipeline
python scripts/test_pipeline.py
```

### Scenario 2: Data Corruption

```sql
-- In Databricks, restore from time travel
RESTORE TABLE data_platform.gold.fct_orders TO TIMESTAMP AS OF TIMESTAMP '2024-01-15 00:00:00'

-- Or restore specific version
RESTORE TABLE data_platform.gold.fct_orders TO VERSION AS OF 5
```

### Scenario 3: Accidental Deletion

```sql
-- Recover deleted table
RESTORE TABLE data_platform.gold.dim_customers TO TIMESTAMP AS OF TIMESTAMP_ADD(CURRENT_TIMESTAMP, INTERVAL -1 HOUR)

-- Undrop table (if recently dropped)
UNDROP TABLE data_platform.gold.dim_customers
```

## Verification

### Test Backup Integrity

```bash
# scripts/verify_backup.sh
#!/bin/bash

BACKUP_FILE="./backups/config/$(date +%Y%m%d --date='1 day ago').tar.gz"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup not found!"
    exit 1
fi

# Test extraction
tar -tzf $BACKUP_FILE > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Backup file is valid"
else
    echo "Backup file is corrupted!"
    exit 1
fi

# Check contents
tar -tzf $BACKUP_FILE | grep -q ".env"
if [ $? -eq 0 ]; then
    echo "Backup contains .env"
fi
```

### Test Restore Process

```bash
# Monthly: Test restore to verify backup works
./scripts/restore_config.sh $(date +%Y%m%d --date='1 week ago')
```

## Retention Policy

| Backup Type | Frequency | Keep For |
|-------------|-----------|----------|
| Config | Weekly | 90 days |
| Metabase | Weekly | 30 days |
| Databricks | Weekly | 90 days |
| Logs | Daily | 30 days |
| Google Drive | Daily | 7 days |

## Storage Calculator

```
Weekly backup size: ~500 MB
Monthly storage needed: ~2 GB
Annual storage needed: ~24 GB
```

## Related Documentation

- [Daily Checklist](./daily-checklist.md)
- [Troubleshooting Guide](./troubleshooting.md)
- [Logging Architecture](../logging/architecture.md)
