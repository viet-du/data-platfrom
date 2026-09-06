# Tech Stack

## Overview

Danh sách đầy đủ các công nghệ sử dụng trong Data Platform.

## 🗄️ Storage Layer

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| **Google Drive** | - | Raw Data Storage (Free) | Shared Drive for CSV/Excel |
| **Databricks DBFS** | - | Delta Lake Storage | Free tier: 20GB |
| **Delta Lake** | Latest | Data Lakehouse format | ACID transactions |
| **Unity Catalog** | - | Data Governance | (If available) |

## ⚙️ Processing Layer

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| **Databricks Community Edition** | 14.x | Data Processing | Free forever, 1 cluster |
| **Apache Spark** | 3.5 | Distributed Computing | Built-in Databricks |
| **Python** | 3.11+ | Scripting | pandas, pyspark |
| **dbt-databricks** | 1.7+ | Data Transformation | SQL-based |

## 🔧 Data Integration

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| **Google Drive API** | v3 | Read/Write files | Service account |
| **Google Sheets API** | v4 | Read/Write spreadsheets | (If needed) |
| **REST API Client** | - | External APIs | requests library |

## 🎛️ Orchestration

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| **Apache Airflow** | 2.8+ | Workflow Orchestration | Local Docker |
| **Databricks Jobs** | - | Task Scheduling | Built-in |
| **Docker Compose** | 2.x | Container Management | Local dev |

## 📊 Analytics & Visualization

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| **Metabase** | Latest | Dashboard & BI | Free, Mac-friendly ⭐ |
| **SQL** | - | Query Language | Databricks SQL |
| **Matplotlib** | - | Python Charts | For scripts |
| **Plotly** | - | Interactive Charts | For scripts |

## 🌐 API Layer

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| **FastAPI** | 0.100+ | REST API | Python async |
| **Uvicorn** | - | ASGI Server | Fast, lightweight |
| **Pydantic** | 2.x | Data Validation | Type safety |
| **SQLAlchemy** | 2.x | Database ORM | (If needed) |

## 📝 Logging & Monitoring

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| **Python logging** | - | Standard logging | Built-in |
| **Loguru** | 3.x | Enhanced logging | Easier than logging |
| **structlog** | 24.x | Structured logging | JSON format |
| **ELK Stack** | 8.x | Log aggregation | Optional |
| **Loki** | - | Log aggregation | Optional, lighter |
| **Grafana** | 10.x | Metrics visualization | Optional |

## 🧪 Testing

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| **pytest** | 8.x | Unit Testing | Main test framework |
| **pytest-cov** | - | Coverage Reports | Code coverage |
| **Great Expectations** | 0.18+ | Data Validation | Data quality |
| **tox** | - | Test automation | Multiple envs |

## 🔐 Security

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| **OAuth 2.0** | - | Authentication | Google, Metabase |
| **JWT** | - | Token-based auth | API security |
| **HashiCorp Vault** | - | Secrets management | (If needed) |
| **Databricks Secrets** | - | Credentials storage | Built-in |

## 🛠️ Development Tools

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| **VS Code** | Latest | Code Editor | Recommended |
| **Git** | Latest | Version Control | Required |
| **Docker Desktop** | Latest | Containerization | Mac support |
| **Homebrew** | Latest | Package Manager | Mac package manager |
| **Databricks CLI** | Latest | Databricks management | Local operations |
| **DataGrip** | Latest | Database IDE | (Optional) |
| **Postman** | Latest | API Testing | (Optional) |

## 📦 Python Packages (Core)

```txt
# requirements.txt

# Data Processing
pandas>=2.0.0
pyarrow>=14.0.0
pyspark>=3.5.0

# Databricks
databricks-sdk>=0.10.0
databricks-connect>=14.0.0
dbt-databricks>=1.7.0

# Cloud APIs
google-api-python-client>=2.100.0
google-auth>=2.25.0

# API
fastapi>=0.100.0
uvicorn>=0.25.0
pydantic>=2.0.0

# Database
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0

# Logging
loguru>=3.10.0
structlog>=24.0.0

# Testing
pytest>=8.0.0
pytest-cov>=4.0.0
great-expectations>=0.18.0

# Development
black>=24.0.0
isort>=5.13.0
flake8>=7.0.0
mypy>=1.8.0

# Utils
python-dotenv>=1.0.0
requests>=2.31.0
```

## 🐳 Docker Images

```yaml
# docker-compose.yml - Core Services

services:
  # Airflow for orchestration
  airflow-webserver:
    image: apache/airflow:2.8.0-python3.11
    ports:
      - "8080:8080"

  # Metabase for dashboards
  metabase:
    image: metabase/metabase:latest
    ports:
      - "3000:3000"

  # PostgreSQL for metadata
  postgres:
    image: postgres:15
    ports:
      - "5432:5432"

  # Optional: ELK Stack
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    ports:
      - "5044:5044"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
```

## 🖥️ Recommended IDE Setup (VS Code)

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "editor.formatOnSave": true,
  "editor.rulers": [88],
  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true,
    "**/*.pyc": true
  }
}
```

```json
// .vscode/extensions.json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylint",
    "ms-python.black-formatter",
    "ms-python.isort",
    "redhat.vscode-yaml",
    "esbenp.prettier-vscode",
    "github.copilot"
  ]
}
```

## 💻 Mac-Specific Setup

```bash
# Install via Homebrew (Mac)
brew install \
  python@3.11 \
  pyenv \
  git \
  docker \
  postgresql \
  redis

# Install via Homebrew Cask
brew install --cask \
  visual-studio-code \
  datagrip \
  postman \
  docker
```

## 📊 System Requirements

### For Mac (Local Development)

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| macOS | 12.x (Monterey) | 14.x (Sonoma) |
| RAM | 8 GB | 16 GB |
| Storage | 50 GB free | 100 GB free |
| CPU | Apple Silicon / Intel | Apple Silicon (M1/M2/M3) |

### For Docker

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM allocated to Docker | 4 GB | 8 GB |
| CPUs allocated | 2 cores | 4 cores |
| Disk space for containers | 20 GB | 50 GB |

## 🔄 Dependency Compatibility Matrix

| Python | dbt-databricks | Databricks SDK | pandas |
|--------|----------------|----------------|--------|
| 3.9 | 1.5+ | 0.10+ | 1.5+ |
| 3.10 | 1.6+ | 0.12+ | 2.0+ |
| 3.11 | 1.7+ | 0.14+ | 2.1+ |
| 3.12 | 1.8+ | 0.16+ | 2.2+ |

## Related Documentation

- [Data Flow](./data-flow.md) - Architecture details
- [Local Environment Setup](../setup/local-environment.md) - Setup guide
- [dbt Quickstart](../tools/dbt-quickstart.md) - dbt setup
