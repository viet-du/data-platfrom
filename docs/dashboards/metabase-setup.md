# Metabase Setup Guide

## Overview

Hướng dẫn setup và configure Metabase cho Data Platform (Mac-friendly, miễn phí).

## Why Metabase?

| Feature | Metabase | Power BI | Tableau |
|---------|----------|----------|---------|
| Mac Support | ✅ | ❌ | ✅ |
| Price | Free | $10/mo (Pro) | $70/mo |
| Self-hosted | ✅ | ❌ | ✅ |
| Easy to use | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Databricks support | ✅ | ✅ | ✅ |
| SQL Editor | ✅ | ✅ | ✅ |
| Embedding | ✅ | ✅ | ✅ |

## Installation

### Option 1: Docker (Recommended)

```bash
# Create network
docker network create metabase-network

# Run Metabase
docker run -d \
  --name metabase \
  --network metabase-network \
  -p 3000:3000 \
  -e "MB_DB_TYPE=postgres" \
  -e "MB_DB_DBNAME=metabase" \
  -e "MB_DB_PORT=5432" \
  -e "MB_DB_USER=metabase" \
  -e "MB_DB_PASS=metabase123" \
  -e "MB_DB_HOST=postgres" \
  -e "MB_SITE_NAME=Data Platform" \
  -e "MB_ADMIN_EMAIL=admin@company.com" \
  -e "MB_SEND_EMAIL_ON_FIRST_LOGIN_FROM_NEW_ACCOUNT=true" \
  -v metabase-data:/metabase-data \
  metabase/metabase
```

### Option 2: Standalone JAR

```bash
# Download latest
wget https://downloads.metabase.com/latest/metabase.jar

# Run
java -jar metabase.jar
# Access: http://localhost:3000
```

### Option 3: Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  metabase:
    image: metabase/metabase:latest
    container_name: metabase
    ports:
      - "3000:3000"
    environment:
      MB_DB_TYPE: postgres
      MB_DB_DBNAME: metabase
      MB_DB_PORT: 5432
      MB_DB_USER: metabase
      MB_DB_PASS: metabase123
      MB_DB_HOST: postgres
      MB_SITE_NAME: Data Platform
      MB_ANALYTICS_ENABLED: true
    volumes:
      - metabase-data:/metabase-data
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:15
    container_name: metabase-db
    environment:
      POSTGRES_USER: metabase
      POSTGRES_PASSWORD: metabase123
      POSTGRES_DB: metabase
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  metabase-data:
  postgres-data:
```

```bash
docker-compose up -d
```

## Initial Setup

### 1. Access Metabase

```
http://localhost:3000
```

### 2. First-time Setup

1. **Welcome** → Click "Let's get started"
2. **Create your account**
   - Email: admin@company.com
   - Password: Your password
   - Name: Admin
3. **Add your data** → Skip for now (we'll add manually)
4. **Usage analytics** → Choose preference
5. **Finish** → Go to main screen

## Connect to Databricks

### Step 1: Add Database

1. Click **Settings** (⚙️) → **Admin** → **Databases**
2. Click **Add database**
3. Select **Databricks**

### Step 2: Configure Connection

```
┌─────────────────────────────────────────────────────────────┐
│                   Database Settings                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Name:                    Data Platform                    │
│                                                             │
│  Batch  ⚠️ Settings                                     │
│                                                             │
│  Use a dynamic connection           ⚠️ Advanced           │
│  checkbox                         checkbox                 │
│                                                             │
│  ─────────────────────────────────────────────────────   │
│                                                             │
│  ⚠️ Connection Details                                   │
│                                                             │
│  Databricks Host:                                          │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ https://dbc-xxxxx.cloud.databricks.com              │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  HTTP Path:                                                │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ /sql/1.0/warehouses/your-warehouse-id              │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  API Key:                                                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ <YOUR-DATABRICKS-TOKEN>                                  │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  Additional JDBC options:                                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ AuthMech=1;ZoomedOut=0                              │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  Choose a sync schedule                                    │
│  ○ Scan       Every hour    ▼                            │
│  ○ Don't      Every 2 hours ▼                            │
│    sync       Every 12 hours▼                            │
│  ○ Hour       Every 24 hours ▼                            │
│                                                             │
│  [Cancel]                              [Save]             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Step 3: Test Connection

1. Click **Save**
2. Metabase will test the connection
3. If successful, you'll see "Successfully connected!"

### Connection String Format

```
jdbc:databricks://<host>:443/<database>;AuthMech=1;Pwd=<token>;HTTPPath=<http_path>;SparkServerType=3
```

Or use environment variables:

```bash
# .env for Metabase
DATABRICKS_HOST=https://dbc-xxxxx.cloud.databricks.com
DATABRICKS_TOKEN=dapi0123456789abcdef...
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
```

## Create First Dashboard

### Step 1: Create a Question (Query)

1. Click **+ New** → **SQL query**
2. Enter a name: "Total Revenue"
3. Write SQL:

```sql
SELECT 
    SUM(net_revenue) AS total_revenue,
    COUNT(DISTINCT order_id) AS total_orders,
    AVG(net_revenue) AS avg_order_value
FROM data_platform.gold.fct_orders
WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
```

4. Click **Run** (▶️)
5. Click **Save**

### Step 2: Create Visualizations

1. From the result, click **Visualization**
2. Choose chart type:
   - For KPIs: **Progress/Score**
   - For trends: **Line**
   - For categories: **Bar**
3. Configure display options
4. Click **Save**

### Step 3: Create Dashboard

1. Click **+ New** → **Dashboard**
2. Name: "Sales Overview"
3. Click **Add questions**
4. Select your saved questions
5. Arrange on dashboard
6. Add filters if needed

## Useful SQL Queries for Dashboard

### Revenue Metrics

```sql
-- Daily Revenue
SELECT 
    order_date,
    SUM(net_revenue) AS revenue,
    COUNT(DISTINCT order_id) AS orders
FROM data_platform.gold.fct_orders
WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY order_date
ORDER BY order_date

-- Revenue by Category
SELECT 
    category,
    SUM(net_revenue) AS revenue,
    COUNT(DISTINCT order_id) AS orders
FROM data_platform.gold.fct_orders
GROUP BY category
ORDER BY revenue DESC
```

### Customer Metrics

```sql
-- Customer Summary
SELECT 
    COUNT(DISTINCT customer_id) AS total_customers,
    COUNT(DISTINCT CASE WHEN order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) 
        THEN customer_id END) AS active_customers,
    SUM(lifetime_value) AS total_ltv,
    AVG(lifetime_value) AS avg_ltv
FROM data_platform.gold.dim_customers
```

### Product Metrics

```sql
-- Top Products
SELECT 
    p.product_name,
    p.category,
    SUM(o.net_revenue) AS revenue,
    SUM(o.quantity) AS units_sold
FROM data_platform.gold.fct_orders o
JOIN data_platform.gold.dim_products p ON o.product_id = p.product_id
GROUP BY p.product_name, p.category
ORDER BY revenue DESC
LIMIT 20
```

## Filters & Parameters

### Dashboard Filters

Metabase supports these filter types:

| Filter Type | Use For | Example |
|-------------|---------|---------|
| Time range | Date columns | Last 30 days, Custom |
| Location | Geographic | State, City |
| Category | Dropdown | Product Category |
| ID | Search | Customer ID |
| Text | Contains | Product name |

### Example: Date Filter

1. Click **Edit Dashboard**
2. Click **Add a filter**
3. Select **Time range**
4. Configure: "Filter by Date Range"
5. Connect to questions with date columns
6. Save

## Sharing & Permissions

### Sharing

1. Click **Share** on dashboard
2. Choose:
   - **Public link** - Anyone with link can view
   - **Invite users** - Specific Metabase users

### Permissions

| Collection | Admin | Editor | Viewer |
|------------|-------|--------|--------|
| Executive | Full | View | View |
| Sales | Full | Edit | View |
| Draft | Full | Edit | None |

## Embedding

### Simple Embed

```html
<!-- embed.html -->
<iframe 
    src="http://localhost:3000/public/dashboard/abc123"
    width="100%" 
    height="600"
    frameborder="0"
></iframe>
```

### Signed Embed (Secure)

```python
# generate_signed_url.py
import metabase_api

# Initialize
mb = metabase_api.MetabaseApi(
    base_url="http://localhost:3000",
    email="admin@company.com",
    password="password"
)

# Generate signed URL
url = mb.generate_signed_url(
    resource_type="dashboard",
    resource_id=1,
    params={"date_filter": "last30days"}
)
print(url)
```

## Troubleshooting

### Connection Issues

| Error | Solution |
|-------|----------|
| "Connection refused" | Check Databricks is running |
| "Invalid credentials" | Verify API token |
| "Host not found" | Check Databricks URL |
| "Timeout" | Increase timeout in settings |

### Performance Issues

| Issue | Solution |
|-------|----------|
| Slow queries | Use summarized tables |
| Dashboard timeout | Increase timeout in settings |
| Too many filters | Limit filter complexity |

### Common Issues

```bash
# Check logs
docker logs metabase

# Reset admin password
docker exec -it metabase metabase reset-password

# Clear cache
docker exec -it metabase bash
rm -rf /metabase-data/db/*
docker restart metabase
```

## Maintenance

### Backup

```bash
# Backup Metabase data
docker exec postgres pg_dump -U metabase metabase > backup.sql

# Backup Metabase application
docker run --rm \
  -v metabase-data:/data \
  alpine tar czf /tmp/metabase-backup.tar.gz -C /data .
```

### Update

```bash
# Pull new version
docker pull metabase/metabase:latest

# Restart
docker-compose down
docker-compose up -d
```

## Related Documentation

- [Analytics Dashboard Guide](./analytics-dashboard.md)
- [Databricks Setup](../setup/databricks-setup.md)
- [Transformation Pipeline](../pipelines/transformation-guide.md)
