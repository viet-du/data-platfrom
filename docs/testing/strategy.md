# Testing Strategy

## Overview

Chiến lược testing cho Data Platform để đảm bảo chất lượng dữ liệu và code.

## Testing Pyramid

```
                    ┌─────────────┐
                    │    E2E     │  Few, slow
                    │   Tests    │  Critical paths
                   ─┴─────────────┴─
                  ┌─────────────────┐
                  │   Integration   │  More, medium
                  │     Tests      │  System interactions
                 ─┴─────────────────┴─
                ┌───────────────────────┐
                │      Unit Tests       │  Many, fast
                │  (Code + Data)        │
               ─┴───────────────────────┴─
```

## Test Categories

### 1. Unit Tests

#### Python Unit Tests

```python
# tests/unit/test_google_drive_sync.py
import pytest
from unittest.mock import Mock, patch
from src.ingestion.google_drive_sync import GoogleDriveSync


class TestGoogleDriveSync:
    """Unit tests for Google Drive sync"""
    
    @pytest.fixture
    def mock_credentials(self, tmp_path):
        """Create mock credentials file"""
        creds = {
            "type": "service_account",
            "client_email": "test@test.iam.gserviceaccount.com",
            "private_key": "fake_key"
        }
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))
        return str(creds_file)
    
    @patch('src.ingestion.google_drive_sync.build')
    def test_list_files_returns_list(self, mock_build, mock_credentials):
        """Test that list_files returns a list"""
        # Setup
        mock_build.return_value.files.return_value.list.return_value.execute.return_value = {
            'files': [
                {'id': '1', 'name': 'test.csv'}
            ]
        }
        
        # Execute
        client = GoogleDriveSync(
            credentials_path=mock_credentials,
            folder_id='test-folder'
        )
        files = client.list_files()
        
        # Assert
        assert isinstance(files, list)
        assert len(files) == 1
        assert files[0]['name'] == 'test.csv'
    
    @patch('src.ingestion.google_drive_sync.build')
    def test_download_file_creates_local_file(self, mock_build, tmp_path, mock_credentials):
        """Test that download_file creates a local file"""
        # Setup
        mock_build.return_value.files.return_value.get.return_value.execute.return_value = {
            'name': 'test.csv'
        }
        mock_build.return_value.files.return_value.get_media.return_value.next_chunk = Mock(
            return_value=(Mock(progress=1.0), True)
        )
        
        # Execute
        client = GoogleDriveSync(
            credentials_path=mock_credentials,
            folder_id='test-folder',
            local_download_path=str(tmp_path)
        )
        dest = tmp_path / 'downloaded.csv'
        result = client.download_file('file-id', str(dest))
        
        # Assert
        assert os.path.exists(result)
```

#### dbt Unit Tests

```yaml
# models/_schema.yml
version: 2

models:
  - name: dim_customers
    columns:
      - name: customer_id
        tests:
          - not_null
          - unique
      - name: lifetime_value
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min: 0
```

### 2. Data Quality Tests (Great Expectations)

```python
# tests/data_quality/test_sales_data.py
import great_expectations as gx
import pytest


class TestSalesDataQuality:
    """Data quality tests for sales data"""
    
    @pytest.fixture
    def context(self):
        """Create Great Expectations context"""
        return gx.get_context()
    
    @pytest.fixture
    def sales_suite(self, context):
        """Create expectation suite for sales data"""
        suite = context.add_or_update_expectation_suite(
            expectation_suite_name="sales_data_quality"
        )
        return suite
    
    def test_no_null_ids(self, context, sales_suite):
        """Test that order_id has no nulls"""
        expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
            column="order_id"
        )
        sales_suite.add_expectation(expectation)
    
    def test_revenue_positive(self, context, sales_suite):
        """Test that revenue is always positive"""
        expectation = gx.expectations.ExpectColumnValuesToBeBetween(
            column="net_revenue",
            min_value=0,
            max_value=None
        )
        sales_suite.add_expectation(expectation)
    
    def test_date_not_in_future(self, context, sales_suite):
        """Test that order dates are not in the future"""
        expectation = gx.expectations.ExpectColumnValuesToBeInSet(
            column="order_date",
            value_set=[
                "2024-01-15",
                "2024-01-16"
            ]
        )
        sales_suite.add_expectation(expectation)
```

### 3. Integration Tests

```python
# tests/integration/test_databricks_connection.py
import pytest
import os
from databricks import sql


class TestDatabricksConnection:
    """Integration tests for Databricks connection"""
    
    @pytest.fixture
    def connection(self):
        """Create Databricks connection"""
        conn = sql.connect(
            host=os.environ.get('DATABRICKS_HOST'),
            token=os.environ.get('DATABRICKS_TOKEN'),
            http_path=os.environ.get('DATABRICKS_HTTP_PATH')
        )
        yield conn
        conn.close()
    
    def test_connection_works(self, connection):
        """Test that connection is successful"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
    
    def test_table_exists(self, connection):
        """Test that expected tables exist"""
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES FROM data_platform.gold")
            tables = cursor.fetchall()
            table_names = [t[1] for t in tables]
            assert 'fct_orders' in table_names
    
    def test_query_returns_data(self, connection):
        """Test that query returns data"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM data_platform.gold.fct_orders")
            count = cursor.fetchone()[0]
            assert count >= 0
```

### 4. End-to-End Tests

```python
# tests/e2e/test_ingestion_pipeline.py
import pytest
import os
from datetime import datetime


class TestIngestionPipeline:
    """End-to-end tests for ingestion pipeline"""
    
    @pytest.fixture
    def pipeline(self):
        """Create pipeline instance"""
        from src.ingestion.batch_ingestion import BatchIngestionPipeline
        return BatchIngestionPipeline(config={
            'credentials_path': os.environ.get('GOOGLE_DRIVE_CREDENTIALS_PATH'),
            'folder_id': os.environ.get('GOOGLE_DRIVE_FOLDER_ID'),
            'databricks_host': os.environ.get('DATABRICKS_HOST'),
            'databricks_token': os.environ.get('DATABRICKS_TOKEN'),
            'http_path': os.environ.get('DATABRICKS_HTTP_PATH')
        })
    
    def test_full_ingestion_run(self, pipeline):
        """Test complete ingestion flow"""
        # Run pipeline
        result = pipeline.run(date=datetime.now())
        
        # Assert success
        assert result['status'] == 'success'
        
        # Assert data was ingested
        assert result['files_processed'] > 0
        assert result['rows_ingested'] > 0
    
    def test_pipeline_handles_no_files(self, pipeline):
        """Test pipeline handles no new files gracefully"""
        # Run with a date in the future (no files)
        result = pipeline.run(date=datetime(2099, 1, 1))
        
        # Should succeed with no files
        assert result['status'] == 'success'
        assert result['message'] == 'No new files'
```

## Test Fixtures

```python
# tests/conftest.py
import pytest
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@pytest.fixture(scope='session')
def databricks_config():
    """Databricks configuration"""
    return {
        'host': os.environ.get('DATABRICKS_HOST'),
        'token': os.environ.get('DATABRICKS_TOKEN'),
        'http_path': os.environ.get('DATABRICKS_HTTP_PATH')
    }


@pytest.fixture(scope='session')
def google_drive_config():
    """Google Drive configuration"""
    return {
        'credentials_path': os.environ.get('GOOGLE_DRIVE_CREDENTIALS_PATH'),
        'folder_id': os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
    }


@pytest.fixture
def sample_dataframe():
    """Sample DataFrame for testing"""
    import pandas as pd
    return pd.DataFrame({
        'order_id': ['A001', 'A002', 'A003'],
        'customer_id': ['C001', 'C002', 'C003'],
        'amount': [100.0, 200.0, 300.0],
        'date': ['2024-01-15', '2024-01-16', '2024-01-17']
    })
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_google_drive_sync.py

# Run specific test class
pytest tests/unit/test_google_drive_sync.py::TestGoogleDriveSync

# Run with coverage
pytest --cov=src --cov-report=html

# Run dbt tests
cd data_platform_dbt
dbt test

# Run with tags
pytest -m "not slow"

# Run integration tests only
pytest -m integration
```

## CI/CD Testing

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
          
      - name: Run unit tests
        run: pytest tests/unit -v
        
      - name: Run integration tests
        run: pytest tests/integration -v
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
          
      - name: Run dbt tests
        run: |
          cd data_platform_dbt
          dbt test
          
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Test Coverage Targets

| Test Type | Coverage Target | Max Runtime |
|-----------|----------------|-------------|
| Unit Tests | 80% | < 5 min |
| Data Quality | 100% key columns | < 10 min |
| Integration | 100% critical paths | < 30 min |
| E2E | 5 core scenarios | < 60 min |

## Related Documentation

- [dbt Modeling Guide](../tools/dbt-modeling-guide.md)
- [Transformation Pipeline](../pipelines/transformation-guide.md)
- [Troubleshooting Guide](../runbooks/troubleshooting.md)
