# Logging Architecture

## Overview

Kiến trúc logging hệ thống cho Data Platform - giúp debug và track issues khi chạy agent.

## Logging Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LOGGING ARCHITECTURE                               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    PYTHON APPLICATION LAYER                           │  │
│  │                                                                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │  │
│  │  │ Ingestion   │  │Transform   │  │   API      │                 │  │
│  │  │   Script    │  │  (dbt)     │  │  Server    │                 │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │  │
│  │         │                │                │                         │  │
│  │         └────────────────┼────────────────┘                         │  │
│  │                          ▼                                            │  │
│  │  ┌───────────────────────────────────────────────────────────────┐  │  │
│  │  │                    Python Logging + Loguru                    │  │  │
│  │  │  - Structured JSON logs                                       │  │  │
│  │  │  - Contextual information (request_id, user_id, etc.)         │  │  │
│  │  │  - Automatic exception handling                                │  │  │
│  │  └───────────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                       LOG TRANSPORT LAYER                           │  │
│  │                                                                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │  │
│  │  │   Console   │  │    File    │  │   Network  │                 │  │
│  │  │  (stdout)   │  │  (rotated) │  │  (syslog)  │                 │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      LOG STORAGE LAYER                              │  │
│  │                                                                       │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │                    ELASTICSEARCH / LOKI                      │  │  │
│  │  │  - Full-text search                                           │  │  │
│  │  │  - Time-based indexing                                        │  │  │
│  │  │  - Scalable storage                                           │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    LOG VISUALIZATION LAYER                          │  │
│  │                                                                       │  │
│  │  ┌─────────────────┐                ┌─────────────────┐            │  │
│  │  │     Kibana      │                │     Grafana     │            │  │
│  │  │ (Elasticsearch) │                │     (Loki)      │            │  │
│  │  └─────────────────┘                └─────────────────┘            │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Log Levels

| Level | Numeric | Usage | Example |
|-------|---------|-------|---------|
| **DEBUG** | 10 | Detailed debugging info | Variable values, loop iterations |
| **INFO** | 20 | Normal operation events | "Started ingestion", "File downloaded" |
| **WARNING** | 30 | Potential issues | "File not found, using default" |
| **ERROR** | 40 | Errors that need attention | "Connection failed", "Query timeout" |
| **CRITICAL** | 50 | System failures | "Database unreachable", "Out of memory" |

## Log Format

### Structured JSON Format

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "logger": "ingestion.google_drive_sync",
  "message": "Downloaded file successfully",
  "context": {
    "request_id": "req-12345",
    "file_id": "abc123",
    "file_name": "sales_2024.csv",
    "file_size": 1048576
  },
  "duration_ms": 1234
}
```

### Human-readable Format (Development)

```
2024-01-15 10:30:00 | INFO     | ingestion.google_drive_sync | Downloaded file successfully | file_name=sales_2024.csv duration_ms=1234
```

## Log Categories

| Category | Loggers | Description |
|----------|---------|-------------|
| **Ingestion** | `ingestion.*` | Data ingestion logs |
| **Transformation** | `transformation.*` | dbt transformation logs |
| **API** | `api.*` | API request/response logs |
| **Databricks** | `databricks.*` | Databricks connection logs |
| **Google Drive** | `google_drive.*` | Google Drive API logs |
| **Airflow** | `airflow.*` | Airflow task logs |
| **System** | `system.*` | System-level logs |

## Components

### 1. Loguru (Recommended for Python)

```python
# Features:
# - Zero configuration required
# - Automatic exception handling
# - Structured logging
# - Colorized output in console
# - Easy file rotation
```

### 2. structlog (Alternative)

```python
# Features:
# - Pure structured logging
# - Multiple output formats
# - Context binding
# - Processor chains
```

### 3. Python Standard Logging

```python
# Features:
# - Built-in
# - Compatible with all libraries
# - Handler hierarchy
# - Filter support
```

## Log Storage Options

| Option | Best For | Pros | Cons |
|--------|----------|------|------|
| **Local Files** | Development | Simple, no setup | No search, no scale |
| **ELK Stack** | Production | Full-text search, dashboards | Resource heavy |
| **Loki** | Production | Lightweight, Grafana native | Less feature-rich than ELK |
| **CloudWatch** | AWS | Integrated with AWS | Vendor lock-in |
| **Datadog** | Production | APM + Logs | Expensive |

## Key Design Decisions

### ADR-003: Logging System Choice

**Context:**
Cần một hệ thống logging để debug khi agent chạy, track pipeline execution, và monitor system health.

**Options Considered:**
1. Python logging (built-in) - Simple, no extra dependencies
2. Loguru - Modern, easier API, better defaults
3. structlog - Pure structured, very powerful
4. ELK Stack - Full solution for production
5. Loki + Grafana - Lightweight alternative

**Decision:**
Use **Loguru** for application logging + **Loki** for log aggregation.

**Rationale:**
- Loguru: Zero-config, beautiful output, excellent for development
- Loki: Lightweight, integrates with Grafana, easy setup
- Suitable for both local development and production

**Consequences:**
- Positive: Easy to use, good developer experience
- Positive: Structured JSON output for production
- Negative: Loki requires separate setup
- Negative: Less enterprise features than ELK

## Related Documentation

- [Logging Setup Guide](./setup-guide.md)
- [Log Analysis Guide](./log-analysis.md)
- [ADR-003 Logging System](./003-logging-system.md)
