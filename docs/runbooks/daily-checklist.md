# Daily Checklist

## Overview

Danh sách kiểm tra hàng ngày để đảm bảo Data Platform hoạt động tốt.

## Morning Check (9:00 AM)

### 1. Check Pipeline Health

```bash
# Check if Airflow is running
docker-compose ps

# Check Airflow webserver
curl -s http://localhost:8080/health | jq .

# Check for failed DAGs
docker-compose logs airflow-scheduler --since 1h | grep -i "failed\|error"
```

### 2. Check Databricks

```bash
# Check Databricks cluster status
databricks clusters list

# Check for running jobs
databricks jobs list

# Verify data freshness
python -c "
from databricks import sql
conn = sql.connect(host='...', token='...', http_path='...')
cursor = conn.cursor()
cursor.execute('SELECT MAX(_etl_loaded_at) FROM data_platform.gold.fct_orders')
print('Last load:', cursor.fetchone()[0])
"
```

### 3. Check Google Drive

```bash
# List recent files
python -c "
from src.ingestion.google_drive_sync import GoogleDriveSync
gd = GoogleDriveSync(credentials_path='...', folder_id='...')
files = gd.list_files()
for f in files:
    print(f\"{f['name']} - {f['modifiedTime']}\")
"
```

### 4. Check Metabase

```bash
# Check Metabase is running
curl -s http://localhost:3000/api/health

# Check dashboard refresh
# Login to Metabase → Admin → Dashboard
```

### 5. Check Logs

```bash
# Check for errors in last 24h
grep -i "ERROR\|CRITICAL" logs/data_platform_*.log | tail -20

# Check pipeline completion
grep "Pipeline completed" logs/data_platform_*.log | tail -5
```

## Checklist Template

```
╔══════════════════════════════════════════════════════════════════════╗
║                    DAILY CHECKLIST                                   ║
╠══════════════════════════════════════════════════════════════════════╣
║ Date: _________________  Day: _________________                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║ □ AIRFLOW                                                            ║
║   □ Webserver running        □ Scheduler running                     ║
║   □ No failed DAGs          □ Daily ingestion succeeded              ║
║                                                                       ║
║ □ DATABRICKS                                                         ║
║   □ Cluster running           □ Jobs completed                        ║
║   □ Data fresh               □ No schema errors                      ║
║                                                                       ║
║ □ GOOGLE DRIVE                                                        ║
║   □ Files available           □ No access errors                     ║
║   □ Service account ok       □ No rate limit issues                 ║
║                                                                       ║
║ □ METABASE                                                           ║
║   □ Dashboard loading        □ Data up-to-date                       ║
║   □ No query errors          □ Permissions correct                  ║
║                                                                       ║
║ □ LOGS                                                                ║
║   □ No CRITICAL errors      □ Pipeline logs complete                 ║
║   □ No authentication issues □ Log rotation working                 ║
║                                                                       ║
╠══════════════════════════════════════════════════════════════════════╣
║ Notes: ____________________________________________________________ ║
║ __________________________________________________________________ ║
║ __________________________________________________________________ ║
║ __________________________________________________________________ ║
╠══════════════════════════════════════════════════════════════════════╣
║ Completed by: _________________  Time: _____________                ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Weekly Tasks

### Every Monday

1. **Review上周数据**
   ```bash
   # Check weekly metrics
   python scripts/weekly_summary.py
   
   # Review error patterns
   grep "ERROR" logs/data_platform_*.log | grep -v $(date +%Y%m%d) | sort | uniq -c | head -10
   ```

2. **Check storage**
   ```bash
   # Check Databricks storage
   databricks workspace ls /mnt/data_platform
   
   # Check Google Drive storage
   # https://drive.google.com/settings/storage
   
   # Clean old logs
   find logs -name "*.log" -mtime +30 -delete
   ```

3. **Review dbt models**
   ```bash
   cd data_platform_dbt
   dbt test --target prod
   dbt docs generate
   ```

### Every Friday

1. **Backup configs**
   ```bash
   # Backup environment files
   tar -czf configs_backup_$(date +%Y%m%d).tar.gz configs/
   
   # Backup Airflow DAGs
   tar -czf airflow_backup_$(date +%Y%m%d).tar.gz airflow/dags/
   ```

2. **Review weekly performance**
   ```bash
   python scripts/analyze_performance.py logs/data_platform_*.log
   ```

## Monthly Tasks

### End of Month

1. **Archive old data**
   ```sql
   -- In Databricks
   VACUUM data_platform.bronze RETAIN 90 HOURS
   ```

2. **Review and rotate credentials**
   ```bash
   # Check token expiration
   # Rotate if needed
   ```

3. **Documentation review**
   - Update if có changes
   - Review runbooks
   - Update contacts

## Health Metrics to Track

| Metric | Target | Alert if |
|--------|--------|----------|
| Daily pipeline success rate | 100% | < 95% |
| Average ingestion time | < 30 min | > 60 min |
| Databricks cluster uptime | 100% | < 99% |
| Log error rate | < 0.1% | > 1% |
| Dashboard load time | < 5s | > 15s |

## Related Documentation

- [Troubleshooting Guide](./troubleshooting.md)
- [Backup & Recovery](./backup-recovery.md)
- [Log Analysis Guide](../logging/log-analysis.md)
