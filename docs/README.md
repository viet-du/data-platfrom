# Data Platform Documentation

## Welcome

Đây là bộ documentation đầy đủ cho Data Platform - một hệ thống data pipeline miễn phí, chạy tốt trên Mac.

## Quick Start

```bash
# 1. Setup môi trường
brew install python@3.11 pyenv
python -m venv venv && source venv/bin/activate

# 2. Clone và cài dependencies
git clone <repo-url> && cd data-platform
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env với credentials của bạn

# 4. Start services
docker-compose up -d

# 5. Access
# - Airflow: http://localhost:8080
# - Metabase: http://localhost:3000
```

## Architecture

```
Google Drive → Databricks (Bronze→Silver→Gold) → Metabase Dashboard
                           ↓
                    LOGGING LAYER
                    (Debug & Monitor)
```

## Documentation Structure

```
docs/
├── setup/                    # Setup guides
│   ├── local-environment.md   # Mac setup
│   ├── databricks-setup.md   # Databricks config
│   └── google-drive-setup.md # Google Drive API
│
├── architecture/             # System design
│   ├── data-flow.md         # Data flow
│   └── tech-stack.md        # Technologies
│
├── tools/                   # Tool guides
│   ├── dbt-quickstart.md   # dbt basics
│   ├── dbt-modeling-guide.md # dbt patterns
│   ├── airflow-dag-guide.md  # Airflow DAGs
│   └── python-ingestion.md   # Python scripts
│
├── pipelines/               # Pipeline guides
│   ├── ingestion-guide.md   # Ingestion
│   └── transformation-guide.md # dbt transforms
│
├── api/                    # API docs
│   └── fastapi-reference.md # REST API
│
├── dashboards/             # Dashboard guides
│   ├── analytics-dashboard.md # Dashboard design
│   └── metabase-setup.md    # Metabase config
│
├── logging/                # Logging docs ⭐
│   ├── architecture.md     # Logging system
│   ├── setup-guide.md     # Setup logging
│   └── log-analysis.md    # Debug & analyze
│
├── testing/               # Testing
│   └── strategy.md        # Test strategy
│
├── adr/                   # Decisions
│   ├── 001-databricks-choice.md
│   ├── 002-google-drive-raw-layer.md
│   └── 003-logging-system.md
│
└── runbooks/              # Operations
    ├── daily-checklist.md   # Daily tasks
    ├── troubleshooting.md   # Fix issues
    └── backup-recovery.md  # Backup guide
```

## Key Features

### ✅ Free & Mac-Friendly

| Component | Option | Price |
|-----------|--------|-------|
| Processing | Databricks Community | Free |
| Dashboard | Metabase | Free |
| Raw Storage | Google Drive | 15GB Free |
| Orchestration | Airflow | Free |
| Logging | Loguru + Loki | Free |

### ✅ Logging System (Debug Agent)

Hệ thống logging đặc biệt cho việc debug khi agent chạy:

```python
# Simple logging
from src.utils.logging_config import get_logger
logger = get_logger(__name__)

logger.info("Starting process")
logger.debug(f"Variable value: {value}")
logger.error(f"Failed: {error}", exc_info=True)
```

Xem chi tiết:
- [Logging Architecture](./logging/architecture.md)
- [Logging Setup](./logging/setup-guide.md)
- [Log Analysis](./logging/log-analysis.md)

## Common Tasks

### Daily Operations

```bash
# Check system health
./scripts/daily_check.sh

# View logs
tail -f logs/data_platform_today.log

# Run pipeline manually
python src/ingestion/run.py

# Check Databricks
databricks workspace list
```

### Troubleshooting

```bash
# Check all services
docker-compose ps

# View error logs
grep ERROR logs/*.log

# Restart services
docker-compose restart

# Clear cache
docker-compose down -v && docker-compose up -d
```

Xem chi tiết: [Troubleshooting Guide](./runbooks/troubleshooting.md)

## Tech Stack

| Layer | Technology |
|-------|------------|
| Storage | Google Drive (Raw), Delta Lake (Processed) |
| Processing | Databricks Community, Apache Spark |
| Transform | dbt-databricks |
| Orchestration | Apache Airflow |
| Dashboard | Metabase |
| API | FastAPI |
| Logging | Loguru, Loki |
| Container | Docker |

## Environment Variables

```bash
# .env
DATABRICKS_HOST=https://dbc-xxxxx.cloud.databricks.com
DATABRICKS_TOKEN=dapi...
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/...

GOOGLE_DRIVE_CREDENTIALS_PATH=./configs/google-drive-credentials.json
GOOGLE_DRIVE_FOLDER_ID=...

LOG_LEVEL=INFO
LOG_DIR=./logs
```

## Dashboard URLs

| Service | URL | Default Login |
|---------|-----|---------------|
| Airflow | http://localhost:8080 | airflow / airflow |
| Metabase | http://localhost:3000 | admin @ email.com |
| Grafana | http://localhost:3001 | admin / admin |

## Development

```bash
# Setup development
make setup

# Run tests
make test

# Run linter
make lint

# Build Docker
make build

# Deploy
make deploy
```

## Support

- **Documentation**: Xem trong folder `docs/`
- **Logs**: Folder `logs/`
- **Issues**: Tạo issue trên GitHub
- **Questions**: Slack #data-platform

## Contributing

1. Fork repository
2. Tạo branch `feature/your-feature`
3. Viết tests
4. Submit PR

## License

MIT License - Xem LICENSE file.

---

**Version:** 1.0.0  
**Last Updated:** 2024-01-15  
**Maintainer:** Data Platform Team
