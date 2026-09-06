# Architecture Overview - Tổng Quan Kiến Trúc

## 📊 Sơ Đồ Kiến Trúc Tổng Quan

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              DATA PLATFORM ARCHITECTURE                             │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌─────────────────┐
                                    │   DATA SOURCES   │
                                    └────────┬────────┘
                                             │
              ┌──────────────────────────────┼──────────────────────────────┐
              │                              │                              │
              ▼                              ▼                              ▼
    ┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
    │  Google Drive   │          │   REST APIs    │          │  Manual Upload │
    │  (CSV/Excel)   │          │  (JSON)        │          │   (API)        │
    └────────┬────────┘          └────────┬────────┘          └────────┬────────┘
             │                             │                             │
             └──────────────────────────────┼──────────────────────────────┘
                                          │
                                          ▼
    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                          RAW LAYER - BRONZE                                    │
    │  ┌─────────────────────────────────────────────────────────────────────────┐   │
    │  │  Google Drive Shared Drive (Free)                                      │   │
    │  │  ├── /raw/sources/         (CSV, Excel files từ business)            │   │
    │  │  ├── /raw/api_responses/   (Raw JSON responses)                      │   │
    │  │  └── /raw/manual_uploads/ (User uploads)                            │   │
    │  └─────────────────────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          │ Python Scripts + Databricks SDK
                                          ▼
    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                          DELTA LAKE LAYER                                     │
    │                                                                               │
    │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
    │  │   BRONZE        │───▶│   SILVER        │───▶│   GOLD                 │  │
    │  │   (Raw Tables)  │    │   (Cleaned)     │    │   (Business Metrics)   │  │
    │  │                 │    │                 │    │                        │  │
    │  │ stg_sales      │    │ int_orders      │    │ dim_customers          │  │
    │  │ stg_customers  │    │ int_customers   │    │ dim_products           │  │
    │  │ stg_products   │    │ int_products    │    │ dim_dates              │  │
    │  │                 │    │                 │    │                        │  │
    │  │ Location:       │    │ Location:       │    │ fct_orders             │  │
    │  │ /bronze/tables/ │    │ /silver/tables/ │    │ fct_order_items        │  │
    │  │                 │    │                 │    │ agg_daily_metrics      │  │
    │  │                 │    │                 │    │                        │  │
    │  │ 100% raw data   │    │ 95% clean       │    │ Location:              │  │
    │  │ Schema-on-read  │    │ Validated       │    │ /gold/tables/         │  │
    │  │ Add metadata    │    │ Deduplicated    │    │                        │  │
    │  └─────────────────┘    └─────────────────┘    │ Business-ready         │  │
    │                                                │ KPIs, Metrics           │  │
    │  Databricks Community Edition                  └─────────────────────────┘  │
    └─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          │ SQL Queries
                                          ▼
    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                          SERVING LAYER                                         │
    │                                                                               │
    │  ┌─────────────────────────────────────────────────────────────────────────┐   │
    │  │  METABASE DASHBOARD (Mac-Friendly, Free)                               │   │
    │  │                                                                         │   │
    │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │   │
    │  │  │  Executive   │  │   Sales     │  │  Customer   │             │   │
    │  │  │  Dashboard  │  │  Dashboard   │  │  Dashboard  │             │   │
    │  │  └──────────────┘  └──────────────┘  └──────────────┘             │   │
    │  │                                                                         │   │
    │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │   │
    │  │  │  Product    │  │  Marketing  │  │  Operations │             │   │
    │  │  │  Dashboard  │  │  Dashboard   │  │  Dashboard  │             │   │
    │  │  └──────────────┘  └──────────────┘  └──────────────┘             │   │
    │  │                                                                         │   │
    │  │  Features:                                                              │   │
    │  │  • KPI Cards    • Line Charts    • Bar Charts    • Maps              │   │
    │  │  • Tables       • Funnels        • Pie Charts     • Dashboards        │   │
    │  └─────────────────────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                          LOGGING & MONITORING LAYER                            │
    │                                                                               │
    │  ┌─────────────────────────────────────────────────────────────────────────┐   │
    │  │  Python Logging + Loguru + Loki                                        │   │
    │  │                                                                         │   │
    │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │   │
    │  │  │  Pipeline   │  │   Data      │  │   System   │             │   │
    │  │  │  Logs       │  │  Quality    │  │  Metrics   │             │   │
    │  │  │  (INFO)     │  │  Logs      │  │  (DEBUG)    │             │   │
    │  │  └──────────────┘  └──────────────┘  └──────────────┘             │   │
    │  │                                                                         │   │
    │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │   │
    │  │  │  Error      │  │  Slack      │  │   Grafana   │             │   │
    │  │  │  Tracking   │  │  Alerts     │  │  Dashboard   │             │   │
    │  │  │  (ERROR)    │  │             │  │             │             │   │
    │  │  └──────────────┘  └──────────────┘  └──────────────┘             │   │
    │  └─────────────────────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                              ORCHESTRATION LAYER                               │
    │                                                                               │
    │  ┌─────────────────────────────────────────────────────────────────────────┐   │
    │  │  APACHE AIRFLOW (Local Docker)                                          │   │
    │  │                                                                         │   │
    │  │  DAGs:                                                                  │   │
    │  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │   │
    │  │  │  daily_ingestion │  │  dbt_transform  │  │  health_check   │     │   │
    │  │  │  DAG            │  │  DAG            │  │  DAG            │     │   │
    │  │  └──────────────────┘  └──────────────────┘  └──────────────────┘     │   │
    │  │                                                                         │   │
    │  │  Schedule:                                                              │   │
    │  │  • Ingestion: Daily 2:00 AM                                            │   │
    │  │  • Transformation: Daily 3:30 AM                                       │   │
    │  │  • Health Check: Every 15 minutes                                     │   │
    │  └─────────────────────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow Chi Tiết

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                          │
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: INGESTION (Python Scripts)                                            │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   Google Drive          Python Script            Databricks                       │
│   ┌──────────┐        ┌─────────────┐         ┌──────────────────┐            │
│   │ sales_   │──────▶│ Google      │───────▶│  Bronze Layer     │            │
│   │ 2024.csv │        │ Drive API   │         │  stg_sales        │            │
│   └──────────┘        └─────────────┘         └──────────────────┘            │
│                               │                                                 │
│                               │                                                 │
│   ┌──────────┐        ┌─────────────┐         ┌──────────────────┐            │
│   │ customers│──────▶│ Download   │───────▶│  Bronze Layer     │            │
│   │ .csv    │        │ Files      │         │  stg_customers   │            │
│   └──────────┘        └─────────────┘         └──────────────────┘            │
│                               │                                                 │
│                               │                                                 │
│   ┌──────────┐        ┌─────────────┐         ┌──────────────────┐            │
│   │ products │──────▶│ Validate   │───────▶│  Bronze Layer     │            │
│   │ .xlsx   │        │ Schema     │         │  stg_products    │            │
│   └──────────┘        └─────────────┘         └──────────────────┘            │
│                                                                                  │
│   Logs:                                                                            │
│   [INFO] GoogleDriveSync: Found 3 new files                                       │
│   [INFO] DatabricksWriter: Written 1000 rows to bronze.sales_raw                  │
│   [INFO] Pipeline: Ingestion completed in 120s                                    │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: TRANSFORMATION (dbt)                                                    │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   Bronze Layer          dbt                Silver Layer           Gold Layer       │
│   ┌──────────┐       ┌──────┐        ┌──────────────┐     ┌─────────────────┐  │
│   │ stg_     │─────▶│ Clean│──────▶│ int_orders   │────▶│ dim_customers   │  │
│   │ sales    │       │ Dedupe│        │ _clean       │     │ dim_products    │  │
│   └──────────┘       │ Valid│        └──────────────┘     │ fct_orders      │  │
│                       │ Trans│                                  └─────────────────┘  │
│   ┌──────────┐       └──────┘        ┌──────────────┐                             │
│   │ stg_     │─────▶│ Enrich │──────▶│ int_customers│                             │
│   │ customers│       │ Join  │        │ _enriched     │                             │
│   └──────────┘       └──────┘        └──────────────┘                             │
│                                                                                  │
│   dbt run:                                                                          │
│   dbt run --select tag:bronze        # Run bronze models                         │
│   dbt run --select tag:silver        # Run silver models                         │
│   dbt run --select tag:gold          # Run gold models                          │
│                                                                                  │
│   dbt test:                                                                         │
│   dbt test --select tag:silver        # Run tests on silver                      │
│   dbt test --select tag:gold         # Run tests on gold                       │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: VISUALIZATION (Metabase)                                               │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   Gold Layer              Metabase                Dashboard                       │
│   ┌──────────┐       ┌─────────────┐         ┌──────────────────┐            │
│   │ fct_     │─────▶│  SQL Query  │───────▶│  Executive        │            │
│   │ orders   │       │             │         │  Overview         │            │
│   └──────────┘       └─────────────┘         │  ┌─────────────┐ │            │
│                          │                   │  │ KPI: Revenue│ │            │
│   ┌──────────┐       ┌─────────────┐         │  │ KPI: Orders │ │            │
│   │ dim_     │─────▶│  SQL Query  │───────▶│  │ Line Chart   │ │            │
│   │ customers │       │             │         │  │ Bar Chart    │ │            │
│   └──────────┘       └─────────────┘         │  └─────────────┘ │            │
│                          │                   └──────────────────┘            │
│   ┌──────────┐       ┌─────────────┐         ┌──────────────────┐            │
│   │ agg_     │─────▶│  SQL Query  │───────▶│  Sales            │            │
│   │ daily    │       │             │         │  Dashboard        │            │
│   └──────────┘       └─────────────┘         └──────────────────┘            │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Component Details

### 1. Data Sources

| Source | Type | Format | Access |
|--------|------|--------|--------|
| Google Drive | Shared Drive | CSV, Excel | Google Drive API |
| REST APIs | External | JSON | HTTP Requests |
| Manual Upload | Web App | Any | FastAPI Endpoint |

### 2. Storage Layers

| Layer | Technology | Purpose | Location |
|-------|------------|---------|----------|
| Raw | Google Drive | Original files | `/raw/` |
| Bronze | Delta Lake | Raw tables | `/bronze/tables/` |
| Silver | Delta Lake | Cleaned tables | `/silver/tables/` |
| Gold | Delta Lake | Metrics | `/gold/tables/` |

### 3. Processing

| Component | Technology | Purpose |
|-----------|------------|---------|
| Ingestion | Python | Load data to Bronze |
| Transformation | dbt-databricks | Clean & transform |
| Orchestration | Airflow | Schedule & monitor |

### 4. Serving

| Component | Technology | Purpose |
|-----------|------------|---------|
| BI Tool | Metabase | Dashboards |
| API | FastAPI | REST endpoints |

### 5. Logging

| Component | Technology | Purpose |
|-----------|------------|---------|
| Logging | Loguru | Application logs |
| Aggregation | Loki | Log storage |
| Visualization | Grafana | Log dashboards |

---

## 🔗 Technology Connections

```
Google Drive  ──────▶  Python  ──────▶  Databricks
   API              Scripts         Bronze Layer
                                            │
                                            ▼
                                   dbt (Transformation)
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    ▼                       ▼                       ▼
              Silver Layer            Gold Layer              dbt Tests
                    │                       │
                    └───────────────────────┘
                               │
                               ▼
                       Metabase Dashboard
```

---

## 📝 Cách Vẽ Sơ Đồ

### Công Cụ Đề Xuất

1. **Draw.io (diagrams.net)** - Miễn phí, trực tuyến
   - https://app.diagrams.net/

2. **Miro** - Collaborative whiteboard
   - https://miro.com/

3. **Lucidchart** - Chuyên nghiệp
   - https://lucidchart.com/

4. **Excalidraw** - Hand-drawn style
   - https://excalidraw.com/

### Màu Sắc Đề Xuất

| Component | Màu | Hex |
|-----------|------|-----|
| Data Sources | 🟢 Xanh lá | #4CAF50 |
| Raw/Bronze | 🟠 Cam | #FF9800 |
| Silver | 🔵 Xanh dương | #2196F3 |
| Gold | 🟡 Vàng | #FFC107 |
| Dashboard | 🟣 Tím | #9C27B0 |
| Orchestration | ⚫ Đen | #212121 |
| Logging | 🟤 Nâu | #795548 |

---

## 📋 Checklist Để Vẽ

- [ ] Data Sources (Google Drive, APIs, Manual)
- [ ] Raw Layer (Google Drive)
- [ ] Bronze Layer (Databricks)
- [ ] Silver Layer (Databricks)
- [ ] Gold Layer (Databricks)
- [ ] Metabase Dashboard
- [ ] Airflow Orchestration
- [ ] Logging Layer (Loguru, Loki, Grafana)
- [ ] Arrows showing data flow
- [ ] Labels cho mỗi layer

---

## Related Documentation

- [Data Flow](./architecture/data-flow.md)
- [Tech Stack](./architecture/tech-stack.md)
- [Logging Architecture](./logging/architecture.md)
