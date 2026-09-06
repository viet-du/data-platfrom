# END-TO-END ARCHITECTURE
# Sơ đồ kiến trúc tổng quan - Dùng để vẽ

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          DATA PLATFORM - END TO END ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘


                                    ┌─────────────────────────────────────────┐
                                    │           DATA SOURCES                 │
                                    │                                         │
    ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────────────┐  │
    │   GOOGLE DRIVE    │   │    REST APIs     │   │      MANUAL UPLOAD       │  │
    │                   │   │                   │   │                         │  │
    │  📁 Shared Drive │   │  🌐 External API  │   │  📤 Web/API Upload      │  │
    │  • sales/*.csv   │   │  • Weather API   │   │  • File upload          │  │
    │  • customers.xlsx│   │  • CRM API       │   │  • Batch import         │  │
    │  • products.csv  │   │  • ERP API       │   │                         │  │
    └─────────┬─────────┘   └─────────┬─────────┘   └────────────┬────────────┘  │
              │                         │                         │               │
              │                         │                         │               │
              └─────────────────────────┼─────────────────────────┘               │
                                    │                                         │
                                    ▼                                         │
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              INGESTION LAYER                                        │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                               │  │
│  │   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐  │  │
│  │   │  Google Drive   │    │  API Fetcher    │    │    Validator       │  │  │
│  │   │    Sync         │    │                 │    │                     │  │  │
│  │   │  • List files   │    │  • HTTP calls   │    │  • Schema check   │  │  │
│  │   │  • Download     │    │  • Pagination   │    │  • Quality rules  │  │  │
│  │   │  • Track changes│    │  • Rate limit   │    │  • Type convert   │  │  │
│  │   └────────┬────────┘    └────────┬────────┘    └──────────┬──────────┘  │  │
│  │            │                      │                           │              │  │
│  │            └──────────────────────┼───────────────────────────┘              │  │
│  │                                   ▼                                          │  │
│  │                         ┌─────────────────┐                               │  │
│  │                         │  Databricks     │                               │  │
│  │                         │    Writer      │                               │  │
│  │                         │                │                               │  │
│  │                         │  • Write to    │                               │  │
│  │                         │    Bronze     │                               │  │
│  │                         │  • Add metadata│                               │  │
│  │                         │  • Partition   │                               │  │
│  │                         └────────┬────────┘                               │  │
│  │                                  │                                        │  │
│  └──────────────────────────────────┼────────────────────────────────────────┘  │
│                                     ▼                                           │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              RAW LAYER - BRONZE                                    │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                               │  │
│  │  📍 Location: Google Drive + Databricks DBFS                                 │  │
│  │                                                                               │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐   │  │
│  │  │  sales_raw/     │  │  customers_raw/ │  │   products_raw/         │   │  │
│  │  │                 │  │                 │  │                         │   │  │
│  │  │  • sales_2024.csv│  │  • customers_  │  │  • products_catalog_  │   │  │
│  │  │  • sales_2023.csv│  │      2024.xlsx │  │      2024.csv         │   │  │
│  │  │  • sales_2022.csv│  │  • customers_ │  │  • product_images/   │   │  │
│  │  │                  │  │      2023.xlsx │  │                        │   │  │
│  │  │                  │  │                │  │                        │   │  │
│  │  │  Columns:       │  │  Columns:      │  │  Columns:             │   │  │
│  │  │  • order_id     │  │  • customer_id │  │  • product_id        │   │  │
│  │  │  • customer_id  │  │  • name        │  │  • product_name      │   │  │
│  │  │  • product_id   │  │  • email       │  │  • category          │   │  │
│  │  │  • order_date   │  │  • phone       │  │  • price             │   │  │
│  │  │  • sale_amount  │  │  • address     │  │  • stock             │   │  │
│  │  │  • quantity     │  │  • segment     │  │  • supplier          │   │  │
│  │  │                  │  │                │  │                        │   │  │
│  │  │  + Metadata:    │  │  + Metadata:   │  │  + Metadata:         │   │  │
│  │  │  • _file_name   │  │  • _file_name  │  │  • _file_name        │   │  │
│  │  │  • _etl_loaded  │  │  • _etl_loaded │  │  • _etl_loaded       │   │  │
│  │  │  • _batch_id    │  │  • _batch_id   │  │  • _batch_id         │   │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────┘   │  │
│  │                                                                               │  │
│  │  ✅ Characteristics:                                                           │  │
│  │  • 100% raw data, no transformation                                          │  │
│  │  • Schema-on-read (infer khi đọc)                                           │  │
│  │  • Add metadata columns (audit)                                              │  │
│  │  • Partition by date                                                         │  │
│  │                                                                               │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ dbt run (tag:bronze)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                            STAGING LAYER - SILVER                                   │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                               │  │
│  │  📍 Location: Databricks Delta Lake                                          │  │
│  │  🏷️ Materialized: TABLE                                                     │  │
│  │                                                                               │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐   │  │
│  │  │  stg_sales/     │  │  stg_customers/ │  │   stg_products/        │   │  │
│  │  │                 │  │                 │  │                         │   │  │
│  │  │  • Type cast   │  │  • Normalize   │  │  • Standardize        │   │  │
│  │  │  • Rename cols │  │  • Clean names │  │  • Category mapping   │   │  │
│  │  │  • Add dates   │  │  • Valid email │  │  • Price normalize   │   │  │
│  │  │                 │  │  • Phone format│  │  • Unit conversion   │   │  │
│  │  │                 │  │                │  │                        │   │  │
│  │  │  Schema:       │  │  Schema:       │  │  Schema:             │   │  │
│  │  │  • order_id    │  │  • customer_id│  │  • product_id        │   │  │
│  │  │  • customer_id │  │  • full_name  │  │  • product_name      │   │  │
│  │  │  • product_id  │  │  • email      │  │  • category_id      │   │  │
│  │  │  • order_date  │  │  • phone      │  │  • category_name    │   │  │
│  │  │  • net_amount  │  │  • city       │  │  • standard_price   │   │  │
│  │  │  • quantity    │  │  • country    │  │  • stock_quantity   │   │  │
│  │  │                 │  │  • segment    │  │                        │   │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────┘   │  │
│  │                                                                               │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │  │
│  │  │  INTERMEDIATE MODELS (int_*)                                       │   │  │
│  │  │                                                                      │   │  │
│  │  │  ┌─────────────────────┐  ┌─────────────────────────────────────┐   │   │  │
│  │  │  │  int_orders_base/  │  │  int_customers_enriched/             │   │   │  │
│  │  │  │                    │  │                                      │   │   │  │
│  │  │  │  • Deduplicate    │  │  • Join with orders                 │   │   │  │
│  │  │  │  • Date parse    │  │  • Calculate LTV                     │   │   │  │
│  │  │  │  • Status norm   │  │  • Segment customers                 │   │   │  │
│  │  │  │  • Calculate amt │  │  • Flag churn risk                   │   │   │  │
│  │  │  │  • Quality flags │  │                                      │   │   │  │
│  │  │  └─────────────────────┘  └─────────────────────────────────────┘   │   │  │
│  │  │                                                                      │   │  │
│  │  └─────────────────────────────────────────────────────────────────────┘   │  │
│  │                                                                               │  │
│  │  ✅ Characteristics:                                                           │  │
│  │  • Cleansed & validated                                                       │  │
│  │  • Deduplicated                                                               │  │
│  │  • Type corrected                                                             │  │
│  │  • Business logic layer 1                                                     │  │
│  │                                                                               │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ dbt run (tag:silver) + dbt test
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                            BUSINESS LAYER - GOLD                                    │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                               │  │
│  │  📍 Location: Databricks Delta Lake                                          │  │
│  │  🏷️ Materialized: TABLE (partitioned, clustered)                            │  │
│  │                                                                               │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  DIMENSION TABLES (dim_*) - Kimball Style                             │ │  │
│  │  │                                                                          │ │  │
│  │  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐│ │  │
│  │  │  │  dim_customers/ │  │  dim_products/ │  │   dim_dates/            ││ │  │
│  │  │  │                 │  │                 │  │                         ││ │  │
│  │  │  │  • Surrogate   │  │  • Surrogate   │  │  • Date key (PK)       ││ │  │
│  │  │  │    key        │  │    key        │  │  • Date                ││ │  │
│  │  │  │  • Business   │  │  • Business   │  │  • Day of week         ││ │  │
│  │  │  │    keys      │  │    keys      │  │  • Month               ││ │  │
│  │  │  │  • Attributes│  │  • Attributes│  │  • Quarter            ││ │  │
│  │  │  │  • Flags     │  │  • Hierarchy │  │  • Year               ││ │  │
│  │  │  │  • Metrics   │  │  • SCD Type2 │  │  • Is weekend         ││ │  │
│  │  │  │              │  │             │  │  • Fiscal period       ││ │  │
│  │  │  └─────────────────┘  └─────────────────┘  └─────────────────────────┘│ │  │
│  │  │                                                                          │ │  │
│  │  │  ┌─────────────────┐  ┌─────────────────┐                           ││ │  │
│  │  │  │  dim_locations/ │  │  dim_categories/│                           ││ │  │
│  │  │  │                 │  │                 │                           ││ │  │
│  │  │  │  • location_key │  │  • category_key │                           ││ │  │
│  │  │  │  • country      │  │  • category     │                           ││ │  │
│  │  │  │  • state        │  │  • sub_category │                           ││ │  │
│  │  │  │  • city         │  │  • hierarchy    │                           ││ │  │
│  │  │  │  • region       │  │                 │                           ││ │  │
│  │  │  │  • timezone     │  │                 │                           ││ │  │
│  │  │  └─────────────────┘  └─────────────────┘                           ││ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                               │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  FACT TABLES (fct_*)                                                  │ │  │
│  │  │                                                                          │ │  │
│  │  │  ┌─────────────────────┐  ┌─────────────────────────────────────┐      │ │  │
│  │  │  │  fct_orders/        │  │  fct_order_items/                   │      │ │  │
│  │  │  │                     │  │                                      │      │ │  │
│  │  │  │  PK: order_id      │  │  PK: order_item_id                   │      │ │  │
│  │  │  │                     │  │                                      │      │ │  │
│  │  │  │  FK: customer_key  │  │  FK: order_key                      │      │ │  │
│  │  │  │  FK: date_key     │  │  FK: product_key                    │      │ │  │
│  │  │  │  FK: location_key │  │  FK: date_key                      │      │ │  │
│  │  │  │                   │  │  FK: location_key                   │      │ │  │
│  │  │  │  Measures:        │  │                                      │      │ │  │
│  │  │  │  • order_count    │  │  Measures:                          │      │ │  │
│  │  │  │  • gross_amount   │  │  • quantity                         │      │ │  │
│  │  │  │  • net_amount     │  │  • unit_price                       │      │ │  │
│  │  │  │  • discount_amt   │  │  • line_amount                     │      │ │  │
│  │  │  │  • profit         │  │  • discount                         │      │ │  │
│  │  │  │                   │  │  • profit                           │      │ │  │
│  │  │  └─────────────────────┘  └─────────────────────────────────────┘      │ │  │
│  │  │                                                                          │ │  │
│  │  │  ┌─────────────────────────────────────────────────────────────┐      │ │  │
│  │  │  │  AGGREGATES (agg_*) - Pre-computed for dashboards          │      │ │  │
│  │  │  │                                                              │      │ │  │
│  │  │  │  • agg_daily_sales        - Daily sales summary             │      │ │  │
│  │  │  │  • agg_monthly_revenue    - Monthly revenue               │      │ │  │
│  │  │  │  • agg_customer_cohorts   - Cohort analysis               │      │ │  │
│  │  │  │  • agg_product_performance- Product metrics               │      │ │  │
│  │  │  └─────────────────────────────────────────────────────────────┘      │ │  │
│  │  │                                                                          │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                               │  │
│  │  ✅ Characteristics:                                                           │  │
│  │  • Business-ready dimensions & facts                                           │  │
│  │  • Pre-calculated KPIs & metrics                                               │  │
│  │  • Optimized for queries (partitioned, clustered)                             │  │
│  │  • SCD Type 2 for slowly changing dimensions                                  │  │
│  │                                                                               │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ SQL Queries / JDBC
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              ANALYTICS LAYER                                       │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                               │  │
│  │   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐  │  │
│  │   │    METABASE     │    │    FASTAPI      │    │   EMBEDDED          │  │  │
│  │   │   DASHBOARD     │    │      API        │    │   ANALYTICS         │  │  │
│  │   │                 │    │                 │    │                     │  │  │
│  │   │  📊 Executive   │    │  🌐 REST API   │    │  🔗 Power BI        │  │  │
│  │   │  📈 Sales      │    │  • Metrics     │    │  🔗 Tableau         │  │  │
│  │   │  👥 Customer   │    │  • KPIs        │    │  🔗 Embedded        │  │  │
│  │   │  📦 Product    │    │  • Trends      │    │      Reports        │  │  │
│  │   │  📣 Marketing  │    │  • Forecasts   │    │                     │  │  │
│  │   │                 │    │                │    │                     │  │  │
│  │   └────────┬────────┘    └────────┬────────┘    └──────────┬──────────┘  │  │
│  │            │                      │                        │              │  │
│  └────────────┼──────────────────────┼────────────────────────┘              │
│               │                      │                                           │
│               ▼                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         USERS                                              │   │
│  │                                                                             │   │
│  │   👔 Executives     📊 Analysts     👨‍💼 Sales Team     👥 Customers      │   │
│  │                                                                             │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────┘


                                    ┌─────────────────────────────────────────┐
                                    │         LOGGING & MONITORING            │
                                    │                                         │
    ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────────────┐  │
    │    LOGURU        │   │      LOKI        │   │       GRAFANA            │  │
    │                   │   │                   │   │                           │  │
    │  📝 Python Logs  │   │  📦 Log Store   │   │  📊 Dashboards           │  │
    │  • Application   │   │  • Aggregated   │   │  • Pipeline monitoring   │  │
    │  • Pipeline      │   │  • Indexed     │   │  • Error tracking        │  │
    │  • Errors        │   │  • Queried    │   │  • SLA metrics           │  │
    │                   │   │                │   │                           │  │
    └───────────────────┘   └───────────────────┘   └───────────────────────────┘  │
                                    │                                         │
                                    ▼                                         │
                            ┌─────────────────────────────────────────┐        │
                            │            AIRFLOW                       │        │
                            │                                          │        │
                            │  ⏰ Scheduler    📋 DAGs    🔄 Tasks   │        │
                            │                                          │        │
                            │  • daily_ingestion                      │        │
                            │  • dbt_silver_transform                │        │
                            │  • dbt_gold_transform                  │        │
                            │  • health_check                        │        │
                            │                                          │        │
                            └─────────────────────────────────────────┘        │
                                                                                │
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              INFRASTRUCTURE                                         │
│                                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │   LOCAL MAC      │  │   DOCKER        │  │      CLOUD SERVICES             │   │
│  │                  │  │                  │  │                                 │   │
│  │  • Development  │  │  • Airflow      │  │  • Databricks (Free Tier)       │   │
│  │  • Testing      │  │  • Metabase    │  │  • Google Drive (15GB Free)     │   │
│  │  • Debugging    │  │  • Postgres    │  │  • Delta Lake Storage           │   │
│  │                  │  │  • Loki        │  │                                 │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Components to Draw

### 1. Data Sources (3 boxes)
- Google Drive
- REST APIs  
- Manual Upload

### 2. Ingestion Layer (3 boxes + 1 connector)
- Google Drive Sync
- API Fetcher
- Validator
- → Databricks Writer

### 3. Bronze Layer (3 tables)
- sales_raw
- customers_raw
- products_raw

### 4. Silver Layer (3 staging + 2 intermediate)
- stg_sales, stg_customers, stg_products
- int_orders_base, int_customers_enriched

### 5. Gold Layer (4 dimensions + 2 facts + 1 aggregate)
- dim_customers, dim_products, dim_dates, dim_locations
- fct_orders, fct_order_items
- agg_daily_sales

### 6. Analytics Layer (3 boxes)
- Metabase Dashboard
- FastAPI
- Embedded Analytics

### 7. Supporting (3 layers)
- Logging (Loguru → Loki → Grafana)
- Orchestration (Airflow)
- Infrastructure (Local + Docker + Cloud)

---

## 🎨 Color Palette

| Layer | Color | Hex |
|-------|-------|-----|
| Data Sources | Green | #4CAF50 |
| Ingestion | Orange | #FF9800 |
| Bronze | Brown | #795548 |
| Silver | Blue | #2196F3 |
| Gold | Yellow/Gold | #FFC107 |
| Analytics | Purple | #9C27B0 |
| Logging | Gray | #607D8B |
| Orchestration | Dark Gray | #37474F |
| Infrastructure | Light Gray | #ECEFF1 |
