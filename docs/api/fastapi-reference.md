# FastAPI Reference

## Overview

API reference cho FastAPI endpoints của Data Platform.

## Setup

```bash
# Install dependencies
pip install fastapi uvicorn pydantic python-dotenv

# Run server
uvicorn src.api.main:app --reload --port 8000

# Or with Docker
docker-compose up api
```

## Base Configuration

```python
# src/api/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings"""
    
    # App
    app_name: str = "Data Platform API"
    debug: bool = False
    
    # Databricks
    databricks_host: str
    databricks_token: str
    databricks_http_path: str
    
    # Database
    database_url: str = "postgresql://user:pass@localhost:5432/db"
    
    # Security
    secret_key: str
    api_key_header: str = "X-API-Key"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

## Main Application

```python
# src/api/main.py
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from src.api.config import get_settings
from src.api.routes import (
    health,
    ingestion,
    transformation,
    analytics
)

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting API server...")
    yield
    logger.info("Shutting down API server...")


app = FastAPI(
    title=settings.app_name,
    description="Data Platform REST API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(transformation.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs"
    }
```

## Health Endpoints

```python
# src/api/routes/health.py
from fastapi import APIRouter, status
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str


@router.get("", response_model=HealthResponse)
async def health_check():
    """Basic health check"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0"
    )


@router.get("/ready")
async def readiness_check():
    """Readiness check (includes dependencies)"""
    checks = {
        "databricks": check_databricks(),
        "database": check_database(),
    }
    
    all_healthy = all(checks.values())
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks
    }


def check_databricks() -> bool:
    """Check Databricks connection"""
    try:
        from databricks import sql
        # Simplified check
        return True
    except:
        return False

def check_database() -> bool:
    """Check database connection"""
    try:
        # Simplified check
        return True
    except:
        return False
```

## Ingestion Endpoints

```python
# src/api/routes/ingestion.py
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from src.api.auth import verify_api_key
from src.api.schemas import (
    FileInfo,
    IngestionRequest,
    IngestionResponse,
    JobStatus
)

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])
logger = logging.getLogger(__name__)


class FileListResponse(BaseModel):
    files: List[FileInfo]
    count: int


@router.get("/files", response_model=FileListResponse)
async def list_files(
    file_type: Optional[str] = None,
    limit: int = 100,
    api_key: str = Depends(verify_api_key)
):
    """List available files in Google Drive"""
    try:
        from src.ingestion.google_drive_sync import GoogleDriveSync
        
        gdrive = GoogleDriveSync(
            credentials_path="path/to/credentials.json",
            folder_id="folder-id"
        )
        
        files = gdrive.list_files(file_type=file_type, limit=limit)
        
        return FileListResponse(
            files=[FileInfo(**f) for f in files],
            count=len(files)
        )
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest", response_model=IngestionResponse)
async def trigger_ingestion(
    request: IngestionRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Trigger data ingestion"""
    job_id = f"ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Run in background
    background_tasks.add_task(
        run_ingestion,
        job_id=job_id,
        file_ids=request.file_ids
    )
    
    return IngestionResponse(
        job_id=job_id,
        status="started",
        message="Ingestion job started"
    )


async def run_ingestion(job_id: str, file_ids: List[str]):
    """Background ingestion task"""
    logger.info(f"Starting ingestion job: {job_id}")
    # ... ingestion logic
    logger.info(f"Completed ingestion job: {job_id}")


@router.get("/status/{job_id}", response_model=JobStatus)
async def get_ingestion_status(job_id: str):
    """Get ingestion job status"""
    # In production, query from database
    return JobStatus(
        job_id=job_id,
        status="completed",
        progress=100,
        rows_ingested=1000,
        started_at=datetime.now(),
        completed_at=datetime.now()
    )
```

## Transformation Endpoints

```python
# src/api/routes/transformation.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

router = APIRouter(prefix="/transformation", tags=["Transformation"])
logger = logging.getLogger(__name__)


class DbtRunRequest(BaseModel):
    target: str = "dev"
    select: Optional[str] = None  # dbt select pattern
    full_refresh: bool = False


class DbtRunResponse(BaseModel):
    job_id: str
    status: str
    message: str


@router.post("/run", response_model=DbtRunResponse)
async def trigger_dbt_run(
    request: DbtRunRequest,
    background_tasks: BackgroundTasks
):
    """Trigger dbt transformation run"""
    job_id = f"dbt_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    background_tasks.add_task(
        run_dbt_transformation,
        job_id=job_id,
        target=request.target,
        select=request.select,
        full_refresh=request.full_refresh
    )
    
    return DbtRunResponse(
        job_id=job_id,
        status="started",
        message=f"dbt run started with target: {request.target}"
    )


async def run_dbt_transformation(
    job_id: str,
    target: str,
    select: Optional[str],
    full_refresh: bool
):
    """Background dbt run task"""
    import subprocess
    import os
    
    logger.info(f"Starting dbt run: {job_id}")
    
    cmd = ["dbt", "run", "--target", target]
    if select:
        cmd.extend(["--select", select])
    if full_refresh:
        cmd.append("--full-refresh")
    
    result = subprocess.run(
        cmd,
        cwd="/path/to/dbt/project",
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        logger.error(f"dbt run failed: {result.stderr}")
    else:
        logger.info(f"dbt run completed: {job_id}")


@router.get("/status/{job_id}")
async def get_transformation_status(job_id: str):
    """Get transformation job status"""
    # In production, query from database
    return {
        "job_id": job_id,
        "status": "completed",
        "models_run": 25,
        "models_failed": 0,
        "duration_seconds": 120
    }
```

## Analytics Endpoints

```python
# src/api/routes/analytics.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import logging

router = APIRouter(prefix="/analytics", tags=["Analytics"])
logger = logging.getLogger(__name__)


class MetricResponse(BaseModel):
    metric: str
    value: float
    unit: str
    period: str


class SalesSummary(BaseModel):
    total_revenue: float
    total_orders: int
    avg_order_value: float
    top_products: List[Dict[str, Any]]


@router.get("/metrics/summary", response_model=SalesSummary)
async def get_sales_summary(
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    region: Optional[str] = None
):
    """Get sales summary metrics"""
    try:
        from databricks import sql
        import os
        
        conn = sql.connect(
            host=os.environ.get('DATABRICKS_HOST'),
            token=os.environ.get('DATABRICKS_TOKEN'),
            http_path=os.environ.get('DATABRICKS_HTTP_PATH')
        )
        
        with conn.cursor() as cursor:
            query = f"""
                SELECT
                    SUM(net_revenue) AS total_revenue,
                    COUNT(DISTINCT order_id) AS total_orders,
                    AVG(net_revenue) AS avg_order_value
                FROM data_platform.gold.fct_orders
                WHERE order_date BETWEEN '{start_date}' AND '{end_date}'
            """
            
            if region:
                query += f" AND region = '{region}'"
            
            cursor.execute(query)
            result = cursor.fetchone()
            
            return SalesSummary(
                total_revenue=result[0] or 0,
                total_orders=result[1] or 0,
                avg_order_value=result[2] or 0,
                top_products=[]
            )
    except Exception as e:
        logger.error(f"Failed to get sales summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/kpis")
async def get_kpis():
    """Get key performance indicators"""
    return {
        "kpis": [
            {"name": "Total Revenue", "value": 1500000, "change": 5.2},
            {"name": "Active Customers", "value": 12500, "change": 3.1},
            {"name": "Average Order Value", "value": 85.50, "change": 2.8},
            {"name": "Conversion Rate", "value": 3.5, "change": -0.2}
        ],
        "generated_at": datetime.now().isoformat()
    }


@router.get("/trends/revenue")
async def get_revenue_trends(
    period: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    months: int = Query(12, ge=1, le=24)
):
    """Get revenue trends"""
    # Example response structure
    return {
        "period": period,
        "data": [
            {"date": "2024-01-01", "revenue": 50000},
            {"date": "2024-01-02", "revenue": 55000},
            # ... more data
        ]
    }
```

## Authentication

```python
# src/api/auth.py
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
import hashlib
import os

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# In production, store in database
VALID_API_KEYS = {
    "key-001": {"name": "admin", "role": "admin"},
    "key-002": {"name": "readonly", "role": "readonly"},
}


async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key"""
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Missing API key"
        )
    
    if api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return VALID_API_KEYS[api_key]
```

## Schemas

```python
# src/api/schemas.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class FileInfo(BaseModel):
    id: str
    name: str
    mimeType: str
    size: str
    createdTime: str
    modifiedTime: str


class IngestionRequest(BaseModel):
    file_ids: List[str]
    target_schema: str = "bronze"


class IngestionResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    rows_ingested: int
    started_at: datetime
    completed_at: Optional[datetime] = None


class ErrorResponse(BaseModel):
    error: str
    detail: str
    timestamp: datetime
```

## API Documentation

Sau khi chạy server, API documentation có sẵn tại:

| URL | Description |
|-----|-------------|
| http://localhost:8000/docs | Swagger UI (Recommended) |
| http://localhost:8000/redoc | ReDoc alternative |
| http://localhost:8000/openapi.json | OpenAPI JSON spec |

## Related Documentation

- [Ingestion Pipeline](../pipelines/ingestion-guide.md)
- [Transformation Pipeline](../pipelines/transformation-guide.md)
