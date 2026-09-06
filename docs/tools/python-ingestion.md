# Python Ingestion Guide

## Overview

Hướng dẫn viết Python scripts cho data ingestion từ Google Drive vào Databricks.

## Project Structure

```
src/
├── ingestion/
│   ├── __init__.py
│   ├── google_drive_sync.py
│   ├── databricks_writer.py
│   ├── file_validator.py
│   └── schema_inferrer.py
└── utils/
    ├── __init__.py
    ├── logging_config.py
    └── exceptions.py
```

## Core Ingestion Class

```python
# src/ingestion/google_drive_sync.py
"""
Google Drive sync module for Data Platform
"""
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import io

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

from src.utils.logging_config import get_logger
from src.utils.exceptions import (
    GoogleDriveError,
    FileNotFoundError,
    DownloadError
)

logger = get_logger(__name__)


class GoogleDriveSync:
    """Sync files from Google Drive to local storage"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(
        self,
        credentials_path: str,
        folder_id: str,
        local_download_path: str = './data/raw'
    ):
        """
        Initialize Google Drive sync
        
        Args:
            credentials_path: Path to service account JSON
            folder_id: Google Drive folder ID
            local_download_path: Local directory for downloads
        """
        self.folder_id = folder_id
        self.local_path = local_download_path
        self._creds = None
        self._service = None
        
        # Load credentials
        self._load_credentials(credentials_path)
        
        # Create local directory
        os.makedirs(local_download_path, exist_ok=True)
        
        logger.info(f"GoogleDriveSync initialized for folder: {folder_id}")
    
    def _load_credentials(self, credentials_path: str):
        """Load Google Drive credentials"""
        try:
            self._creds = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=self.SCOPES
            )
            self._service = build('drive', 'v3', credentials=self._creds)
            logger.debug("Credentials loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            raise GoogleDriveError(f"Credential load failed: {e}")
    
    @property
    def service(self):
        """Lazy load service"""
        if self._service is None:
            self._service = build('drive', 'v3', credentials=self._creds)
        return self._service
    
    def list_files(
        self,
        file_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        List all files in folder
        
        Args:
            file_type: Filter by type ('csv', 'excel', 'json')
            limit: Maximum files to return
            
        Returns:
            List of file metadata dicts
        """
        try:
            # Build query
            query = f"'{self.folder_id}' in parents and trashed=false"
            
            if file_type:
                if file_type == 'csv':
                    query += " and mimeType='text/csv'"
                elif file_type == 'excel':
                    query += " and (mimeType='application/vnd.ms-excel' or mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')"
                elif file_type == 'json':
                    query += " and mimeType='application/json'"
            
            results = self.service.files().list(
                q=query,
                pageSize=limit,
                fields="files(id, name, mimeType, createdTime, modifiedTime, size)"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Found {len(files)} files in folder")
            
            return files
            
        except HttpError as e:
            logger.error(f"Google Drive API error: {e}")
            raise GoogleDriveError(f"List files failed: {e}")
    
    def list_files_modified_after(
        self,
        since: Optional[datetime] = None,
        file_type: Optional[str] = None
    ) -> List[Dict]:
        """
        List files modified after a given datetime
        
        Args:
            since: Datetime to filter from (optional)
            file_type: Filter by file type
            
        Returns:
            List of new/modified files
        """
        files = self.list_files(file_type=file_type)
        
        if since is None:
            return files
        
        # Filter by modified date
        filtered = []
        for f in files:
            modified = datetime.fromisoformat(
                f['modifiedTime'].replace('Z', '+00:00')
            )
            if modified > since:
                filtered.append(f)
        
        logger.info(f"Found {len(filtered)} files modified after {since}")
        return filtered
    
    def download_file(
        self,
        file_id: str,
        destination: Optional[str] = None
    ) -> str:
        """
        Download a single file
        
        Args:
            file_id: Google Drive file ID
            destination: Local destination path (optional)
            
        Returns:
            Local file path
        """
        try:
            # Get file metadata
            file = self.service.files().get(fileId=file_id).execute()
            filename = file['name']
            
            # Determine destination
            if destination is None:
                destination = os.path.join(self.local_path, filename)
            
            # Download
            request = self.service.files().get_media(fileId=file_id)
            fh = io.FileIO(destination, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            progress = 0
            while not done:
                status, done = downloader.next_chunk()
                new_progress = int(status.progress() * 100)
                if new_progress > progress:
                    logger.debug(f"Download progress: {new_progress}%")
                    progress = new_progress
            
            logger.info(f"Downloaded: {filename} -> {destination}")
            return destination
            
        except HttpError as e:
            logger.error(f"Download failed: {e}")
            raise DownloadError(f"Download file failed: {e}")
    
    def download_files(
        self,
        file_ids: List[str],
        destinations: Optional[List[str]] = None
    ) -> List[str]:
        """
        Download multiple files
        
        Args:
            file_ids: List of file IDs
            destinations: Optional list of destinations
            
        Returns:
            List of local file paths
        """
        paths = []
        
        for i, file_id in enumerate(file_ids):
            dest = destinations[i] if destinations else None
            path = self.download_file(file_id, dest)
            paths.append(path)
        
        logger.info(f"Downloaded {len(paths)} files")
        return paths
    
    def download_latest_by_pattern(
        self,
        name_pattern: str,
        folder_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Download the latest file matching a pattern
        
        Args:
            name_pattern: Filename pattern (e.g., 'sales_*.csv')
            folder_id: Override folder ID
            
        Returns:
            Local file path or None
        """
        import fnmatch
        
        # List files
        parent_id = folder_id or self.folder_id
        files = self.list_files()
        
        # Filter by pattern
        matching = [f for f in files if fnmatch.fnmatch(f['name'], name_pattern)]
        
        if not matching:
            logger.warning(f"No files matching pattern: {name_pattern}")
            return None
        
        # Sort by modified time
        matching.sort(key=lambda x: x['modifiedTime'], reverse=True)
        
        # Download latest
        latest = matching[0]
        return self.download_file(latest['id'])
```

## Databricks Writer

```python
# src/ingestion/databricks_writer.py
"""
Write data from files to Databricks Delta Lake
"""
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Union
from pathlib import Path

import pandas as pd
from databricks import sql
from databricks.sdk import WorkspaceClient

from src.utils.logging_config import get_logger
from src.utils.exceptions import DatabricksWriteError

logger = get_logger(__name__)


class DatabricksWriter:
    """Write data to Databricks Delta Lake"""
    
    def __init__(
        self,
        host: str,
        token: str,
        http_path: str,
        target_catalog: str = 'data_platform',
        target_schema: str = 'bronze'
    ):
        """
        Initialize Databricks writer
        
        Args:
            host: Databricks host URL
            token: Databricks personal access token
            http_path: SQL warehouse HTTP path
            target_catalog: Target catalog name
            target_schema: Target schema name
        """
        self.host = host
        self.token = token
        self.http_path = http_path
        self.catalog = target_catalog
        self.schema = target_schema
        
        # Test connection
        self._test_connection()
        
        logger.info(f"DatabricksWriter initialized for {catalog}.{schema}")
    
    def _test_connection(self):
        """Test Databricks connection"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchall()
            logger.debug("Databricks connection OK")
        except Exception as e:
            logger.error(f"Databricks connection failed: {e}")
            raise DatabricksWriteError(f"Connection test failed: {e}")
    
    def _get_connection(self):
        """Get Databricks connection"""
        return sql.connect(
            host=self.host,
            token=self.token,
            http_path=self.http_path,
            timeout=60
        )
    
    def _infer_table_name(self, file_path: str) -> str:
        """Infer table name from file path"""
        filename = os.path.basename(file_path)
        name = os.path.splitext(filename)[0]
        # Clean and lowercase
        name = name.lower().replace(' ', '_').replace('-', '_')
        return name
    
    def _infer_schema(self, df: pd.DataFrame) -> Dict:
        """Infer schema from DataFrame"""
        schema = {}
        for col, dtype in df.dtypes.items():
            if 'int' in str(dtype):
                schema[col] = 'BIGINT'
            elif 'float' in str(dtype):
                schema[col] = 'DOUBLE'
            elif 'bool' in str(dtype):
                schema[col] = 'BOOLEAN'
            elif 'datetime' in str(dtype) or 'date' in str(dtype):
                schema[col] = 'TIMESTAMP'
            else:
                schema[col] = 'STRING'
        return schema
    
    def read_file(self, file_path: str) -> pd.DataFrame:
        """
        Read file into DataFrame
        
        Args:
            file_path: Path to file
            
        Returns:
            DataFrame
        """
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if suffix == '.csv':
            return pd.read_csv(file_path)
        elif suffix in ['.xlsx', '.xls']:
            return pd.read_excel(file_path)
        elif suffix == '.json':
            return pd.read_json(file_path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
    
    def write_to_bronze(
        self,
        file_path: str,
        table_name: Optional[str] = None,
        mode: str = 'append',
        add_metadata: bool = True
    ) -> Dict:
        """
        Write file to Bronze layer
        
        Args:
            file_path: Path to source file
            table_name: Target table name (optional, inferred from filename)
            mode: Write mode ('append', 'overwrite', 'merge')
            add_metadata: Add ETL metadata columns
            
        Returns:
            Result dict with row count and table name
        """
        try:
            # Read file
            logger.info(f"Reading file: {file_path}")
            df = self.read_file(file_path)
            
            # Get table name
            if table_name is None:
                table_name = self._infer_table_name(file_path)
            
            # Add metadata columns
            if add_metadata:
                df['_file_name'] = os.path.basename(file_path)
                df['_etl_loaded_at'] = datetime.now()
                df['_etl_batch_id'] = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            logger.info(f"Loaded {len(df)} rows, writing to {table_name}")
            
            # Write to Databricks
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Convert DataFrame to SQL
                    table_full = f"{self.catalog}.{self.schema}.{table_name}"
                    
                    # For small datasets, use INSERT VALUES
                    if len(df) < 10000:
                        self._insert_values(cursor, df, table_full, mode)
                    else:
                        # For large datasets, use Spark (via API)
                        self._spark_insert(cursor, df, table_full, mode)
            
            result = {
                'table': table_full,
                'rows': len(df),
                'status': 'success'
            }
            
            logger.info(f"Written {len(df)} rows to {table_full}")
            return result
            
        except Exception as e:
            logger.error(f"Write to Bronze failed: {e}")
            raise DatabricksWriteError(f"Write failed: {e}")
    
    def _insert_values(
        self,
        cursor,
        df: pd.DataFrame,
        table: str,
        mode: str
    ):
        """Insert values using SQL"""
        # Build INSERT statement
        columns = ', '.join(df.columns)
        placeholders = ', '.join(['?' for _ in df.columns])
        
        if mode == 'overwrite':
            cursor.execute(f"DELETE FROM {table}")
        
        # Insert in batches
        batch_size = 1000
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            values = [
                tuple(row) for row in batch.values
            ]
            
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            cursor.executemany(sql, values)
    
    def _spark_insert(
        self,
        cursor,
        df: pd.DataFrame,
        table: str,
        mode: str
    ):
        """Insert using Spark DataFrame"""
        # For large datasets, use Databricks REST API with Spark
        # This is a placeholder - implement based on your setup
        raise NotImplementedError(
            "Large dataset insertion requires Spark setup"
        )
    
    def write_files_to_bronze(
        self,
        file_paths: List[str],
        mode: str = 'append'
    ) -> List[Dict]:
        """
        Write multiple files to Bronze layer
        
        Args:
            file_paths: List of file paths
            mode: Write mode
            
        Returns:
            List of result dicts
        """
        results = []
        
        for file_path in file_paths:
            try:
                result = self.write_to_bronze(file_path, mode=mode)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to write {file_path}: {e}")
                results.append({
                    'file': file_path,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
    
    def validate_table(self, table_name: str) -> Dict:
        """
        Validate table after write
        
        Args:
            table_name: Table name to validate
            
        Returns:
            Validation result dict
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    
                    # Column list
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = cursor.fetchall()
                    
                    return {
                        'table': table_name,
                        'row_count': row_count,
                        'column_count': len(columns),
                        'status': 'valid'
                    }
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                'table': table_name,
                'status': 'invalid',
                'error': str(e)
            }
```

## Usage Example

```python
# examples/ingestion_example.py
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from src.ingestion.google_drive_sync import GoogleDriveSync
from src.ingestion.databricks_writer import DatabricksWriter

# Load environment
load_dotenv()

def main():
    """Main ingestion flow"""
    
    # Initialize clients
    gdrive = GoogleDriveSync(
        credentials_path=os.environ.get('GOOGLE_DRIVE_CREDENTIALS_PATH'),
        folder_id=os.environ.get('GOOGLE_DRIVE_FOLDER_ID'),
        local_download_path='./data/raw'
    )
    
    writer = DatabricksWriter(
        host=os.environ.get('DATABRICKS_HOST'),
        token=os.environ.get('DATABRICKS_TOKEN'),
        http_path=os.environ.get('DATABRICKS_HTTP_PATH')
    )
    
    # Check for new files (last 24 hours)
    yesterday = datetime.now() - timedelta(days=1)
    new_files = gdrive.list_files_modified_after(since=yesterday, file_type='csv')
    
    if not new_files:
        print("No new files found")
        return
    
    # Download files
    local_paths = []
    for f in new_files:
        path = gdrive.download_file(f['id'])
        local_paths.append(path)
    
    # Write to Databricks
    results = writer.write_files_to_bronze(local_paths, mode='append')
    
    # Validate
    for result in results:
        if result.get('status') == 'success':
            validation = writer.validate_table(result['table'])
            print(f"✅ {result['table']}: {validation['row_count']} rows")
        else:
            print(f"❌ {result.get('file')}: {result.get('error')}")

if __name__ == '__main__':
    main()
```

## Error Handling

```python
# src/utils/exceptions.py
class DataPlatformError(Exception):
    """Base exception for data platform"""
    pass

class GoogleDriveError(DataPlatformError):
    """Google Drive related errors"""
    pass

class DatabricksWriteError(DataPlatformError):
    """Databricks write errors"""
    pass

class FileNotFoundError(DataPlatformError):
    """File not found errors"""
    pass

class DownloadError(DataPlatformError):
    """Download errors"""
    pass

class ValidationError(DataPlatformError):
    """Data validation errors"""
    pass
```

## Related Documentation

- [Google Drive Setup](../setup/google-drive-setup.md)
- [Databricks Setup](../setup/databricks-setup.md)
- [Logging Architecture](../logging/architecture.md)
