# Logging Setup Guide

## Overview

Hướng dẫn setup logging system cho Data Platform - dùng Loguru + Loki (Mac-friendly).

## Quick Setup

### Step 1: Install Dependencies

```bash
pip install loguru python-json-logger structlog
```

### Step 2: Basic Configuration

```python
# src/utils/logging_config.py
"""
Central logging configuration for Data Platform
"""
import sys
import logging
from pathlib import Path
from datetime import datetime

from loguru import logger


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "./logs",
    enable_console: bool = True,
    enable_file: bool = True,
    enable_json: bool = False
) -> None:
    """
    Setup logging configuration for the application
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        enable_console: Enable console output
        enable_file: Enable file output
        enable_json: Enable JSON format for production
    """
    
    # Remove default handler
    logger.remove()
    
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Console format
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # File format (with more details)
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # JSON format (for production)
    json_format = (
        '{"timestamp": "{time:YYYY-MM-DDTHH:mm:ss.SSSZ}", '
        '"level": "{level}", '
        '"logger": "{name}", '
        '"function": "{function}", '
        '"line": "{line}", '
        '"message": "{message}"}'
    )
    
    # Console handler
    if enable_console:
        logger.add(
            sys.stdout,
            format=console_format,
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=True
        )
    
    # File handlers with rotation
    today = datetime.now().strftime('%Y%m%d')
    log_file = log_path / f"data_platform_{today}.log"
    
    if enable_file:
        # Main log file (rotating)
        logger.add(
            log_file,
            format=file_format,
            level=log_level,
            rotation="00:00",  # Rotate at midnight
            retention="30 days",  # Keep for 30 days
            compression="zip",  # Compress old logs
            backtrace=True,
            diagnose=True,
            enqueue=True  # Thread-safe
        )
        
        # Error log file
        error_file = log_path / f"errors_{today}.log"
        logger.add(
            error_file,
            format=file_format,
            level="ERROR",
            rotation="00:00",
            retention="90 days",
            compression="zip",
            backtrace=True,
            diagnose=True,
            enqueue=True
        )
    
    # JSON file for production/ELK
    if enable_json:
        json_file = log_path / f"data_platform_{today}.json"
        logger.add(
            json_file,
            format=json_format,
            level=log_level,
            rotation="00:00",
            retention="30 days",
            compression="zip",
            serialize=True,  # Already JSON format
            enqueue=True
        )
    
    logger.info(f"Logging configured: level={log_level}, dir={log_dir}")


def get_logger(name: str = None):
    """
    Get a logger instance
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Loguru logger instance
    """
    if name:
        return logger.bind(name=name.split('.')[-1])
    return logger


# Default logger
logger = get_logger(__name__)
```

### Step 3: Usage in Application

```python
# src/ingestion/example.py
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class DataIngestion:
    """Example class with logging"""
    
    def __init__(self):
        self.logger = logger.bind(class_name="DataIngestion")
    
    def run(self):
        self.logger.info("Starting data ingestion")
        
        try:
            files = self.fetch_files()
            self.logger.info(f"Found {len(files)} files", files=files)
            
            for file in files:
                self.process_file(file)
                self.logger.debug(f"Processed file: {file}")
            
            self.logger.info("Ingestion completed successfully")
            
        except Exception as e:
            self.logger.error(f"Ingestion failed: {e}", exc_info=True)
            raise


# Usage
ingestion = DataIngestion()
ingestion.run()
```

## Advanced Configuration

### Loguru with Context

```python
# src/utils/context_logging.py
"""
Context-aware logging with request tracking
"""
from contextvars import ContextVar
from loguru import logger
from uuid import uuid4
from functools import wraps
import time

# Context variables
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')

# Extra context for every log
def add_context(logger, message, kwargs):
    kwargs['extra'] = {
        'request_id': request_id_var.get(),
        'user_id': user_id_var.get(),
    }
    return message, kwargs

# Configure logger
logger.configure(
    processors=[add_context],
    extra={'request_id': '', 'user_id': ''}
)


def log_execution_time(func):
    """Decorator to log function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        logger.info(f"Starting {func.__name__}")
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            logger.info(
                f"Completed {func.__name__}",
                duration_ms=int(duration * 1000)
            )
            return result
        except Exception as e:
            duration = time.time() - start
            logger.error(
                f"Failed {func.__name__}",
                duration_ms=int(duration * 1000),
                error=str(e)
            )
            raise
    return wrapper


def set_request_context(request_id: str = None, user_id: str = None):
    """Set context for current request"""
    if request_id:
        request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


# Usage example
@log_execution_time
def my_function(param1, param2):
    set_request_context(request_id=str(uuid4()), user_id="user123")
    logger.info("Processing request", param1=param1)
    # ... do work
    return result
```

### Structured Logging with structlog

```python
# src/utils/structlog_config.py
"""
Structured logging using structlog
"""
import structlog
import logging
from datetime import datetime


def configure_structlog(log_level: str = "INFO"):
    """Configure structlog for structured JSON logging"""
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper())
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_struct_logger(name: str = None):
    """Get a structured logger"""
    return structlog.get_logger(name)


# Usage
# log = get_struct_logger(__name__)
# log.info("event", key="value", count=42)
```

## File Rotation Configuration

```python
# logs/log_rotation.py
from loguru import logger
from datetime import datetime

# Rotation policies
logger.add(
    "app_{time}.log",
    rotation="500 MB",  # Rotate when file reaches 500MB
    retention="7 days",  # Keep for 7 days
    compression="zip"  # Compress old logs
)

logger.add(
    "app_{time}.log",
    rotation="12:00",  # Rotate at noon daily
    retention="30 days",
    compression="zip"
)

logger.add(
    "app_{time}.log",
    rotation="1 week",  # Rotate weekly
    retention="12 months",
    compression="zip"
)

# Size-based with count
logger.add(
    "app_{time}.log",
    rotation="100 MB",
    retention=10,  # Keep 10 files
    compression="zip"
)
```

## Environment-based Configuration

```python
# src/utils/logging_factory.py
"""
Factory function to create logging config based on environment
"""
import os
from loguru import logger


def create_logging_config():
    """Create logging configuration based on environment"""
    
    env = os.environ.get('ENVIRONMENT', 'development')
    
    config = {
        'development': {
            'level': 'DEBUG',
            'enable_console': True,
            'enable_file': True,
            'enable_json': False,
            'log_dir': './logs'
        },
        'production': {
            'level': 'INFO',
            'enable_console': False,
            'enable_file': True,
            'enable_json': True,
            'log_dir': '/var/log/data-platform'
        },
        'testing': {
            'level': 'DEBUG',
            'enable_console': True,
            'enable_file': False,
            'enable_json': False,
            'log_dir': '/tmp/test_logs'
        }
    }
    
    return config.get(env, config['development'])


# In main.py or app initialization
from src.utils.logging_config import setup_logging

config = create_logging_config()
setup_logging(**config)
```

## Docker Logging

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    image: data-platform:latest
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    volumes:
      - ./logs:/app/logs
```

```yaml
# docker-compose.yml - With Loki
services:
  app:
    image: data-platform:latest
    logging:
      driver: loki
      options:
        loki-url: "http://loki:3100/loki/api/v1/push"
        loki-retries: "3"
        loki-batch-size: "400"
```

## Environment Variables

```bash
# .env
LOG_LEVEL=INFO
LOG_DIR=./logs
LOG_ENABLE_JSON=false
LOG_ENABLE_CONSOLE=true
LOG_RETENTION_DAYS=30
```

## Testing Logging

```python
# tests/test_logging.py
import pytest
from loguru import logger
from io import StringIO


def test_log_level():
    """Test that log levels work correctly"""
    log_output = StringIO()
    logger.add(log_output, format="{message}")
    
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    
    output = log_output.getvalue()
    
    assert "debug message" not in output  # DEBUG is below INFO
    assert "info message" in output
    assert "warning message" in output
    assert "error message" in output


def test_log_context():
    """Test that context is added to logs"""
    # This would test that request_id, etc. are logged
    pass
```

## Related Documentation

- [Logging Architecture](./architecture.md)
- [Log Analysis Guide](./log-analysis.md)
- [ADR-003 Logging System](./003-logging-system.md)
