# Architecture Overview

## System Design

Data Platform sử dụng kiến trúc **Medallion** (Bronze → Silver → Gold) với **Data Lakehouse** pattern trên Databricks.

## 📊 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │ Google Drive     │  │ REST APIs        │  │ Manual Uploads              │ │
│  │ (CSV/Excel)      │  │ (JSON responses) │  │ (via Upload Endpoint)       │ │
│  └────────┬─────────┘  └────────┬─────────┘  └────────────┬───────────────┘ │
└───────────┼──────────────────────┼──────────────────────────┼─────────────────┘
            │                      │                          │
            ▼                      ▼                          ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                              RAW LAYER (Bronze)                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ Google Drive Shared Drive (Free Storage)                                │   │
│  │  ├── /raw/sources/      (Original files from business)                  │   │
│  │  ├── /raw/api_responses/ (Raw API responses)                           │   │
│  │  └── /raw/manual_uploads/ (User uploads)                               │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────────┘
            │
            │ Python Scripts + Databricks SDK
            ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                           DELTA LAKE LAYER                                    │
│                                                                               │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────┐  │
│  │   BRONZE TABLE     │  │   SILVER TABLE     │  │   GOLD TABLE           │  │
│  │                    │  │                    │  │                        │  │
│  │ Raw ingestion      │  │ Cleansed           │  │ Business-ready         │  │
│  │ - Exact copy       │  │ - Deduplicated     │  │ - dim_* (dimensions)   │  │
│  │ - Schema-on-read   │  │ - Type corrected   │  │ - fct_* (facts)        │  │
│  │ - Audit columns    │  │ - Validated        │  │ - aggregates           │  │
│  │                    │  │ - Enriched         │  │                        │  │
│  │ Location:          │  │ Location:          │  │ Location:              │  │
│  │ /bronze/tables/   │  │ /silver/tables/   │  │ /gold/tables/         │  │
│  └────────────────────┘  └────────────────────┘  └────────────────────────┘  │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
            │
            │ dbt transformations
            ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                              ANALYTICS LAYER                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ Databricks SQL Warehouse                                                │  │
│  │  ├── Business Metrics (KPIs, KPIs)                                      │  │
│  │  ├── Data Marts (Sales, Marketing, Operations)                          │  │
│  │  └── ML Features (if needed)                                             │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
            │
            │ SQL Queries
            ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                              SERVING LAYER                                     │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────┐  │
│  │ Metabase Dashboard │  │ API Endpoints       │  │ Embedded Analytics     │  │
│  │ (Free, Mac-native) │  │ (FastAPI)           │  │ (Power BI Service)     │  │
│  └────────────────────┘  └────────────────────┘  └────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────┐
│                          LOGGING & MONITORING LAYER                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ Python logging + Loguru + ELK Stack                                     │  │
│  │  ├── Pipeline execution logs                                            │  │
│  │  ├── Data quality logs                                                 │  │
│  │  ├── Error tracking & alerting                                          │  │
│  │  └── Performance metrics                                                │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────┐
│                              ORCHESTRATION                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ Apache Airflow (Local Docker) + Databricks Jobs                         │  │
│  │  ├── Schedule orchestration                                             │  │
│  │  ├── Dependency management                                               │  │
│  │  ├── Retry logic & error handling                                       │  │
│  │  └── Monitoring & alerts                                                │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow

```
1. INGESTION FLOW
   ┌────────────┐     ┌──────────────┐     ┌─────────────┐
   │ Google    │────▶│ Python       │────▶│ Databricks  │
   │ Drive     │     │ Ingestion    │     │ Bronze      │
   │ (Raw CSV)  │     │ Script       │     │ (Raw Tables)│
   └────────────┘     └──────────────┘     └─────────────┘

2. TRANSFORMATION FLOW
   ┌────────────┐     ┌──────────────┐     ┌─────────────┐
   │ Bronze     │────▶│ dbt          │────▶│ Silver      │
   │ (Raw)      │     │ Databricks   │     │ (Cleansed)  │
   └────────────┘     └──────────────┘     └─────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │ Gold        │
                     │ (Business   │
                     │ Metrics)    │
                     └─────────────┘

3. SERVING FLOW
   ┌────────────┐     ┌──────────────┐     ┌─────────────┐
   │ Gold       │────▶│ Metabase     │────▶│ Dashboard   │
   │ (Metrics)  │     │ (SQL Query)  │     │ (Charts)   │
   └────────────┘     └──────────────┘     └─────────────┘
```

## 🏗️ Component Architecture

### 1. Data Ingestion Layer

```
┌─────────────────────────────────────────────┐
│         Ingestion Scripts (Python)           │
├─────────────────────────────────────────────┤
│  google_drive_sync.py   │  RestApiFetcher   │
│  - List files          │  - HTTP requests   │
│  - Download files      │  - Pagination      │
│  - Track changes       │  - Rate limiting   │
├─────────────────────────────────────────────┤
│              Databricks SDK                 │
│  - write to Delta Lake                      │
│  - Schema inference                         │
│  - Partition management                     │
└─────────────────────────────────────────────┘
```

### 2. Transformation Layer (dbt)

```
┌─────────────────────────────────────────────┐
│           dbt-databricks Project             │
├─────────────────────────────────────────────┤
│  models/                                   │
│  ├── bronze/        (Staging)              │
│  │   ├── stg_sales.sql                      │
│  │   └── stg_customers.sql                  │
│  ├── silver/       (Intermediate)          │
│  │   ├── int_orders_enriched.sql            │
│  │   └── int_customer_metrics.sql           │
│  ├── gold/         (Business)              │
│  │   ├── dim_customers.sql                  │
│  │   ├── fct_orders.sql                     │
│  │   └── agg_daily_sales.sql                │
│  └── mart/         (Analytics)             │
│      ├── rpt_sales_dashboard.sql            │
│      └── rpt_marketing_metrics.sql          │
├─────────────────────────────────────────────┤
│  tests/                                    │
│  ├── not_null tests                        │
│  ├── unique tests                          │
│  └── relationship tests                    │
└─────────────────────────────────────────────┘
```

### 3. Orchestration Layer (Airflow)

```
┌─────────────────────────────────────────────┐
│              Airflow DAGs                   │
├─────────────────────────────────────────────┤
│  dag_daily_ingestion.py                    │
│  ├── Task: check_google_drive              │
│  ├── Task: download_new_files              │
│  ├── Task: ingest_to_bronze                │
│  ├── Task: run_dbt_silver                  │
│  ├── Task: run_dbt_gold                    │
│  └── Task: refresh_metabase                │
├─────────────────────────────────────────────┤
│  dag_weekly_refresh.py                     │
│  ├── Task: full_refresh                    │
│  └── Task: run_all_tests                   │
└─────────────────────────────────────────────┘
```

### 4. Serving Layer (Metabase)

```
┌─────────────────────────────────────────────┐
│              Metabase                       │
├─────────────────────────────────────────────┤
│  Dashboards/                               │
│  ├── 📊 Overview Dashboard                 │
│  │   ├── KPI Cards (Total Revenue, etc.)  │
│  │   ├── Line Charts (Trends)              │
│  │   └── Funnel Charts                     │
│  ├── 📈 Sales Analytics                    │
│  │   ├── Revenue by Product               │
│  │   ├── Sales by Region                   │
│  │   └── Cohort Analysis                   │
│  └── 👥 Customer Analytics                 │
│      ├── Customer Segments                 │
│      ├── Retention Rates                   │
│      └── LTV Analysis                      │
└─────────────────────────────────────────────┘
```

### 5. Logging & Monitoring Layer

```
┌─────────────────────────────────────────────┐
│           Logging Architecture              │
├─────────────────────────────────────────────┤
│  Python Logging + Loguru                   │
│  ├── Pipeline logs (INFO)                   │
│  ├── Data quality logs                      │
│  ├── Performance metrics (DEBUG)            │
│  └── Error tracking (ERROR)                 │
├─────────────────────────────────────────────┤
│  Log Storage (ELK/Loki)                    │
│  ├── Elasticsearch (Search)                 │
│  ├── Logstash/Filebeat (Collection)        │
│  └── Kibana/Grafana (Visualization)         │
├─────────────────────────────────────────────┤
│  Alerting                                  │
│  ├── Slack notifications (errors)          │
│  ├── Email alerts (critical)               │
│  └── PagerDuty (if needed)                 │
└─────────────────────────────────────────────┘
```

## 📁 Storage Structure

### Databricks DBFS

```
dbfs:/
├── /mnt/
│   └── data_platform/
│       ├── bronze/
│       │   └── tables/
│       │       ├── sales_raw/
│       │       ├── customers_raw/
│       │       └── products_raw/
│       ├── silver/
│       │   └── tables/
│       │       ├── sales_clean/
│       │       ├── customers_enriched/
│       │       └── products_standardized/
│       └── gold/
│           └── tables/
│               ├── dim_customers/
│               ├── fct_orders/
│               └── agg_daily_metrics/
```

### Google Drive (Raw Layer)

```
Google Drive (Shared Drive: data-platform)
├── raw/
│   ├── sources/
│   │   ├── sales/
│   │   │   ├── sales_2024-01.csv
│   │   │   └── sales_2024-02.csv
│   │   ├── customers/
│   │   │   └── customers_master.csv
│   │   └── products/
│   │       └── products_catalog.xlsx
│   ├── api_responses/
│   │   └── weather_api/
│   │       └── 2024-01-15.json
│   └── manual_uploads/
│       └── sales_q1_2024.xlsx
└── staging/
    └── processed/
```

## 🔐 Security Architecture

```
┌─────────────────────────────────────────────┐
│            Security Layers                  │
├─────────────────────────────────────────────┤
│  1. Network Security                       │
│     ├── VPC (Databricks)                   │
│     ├── Firewall rules                     │
│     └── SSL/TLS encryption                 │
├─────────────────────────────────────────────┤
│  2. Access Control                          │
│     ├── IAM (Cloud)                        │
│     ├── Unity Catalog (Databricks)         │
│     └── Row/Column level security          │
├─────────────────────────────────────────────┤
│  3. Authentication                         │
│     ├── Databricks token                   │
│     ├── Service accounts                   │
│     └── OAuth (Metabase)                   │
├─────────────────────────────────────────────┤
│  4. Data Security                          │
│     ├── Encryption at rest                 │
│     ├── PII masking                        │
│     └── Audit logging                      │
└─────────────────────────────────────────────┘
```

## 📊 Performance Considerations

### Databricks Optimization

| Technique | Use Case | Benefit |
|-----------|----------|---------|
| Auto-scaling | Variable workloads | Cost optimization |
| Liquid clustering | Time-series data | Faster queries |
| Photon Engine | All queries | 3x faster |
| Caching | Repeated queries | 10x faster |
| Delta Lake | ACID transactions | Data reliability |

### Best Practices

1. **Partitioning**: Partition by date for time-series data
2. **Bucketing**: Bucket by high-cardinality columns (customer_id)
3. **Z-Ordering**: Optimize data skipped by filters
4. **Materialized Views**: Pre-compute expensive aggregations

## 🔄 Disaster Recovery

```
┌─────────────────────────────────────────────┐
│           Backup Strategy                   │
├─────────────────────────────────────────────┤
│  Daily Backups                             │
│  ├── Bronze layer: 7 days                  │
│  ├── Silver layer: 30 days                 │
│  └── Gold layer: 90 days                   │
├─────────────────────────────────────────────┤
│  Cross-Region Replication                  │
│  ├── Production → DR region               │
│  └── RTO: 4 hours, RPO: 24 hours           │
├─────────────────────────────────────────────┤
│  Point-in-time Recovery                    │
│  └── Delta Lake time travel               │
└─────────────────────────────────────────────┘
```

## Related Documentation

- [Data Flow](./data-flow.md) - Detailed data flow
- [Tech Stack](./tech-stack.md) - Technology details
- [Logging Architecture](../logging/architecture.md) - Logging setup
