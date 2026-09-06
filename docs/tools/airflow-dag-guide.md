# Airflow DAG Guide

## Overview

Hướng dẫn tạo và quản lý Airflow DAGs cho Data Platform.

## DAG Structure

```
airflow/
├── dags/
│   ├── __init__.py
│   ├── dag_config.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── daily_ingestion_dag.py
│   │   └── incremental_ingestion_dag.py
│   ├── transformation/
│   │   ├── __init__.py
│   │   ├── dbt_silver_dag.py
│   │   └── dbt_gold_dag.py
│   └── maintenance/
│       ├── __init__.py
│       ├── cleanup_dag.py
│       └── health_check_dag.py
├── plugins/
│   └── __init__.py
└── logs/
```

## DAG Configuration

```python
# dags/dag_config.py
from datetime import datetime, timedelta

# Default args cho tất cả DAGs
DEFAULT_ARGS = {
    'owner': 'data-platform',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

# Tags cho organization
DAG_TAGS = {
    'ingestion': 'Data Ingestion',
    'transformation': 'Data Transformation',
    'serving': 'Data Serving',
    'maintenance': 'System Maintenance',
}
```

## Daily Ingestion DAG

```python
# dags/ingestion/daily_ingestion_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.databricks.operators.databricks import DatabricksSubmitRunOperator
from airflow.utils.dates import days_ago
import logging

# Import custom modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.ingestion.google_drive_sync import GoogleDriveSync
from src.ingestion.databricks_writer import DatabricksWriter
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# DAG Configuration
DAG_ID = 'daily_ingestion'
SCHEDULE_INTERVAL = '0 2 * * *'  # 2 AM daily

DEFAULT_ARGS = {
    'owner': 'data-platform',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    DAG_ID,
    default_args=DEFAULT_ARGS,
    description='Daily data ingestion from Google Drive to Databricks',
    schedule_interval=SCHEDULE_INTERVAL,
    catchup=False,
    tags=['ingestion', 'daily'],
    max_active_runs=1,
) as dag:

    # Task 1: Start
    start = EmptyOperator(
        task_id='start',
        dag=dag
    )

    # Task 2: Check for new files
    def check_new_files(**context):
        """Check Google Drive for new files"""
        logger.info("Checking for new files in Google Drive...")
        
        gdrive = GoogleDriveSync(
            credentials_path=os.environ.get('GOOGLE_DRIVE_CREDENTIALS_PATH'),
            folder_id=os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
        )
        
        new_files = gdrive.list_files_modified_after(
            since=context['dag_run'].conf.get('since')
        )
        
        logger.info(f"Found {len(new_files)} new files")
        
        # Push to XCom for downstream tasks
        context['task_instance'].xcom_push(
            key='new_files',
            value=new_files
        )
        
        return len(new_files) > 0

    check_files = PythonOperator(
        task_id='check_new_files',
        python_callable=check_new_files,
        provide_context=True,
        dag=dag
    )

    # Task 3: Branch - Continue or Skip
    def should_continue(ti):
        """Check if there are files to process"""
        file_count = ti.xcom_pull(task_ids='check_new_files', key='return_value')
        if file_count > 0:
            return 'download_files'
        else:
            return 'skip_ingestion'

    branch = BranchPythonOperator(
        task_id='branch_decision',
        python_callable=should_continue,
        provide_context=True,
        dag=dag
    )

    # Task 4: Download files
    def download_files(**context):
        """Download files from Google Drive"""
        logger.info("Downloading files from Google Drive...")
        
        ti = context['task_instance']
        files = ti.xcom_pull(task_ids='check_new_files', key='new_files')
        
        gdrive = GoogleDriveSync(
            credentials_path=os.environ.get('GOOGLE_DRIVE_CREDENTIALS_PATH'),
            folder_id=os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
        )
        
        local_paths = []
        for f in files:
            local_path = gdrive.download_file(
                file_id=f['id'],
                destination=f"./data/raw/{f['name']}"
            )
            local_paths.append(local_path)
        
        ti.xcom_push(key='local_paths', value=local_paths)
        logger.info(f"Downloaded {len(local_paths)} files")
        
        return local_paths

    download = PythonOperator(
        task_id='download_files',
        python_callable=download_files,
        provide_context=True,
        dag=dag
    )

    # Task 5: Ingest to Databricks
    def ingest_to_bronze(**context):
        """Ingest downloaded files to Databricks Bronze layer"""
        logger.info("Ingesting files to Databricks Bronze layer...")
        
        ti = context['task_instance']
        local_paths = ti.xcom_pull(task_ids='download_files', key='local_paths')
        
        writer = DatabricksWriter(
            host=os.environ.get('DATABRICKS_HOST'),
            token=os.environ.get('DATABRICKS_TOKEN'),
            http_path=os.environ.get('DATABRICKS_HTTP_PATH')
        )
        
        results = writer.write_files_to_bronze(local_paths)
        
        logger.info(f"Ingested {len(results)} files to Bronze")
        
        return results

    ingest = PythonOperator(
        task_id='ingest_to_bronze',
        python_callable=ingest_to_bronze,
        provide_context=True,
        dag=dag
    )

    # Task 6: Skip path
    skip = EmptyOperator(
        task_id='skip_ingestion',
        dag=dag
    )

    # Task 7: End
    end = EmptyOperator(
        task_id='end',
        trigger_rule='none_failed_or_skipped',
        dag=dag
    )

    # Task 8: Notify on Slack
    def notify_success(**context):
        """Send success notification"""
        logger.info("DAG completed successfully!")
        # Implement Slack notification here
        
    notify = PythonOperator(
        task_id='notify_success',
        python_callable=notify_success,
        provide_context=True,
        trigger_rule='all_success',
        dag=dag
    )

    # Task 9: Cleanup
    def cleanup(**context):
        """Cleanup temporary files"""
        logger.info("Cleaning up temporary files...")
        import shutil
        shutil.rmtree('./data/raw', ignore_errors=True)
        os.makedirs('./data/raw', exist_ok=True)

    cleanup_task = PythonOperator(
        task_id='cleanup',
        python_callable=cleanup,
        provide_context=True,
        dag=dag
    )

    # DAG Flow
    start >> check_files >> branch
    branch >> download >> ingest >> cleanup_task >> notify >> end
    branch >> skip >> end
```

## dbt Transformation DAG

```python
# dags/transformation/dbt_silver_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import logging

logger = logging.getLogger(__name__)

DAG_ID = 'dbt_silver_transformation'
SCHEDULE_INTERVAL = '30 3 * * *'  # 3:30 AM daily

DEFAULT_ARGS = {
    'owner': 'data-platform',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': True,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

DBT_PROJECT_PATH = '/path/to/data_platform_dbt'
DBT_TARGET = 'prod'

with DAG(
    DAG_ID,
    default_args=DEFAULT_ARGS,
    description='Run dbt Silver layer transformations',
    schedule_interval=SCHEDULE_INTERVAL,
    catchup=False,
    tags=['transformation', 'dbt', 'silver'],
) as dag:

    start = EmptyOperator(task_id='start')
    end = EmptyOperator(task_id='end')

    # Task 1: dbt Debug (check connection)
    dbt_debug = BashOperator(
        task_id='dbt_debug',
        bash_command=f'''
            cd {DBT_PROJECT_PATH} &&
            source venv/bin/activate &&
            dbt debug --target {DBT_TARGET}
        ''',
    )

    # Task 2: dbt deps (install packages)
    dbt_deps = BashOperator(
        task_id='dbt_deps',
        bash_command=f'''
            cd {DBT_PROJECT_PATH} &&
            source venv/bin/activate &&
            dbt deps
        ''',
    )

    # Task 3: Run Silver models
    dbt_run_silver = BashOperator(
        task_id='dbt_run_silver',
        bash_command=f'''
            cd {DBT_PROJECT_PATH} &&
            source venv/bin/activate &&
            dbt run --target {DBT_TARGET} --select tag:silver
        ''',
    )

    # Task 4: Run Silver tests
    dbt_test_silver = BashOperator(
        task_id='dbt_test_silver',
        bash_command=f'''
            cd {DBT_PROJECT_PATH} &&
            source venv/bin/activate &&
            dbt test --target {DBT_TARGET} --select tag:silver
        ''',
    )

    # Task 5: Generate docs
    dbt_docs = BashOperator(
        task_id='dbt_docs_generate',
        bash_command=f'''
            cd {DBT_PROJECT_PATH} &&
            source venv/bin/activate &&
            dbt docs generate --target {DBT_TARGET}
        ''',
    )

    # DAG Flow
    start >> dbt_debug >> dbt_deps >> dbt_run_silver >> dbt_test_silver >> dbt_docs >> end
```

## Monitoring DAG

```python
# dags/maintenance/health_check_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import logging

logger = logging.getLogger(__name__)

DAG_ID = 'health_check'
SCHEDULE_INTERVAL = '*/15 * * * *'  # Every 15 minutes

with DAG(
    DAG_ID,
    default_args={
        'owner': 'data-platform',
        'start_date': days_ago(1),
        'retries': 3,
        'retry_delay': timedelta(minutes=1),
    },
    description='Health check for all systems',
    schedule_interval=SCHEDULE_INTERVAL,
    catchup=False,
    tags=['maintenance', 'health'],
) as dag:

    def check_databricks():
        """Check Databricks connection"""
        from databricks.sdk import WorkspaceClient
        
        try:
            wks = WorkspaceClient()
            # Simple health check
            logger.info("Databricks: OK")
            return True
        except Exception as e:
            logger.error(f"Databricks: FAILED - {e}")
            return False

    def check_google_drive():
        """Check Google Drive connection"""
        from src.utils.google_drive_utils import GoogleDriveClient
        
        try:
            client = GoogleDriveClient(
                credentials_path='./configs/google-drive-credentials.json',
                folder_id='1ABCDEF...'
            )
            files = client.list_files(limit=1)
            logger.info("Google Drive: OK")
            return True
        except Exception as e:
            logger.error(f"Google Drive: FAILED - {e}")
            return False

    def check_metabase():
        """Check Metabase connection"""
        import requests
        
        try:
            response = requests.get(
                'http://localhost:3000/api/health',
                timeout=5
            )
            if response.status_code == 200:
                logger.info("Metabase: OK")
                return True
        except Exception as e:
            logger.error(f"Metabase: FAILED - {e}")
            return False

    check_databricks = PythonOperator(
        task_id='check_databricks',
        python_callable=check_databricks,
    )

    check_gdrive = PythonOperator(
        task_id='check_google_drive',
        python_callable=check_google_drive,
    )

    check_metabase = PythonOperator(
        task_id='check_metabase',
        python_callable=check_metabase,
    )

    check_databricks >> check_gdrive >> check_metabase
```

## DAG Best Practices

### 1. Idempotency

```python
# Always make tasks idempotent
def ingest_data(**context):
    """This task is safe to run multiple times"""
    
    # Always use upsert/merge, not insert
    writer.merge_to_bronze(
        data=new_data,
        primary_key='order_id'  # Upsert by order_id
    )
```

### 2. Error Handling

```python
# Use task failure callbacks
def on_task_failure(context):
    """Called when task fails"""
    logger.error(f"Task {context['task_instance_key_str']} failed")
    # Send alert

with DAG(...) as dag:
    task = PythonOperator(
        task_id='risky_task',
        python_callable=risky_function,
        on_failure_callback=on_task_failure
    )
```

### 3. SLA Monitoring

```python
# Set SLA for critical tasks
from airflow import settings
from airflow.models.slamiss import SlaMiss

dag = DAG(
    'critical_dag',
    sla_miss_callback=my_sla_callback,  # Alert when SLA missed
    default_args={'sla': timedelta(hours=1)}
)
```

### 4. XCom for Task Communication

```python
# Task A: Push data
task_instance.xcom_push(key='data', value={'key': 'value'})

# Task B: Pull data
data = task_instance.xcom_pull(task_ids='task_a', key='data')
```

## Common Issues

### Lỗi "DAG not found"

```bash
# Check DAG file location
ls -la airflow/dags/

# Check Airflow webserver logs
docker logs airflow-webserver

# Clear DAG cache
docker-compose restart airflow-webserver
```

### Lỗi "Connection refused"

```bash
# Check Airflow is running
docker-compose ps

# Check port 8080
lsof -i :8080
```

## Related Documentation

- [Ingestion Pipeline](../pipelines/ingestion-guide.md)
- [Transformation Pipeline](../pipelines/transformation-guide.md)
- [Troubleshooting](../runbooks/troubleshooting.md)
