# Local Environment Setup Guide

## Overview

Hướng dẫn setup môi trường phát triển cho Data Platform trên Mac.

## Prerequisites

### Required Software

| Software | Version | Download | Purpose |
|----------|--------|---------|---------|
| Python | 3.11+ | [python.org](https://www.python.org/downloads/) | Core language |
| Git | Latest | `brew install git` | Version control |
| Docker Desktop | Latest | [docker.com](https://www.docker.com/products/docker-desktop/) | Containerization |
| Homebrew | Latest | [brew.sh](https://brew.sh/) | Package manager |

### Optional but Recommended

| Software | Version | Download | Purpose |
|----------|--------|---------|---------|
| VS Code | Latest | [code.visualstudio.com](https://code.visualstudio.com/) | Code editor |
| DataGrip | Latest | [jetbrains.com/datagrip](https://www.jetbrains.com/datagrip/) | Database IDE |
| Postman | Latest | [postman.com](https://www.postman.com/) | API testing |

## Step 1: Install Homebrew (nếu chưa có)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## Step 2: Install Python 3.11+

```bash
# Cài Python qua pyenv (recommend)
brew install pyenv

# Thêm vào shell config (~/.zshrc)
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc

# Cài Python 3.11
pyenv install 3.11.9
pyenv global 3.11.9

# Verify
python --version
```

## Step 3: Install Docker Desktop

```bash
# Download từ docker.com hoặc qua Homebrew
brew install --cask docker

# Start Docker Desktop
open -a Docker
```

**Verify Docker:**
```bash
docker --version
docker-compose --version
```

## Step 4: Create Project Structure

```bash
cd ~/Documents/project/data-platfrom

# Tạo virtual environment
python -m venv venv
source venv/bin/activate

# Tạo folder structure
mkdir -p src/{ingestion,transformation,api,utils}
mkdir -p configs
mkdir -p data/{raw,staging,analytics}
mkdir -p logs
mkdir -p tests
```

## Step 5: Create Environment File

```bash
# Tạo .env file
cat > .env << 'EOF'
# Databricks Configuration
DATABRICKS_HOST=https://dbc-xxxxx.cloud.databricks.com
DATABRICKS_TOKEN=your-databricks-token
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id

# Google Drive API
GOOGLE_DRIVE_CREDENTIALS_PATH=./configs/google-drive-credentials.json
GOOGLE_DRIVE_FOLDER_ID=your-folder-id

# Database (nếu cần local backup)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=data_platform
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password

# Logging
LOG_LEVEL=INFO
LOG_PATH=./logs

# Airflow
AIRFLOW_HOME=./airflow
EOF
```

## Step 6: Install Core Python Packages

```bash
# Upgrade pip
pip install --upgrade pip

# Core packages
pip install \
    databricks-sdk \
    dbt-databricks \
    apache-airflow \
    great-expectations \
    pandas \
    pyarrow \
    fastapi \
    uvicorn \
    python-dotenv \
    pydantic \
    sqlalchemy \
    psycopg2-binary \
    google-api-python-client \
    google-auth \
    loguru \
    structlog \
    pytest \
    pytest-cov \
    black \
    isort \
    flake8
```

## Step 7: Install Databricks CLI

```bash
# Cài Databricks CLI
pip install databricks-cli

# Configure (sẽ hỏi host và token)
databricks configure --token

# Verify
databricks workspace list
```

## Step 8: Install Airflow (Docker)

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    volumes:
      - postgres_data:/var/lib/postgresql/data

  airflow-webserver:
    image: apache/airflow:2.8.0
    command: webserver
    ports:
      - "8080:8080"
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
      AIRFLOW__CORE__FERNET_KEY: ''
      AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: 'true'
      AIRFLOW__CORE__LOAD_EXAMPLES: 'true'
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./airflow/logs:/opt/airflow/logs
    depends_on:
      - postgres
```

```bash
# Start Airflow
docker-compose up -d

# Access: http://localhost:8080
# Default: airflow / airflow
```

## Step 9: Install Metabase (Docker)

```bash
# Metabase Docker
docker run -d \
  -p 3000:3000 \
  --name metabase \
  -e "MB_DB_TYPE=postgres" \
  -e "MB_DB_DBNAME=metabase" \
  -e "MB_DB_PORT=5432" \
  -e "MB_DB_USER=airflow" \
  -e "MB_DB_PASS=airflow" \
  -e "MB_DB_HOST=localhost" \
  metabase/metabase
```

## Step 10: Verify Installation

```bash
# Python packages
python -c "import databricks; print('Databricks SDK OK')"
python -c "import dbt; print('dbt OK')"
python -c "import pandas; print('Pandas OK')"

# Docker
docker ps

# Databricks CLI
databricks workspace list

# Airflow
curl http://localhost:8080

# Metabase
curl http://localhost:3000
```

## Troubleshooting

### Python Version Issues

```bash
# Nếu gặp lỗi python command not found
which python3
/usr/local/bin/python3

# Link python3 to python
ln -s /usr/local/bin/python3 /usr/local/bin/python
```

### Docker Permission Issues

```bash
# Thêm user vào docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Port Already in Use

```bash
# Kiểm tra port đang dùng
lsof -i :8080
lsof -i :3000
lsof -i :5432

# Kill process
kill -9 <PID>
```

## Next Steps

Tiếp theo, làm theo hướng dẫn:
1. [Databricks Setup](./databricks-setup.md)
2. [Google Drive Setup](./google-drive-setup.md)
3. [Architecture Overview](../architecture/data-flow.md)
