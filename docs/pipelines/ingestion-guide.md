# Ingestion Pipeline Guide

## Overview

Chi tiết về cách thiết kế và vận hành data ingestion pipeline.

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INGESTION PIPELINE                                   │
│                                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐               │
│  │   SOURCE     │────▶│  EXTRACT    │────▶│  VALIDATE   │               │
│  │              │     │              │     │              │               │
│  │ Google Drive │     │ Download    │     │ Schema      │               │
│  │ REST APIs    │     │ API Fetch   │     │ Quality     │               │
│  │ Database     │     │ CDC Stream  │     │ Checks      │               │
│  └──────────────┘     └──────────────┘     └──────┬───────┘               │
│                                                     │                       │
│                                                     ▼                       │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐               │
│  │  DELTA LAKE  │◀────│   LOAD      │◀────│  TRANSFORM  │               │
│  │  BRONZE      │     │              │     │              │               │
│  │              │     │ Write to    │     │ Type Cast   │               │
│  │ /bronze/    │     │ Delta Lake  │     │ Add Meta    │               │
│  │  tables/    │     │              │     │ Partition   │               │
│  └──────────────┘     └──────────────┘     └──────────────┘               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Pipeline Types

### Type 1: Batch Ingestion (Daily)

```python
# pipelines/batch_ingestion.py
"""
Daily batch ingestion from Google Drive
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from src.ingestion.google_drive_sync import GoogleDriveSync
from src.ingestion.databricks_writer import DatabricksWriter
from src.ingestion.file_validator import FileValidator
from src.utils.logging_config import get_logger
from src.utils.exceptions import IngestionError

logger = get_logger(__name__)


class BatchIngestionPipeline:
    """Daily batch ingestion pipeline"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.gdrive = GoogleDriveSync(
            credentials_path=config['credentials_path'],
            folder_id=config['folder_id']
        )
        self.writer = DatabricksWriter(
            host=config['databricks_host'],
            token=config['databricks_token'],
            http_path=config['http_path']
        )
        self.validator = FileValidator()
        
    def run(self, date: datetime = None) -> Dict:
        """
        Run daily ingestion
        
        Args:
            date: Date to process (defaults to yesterday)
            
        Returns:
            Pipeline result dict
        """
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        logger.info(f"Starting batch ingestion for {date.strftime('%Y-%m-%d')}")
        
        result = {
            'date': date.strftime('%Y-%m-%d'),
            'start_time': datetime.now().isoformat(),
            'files_processed': 0,
            'rows_ingested': 0,
            'errors': []
        }
        
        try:
            # Step 1: Check for new files
            since = date - timedelta(days=1)
            new_files = self.gdrive.list_files_modified_after(since=since)
            
            if not new_files:
                logger.info("No new files found")
                result['status'] = 'success'
                result['message'] = 'No new files'
                return result
            
            # Step 2: Process each file
            for file in new_files:
                try:
                    # Download
                    local_path = self.gdrive.download_file(file['id'])
                    
                    # Validate
                    validation = self.validator.validate_file(local_path)
                    if not validation['is_valid']:
                        raise IngestionError(
                            f"Validation failed: {validation['errors']}"
                        )
                    
                    # Write to Bronze
                    write_result = self.writer.write_to_bronze(
                        file_path=local_path,
                        mode='append'
                    )
                    
                    result['files_processed'] += 1
                    result['rows_ingested'] += write_result.get('rows', 0)
                    
                    logger.info(
                        f"Processed {file['name']}: "
                        f"{write_result.get('rows', 0)} rows"
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to process {file['name']}: {e}")
                    result['errors'].append({
                        'file': file['name'],
                        'error': str(e)
                    })
            
            result['status'] = 'success'
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            result['status'] = 'failed'
            result['errors'].append({
                'file': 'pipeline',
                'error': str(e)
            })
        
        result['end_time'] = datetime.now().isoformat()
        
        return result
```

### Type 2: Incremental Ingestion (CDC)

```python
# pipelines/incremental_ingestion.py
"""
Incremental ingestion using change data capture
"""
import os
import logging
from datetime import datetime
from typing import Dict, List

from src.ingestion.cdc_client import CDCClient
from src.ingestion.databricks_writer import DatabricksWriter
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class IncrementalIngestionPipeline:
    """Incremental/CDC ingestion pipeline"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.writer = DatabricksWriter(
            host=config['databricks_host'],
            token=config['databricks_token'],
            http_path=config['http_path']
        )
        self.cdc_client = CDCClient(config['source_config'])
        
    def run(self) -> Dict:
        """Run incremental ingestion"""
        logger.info("Starting incremental ingestion")
        
        result = {
            'start_time': datetime.now().isoformat(),
            'changes_detected': 0,
            'rows_ingested': 0
        }
        
        try:
            # Get changes since last run
            last_position = self._get_last_position()
            changes = self.cdc_client.get_changes_since(last_position)
            
            if not changes:
                logger.info("No changes detected")
                result['status'] = 'no_changes'
                return result
            
            result['changes_detected'] = len(changes)
            
            # Apply changes to Delta Lake
            for change in changes:
                self._apply_change(change)
                result['rows_ingested'] += 1
            
            # Update position
            self._save_position(changes[-1]['position'])
            
            result['status'] = 'success'
            
        except Exception as e:
            logger.error(f"Incremental ingestion failed: {e}")
            result['status'] = 'failed'
            result['error'] = str(e)
        
        result['end_time'] = datetime.now().isoformat()
        
        return result
    
    def _get_last_position(self) -> str:
        """Get last CDC position from state file"""
        state_file = self.config.get('state_file', './data/.cdc_state')
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                return f.read().strip()
        return None
    
    def _save_position(self, position: str):
        """Save CDC position to state file"""
        state_file = self.config.get('state_file', './data/.cdc_state')
        with open(state_file, 'w') as f:
            f.write(position)
```

### Type 3: API Ingestion

```python
# pipelines/api_ingestion.py
"""
REST API ingestion pipeline
"""
import os
import logging
import time
from datetime import datetime
from typing import Dict, List

import requests
from ratelimit import limits, sleep_and_retry

from src.ingestion.databricks_writer import DatabricksWriter
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class APIIngestionPipeline:
    """REST API ingestion pipeline"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.writer = DatabricksWriter(
            host=config['databricks_host'],
            token=config['databricks_token'],
            http_path=config['http_path']
        )
        self.base_url = config['api_url']
        self.session = requests.Session()
        self.session.headers.update(config.get('headers', {}))
    
    @sleep_and_retry
    @limits(calls=100, period=60)  # Rate limiting
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make API request with rate limiting"""
        url = f"{self.base_url}/{endpoint}"
        
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        return response.json()
    
    def run(self) -> Dict:
        """Run API ingestion"""
        logger.info(f"Starting API ingestion from {self.base_url}")
        
        result = {
            'start_time': datetime.now().isoformat(),
            'endpoints_processed': 0,
            'records_ingested': 0
        }
        
        endpoints = self.config.get('endpoints', [])
        
        for endpoint in endpoints:
            try:
                records = self._fetch_endpoint(endpoint)
                if records:
                    self.writer.write_records(
                        table_name=endpoint['table_name'],
                        records=records
                    )
                    result['endpoints_processed'] += 1
                    result['records_ingested'] += len(records)
            except Exception as e:
                logger.error(f"Failed to fetch {endpoint['name']}: {e}")
                result['errors'] = result.get('errors', [])
                result['errors'].append({
                    'endpoint': endpoint['name'],
                    'error': str(e)
                })
        
        result['end_time'] = datetime.now().isoformat()
        return result
    
    def _fetch_endpoint(self, endpoint: Dict) -> List[Dict]:
        """Fetch data from a single endpoint"""
        page = 1
        all_records = []
        
        while True:
            params = {
                'page': page,
                'per_page': endpoint.get('page_size', 100)
            }
            
            data = self._make_request(endpoint['path'], params=params)
            
            records = data.get(endpoint.get('records_key', 'data'), [])
            if not records:
                break
            
            all_records.extend(records)
            
            # Check pagination
            if page >= endpoint.get('max_pages', 10):
                break
            
            page += 1
            time.sleep(1)  # Be nice to the API
        
        logger.info(f"Fetched {len(all_records)} records from {endpoint['name']}")
        return all_records
```

## File Validation

```python
# src/ingestion/file_validator.py
"""
File validation before ingestion
"""
import os
import logging
from typing import Dict, List
from pathlib import Path

import pandas as pd
from great_expectations.dataset import PandasDataset

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class FileValidator:
    """Validate files before ingestion"""
    
    def validate_file(self, file_path: str) -> Dict:
        """
        Validate a file
        
        Args:
            file_path: Path to file
            
        Returns:
            Validation result dict
        """
        result = {
            'file': file_path,
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check file exists
        if not os.path.exists(file_path):
            result['is_valid'] = False
            result['errors'].append('File does not exist')
            return result
        
        # Check file size
        size = os.path.getsize(file_path)
        if size == 0:
            result['is_valid'] = False
            result['errors'].append('File is empty')
            return result
        
        if size > 1_000_000_000:  # 1GB
            result['warnings'].append('File is larger than 1GB')
        
        # Check file extension
        ext = Path(file_path).suffix.lower()
        if ext not in ['.csv', '.xlsx', '.xls', '.json']:
            result['is_valid'] = False
            result['errors'].append(f'Unsupported file type: {ext}')
            return result
        
        # Validate content
        try:
            df = pd.read_csv(file_path, nrows=1000)
            
            # Check columns
            if df.empty or len(df.columns) == 0:
                result['is_valid'] = False
                result['errors'].append('File has no columns')
            
            # Check for required columns (configurable)
            required_cols = ['id', 'date', 'amount']
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                result['warnings'].append(f'Missing columns: {missing}')
            
            # Data quality checks
            ge_df = PandasDataset(df)
            
            # Check for nulls in key columns
            if 'id' in df.columns:
                null_count = df['id'].isna().sum()
                if null_count > 0:
                    result['warnings'].append(
                        f'{null_count} null values in id column'
                    )
            
        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f'Failed to read file: {e}')
        
        return result
```

## Monitoring & Alerting

```python
# pipelines/monitoring.py
"""
Pipeline monitoring and alerting
"""
import logging
from datetime import datetime
from typing import Dict, List

from src.utils.logging_config import get_logger
from src.utils.alerting import send_alert

logger = get_logger(__name__)


class PipelineMonitor:
    """Monitor pipeline execution"""
    
    def __init__(self):
        self.alerts = []
    
    def on_pipeline_start(self, pipeline_name: str, config: Dict):
        """Called when pipeline starts"""
        logger.info(f"Pipeline started: {pipeline_name}")
        self.alerts.append({
            'event': 'start',
            'pipeline': pipeline_name,
            'time': datetime.now().isoformat()
        })
    
    def on_pipeline_complete(self, pipeline_name: str, result: Dict):
        """Called when pipeline completes"""
        logger.info(
            f"Pipeline completed: {pipeline_name} - "
            f"Status: {result.get('status')}"
        )
        
        self.alerts.append({
            'event': 'complete',
            'pipeline': pipeline_name,
            'status': result.get('status'),
            'time': datetime.now().isoformat()
        })
        
        # Send alerts
        if result.get('status') == 'failed':
            send_alert(
                severity='error',
                title=f"Pipeline Failed: {pipeline_name}",
                message=result.get('errors', [])
            )
        elif result.get('status') == 'success' and result.get('warnings'):
            send_alert(
                severity='warning',
                title=f"Pipeline Warning: {pipeline_name}",
                message=result.get('warnings')
            )
    
    def on_task_failure(self, task_name: str, error: Exception):
        """Called when a task fails"""
        logger.error(f"Task failed: {task_name} - {error}")
        
        send_alert(
            severity='error',
            title=f"Task Failed: {task_name}",
            message=str(error)
        )
```

## Error Handling Strategy

### Retry Logic

```python
# Retry decorator
from functools import wraps
import time

def retry(max_attempts=3, delay=5, backoff=2):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    wait = delay * (backoff ** (attempt - 1))
                    logger.warning(
                        f"Attempt {attempt} failed: {e}. "
                        f"Retrying in {wait}s..."
                    )
                    time.sleep(wait)
        return wrapper
    return decorator
```

### Dead Letter Queue

```python
# For failed records, write to DLQ
def write_to_dlq(records: List[Dict], reason: str):
    """Write failed records to Dead Letter Queue"""
    dlq_path = f"./data/dlq/{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    import json
    with open(dlq_path, 'w') as f:
        json.dump({
            'reason': reason,
            'records': records,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)
    
    logger.warning(f"Written {len(records)} records to DLQ: {dlq_path}")
```

## Performance Optimization

| Technique | Use Case | Impact |
|-----------|----------|--------|
| Batch downloads | Many small files | 10x faster |
| Parallel ingestion | Multiple tables | 3x faster |
| Compression | Large files | 50% smaller |
| Partitioned writes | Large tables | 5x faster |
| Schema caching | Repeated schemas | 20% faster |

## Related Documentation

- [Transformation Pipeline](./transformation-guide.md)
- [Google Drive Setup](../setup/google-drive-setup.md)
- [Databricks Setup](../setup/databricks-setup.md)
