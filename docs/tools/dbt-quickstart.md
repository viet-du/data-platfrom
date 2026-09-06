# dbt Quickstart Guide

## Overview

Hướng dẫn nhanh setup dbt-databricks cho Data Platform.

## Prerequisites

```bash
# Python 3.11+
python --version

# Databricks CLI configured
databricks configure --token
databricks workspace list
```

## Step 1: Install dbt-databricks

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dbt-databricks
pip install dbt-databricks
```

## Step 2: Initialize dbt Project

```bash
# Create project
dbt init data_platform_dbt

# Navigate to project
cd data_platform_dbt

# Install additional packages
pip install dbt-core dbt-semantic-layer
```

## Step 3: Configure profiles.yml

```yaml
# ~/.dbt/profiles.yml
data_platform:
  target: dev
  outputs:
    dev:
      type: databricks
      host: "{{ env_var('DATABRICKS_HOST') }}"
      http_path: "{{ env_var('DATABRICKS_HTTP_PATH') }}"
      token: "{{ env_var('DATABRICKS_TOKEN') }}"
      schema: "dbt_dev"
      database: "data_platform"
      timeout: 60
      retry_on_timeout: true
      
    prod:
      type: databricks
      host: "{{ env_var('DATABRICKS_HOST') }}"
      http_path: "{{ env_var('DATABRICKS_HTTP_PATH') }}"
      token: "{{ env_var('DATABRICKS_TOKEN') }}"
      schema: "dbt_prod"
      database: "data_platform"
      timeout: 120
      retry_on_timeout: true
```

## Step 4: Configure dbt_project.yml

```yaml
# dbt_project.yml
name: 'data_platform'
version: '1.0.0'

config-version: 2

vars:
  source_schema: bronze
  staging_schema: silver
  analytics_schema: gold

# dbt will look for macros in the macros directory
model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]

target-path: "target"
clean-targets:
  - "target"
  - "dbt_packages"

models:
  data_platform:
    bronze:
      +schema: bronze
      +materialized: table
    silver:
      +schema: silver
      +materialized: table
    gold:
      +schema: gold
      +materialized: table
    mart:
      +schema: analytics
      +materialized: view
```

## Step 5: Create Project Structure

```bash
# Create directories
mkdir -p models/bronze
mkdir -p models/silver
mkdir -p models/gold
mkdir -p models/mart
mkdir -p models/_ staging
mkdir -p macros
mkdir -p tests
mkdir -p seeds
mkdir -p analyses
```

## Step 6: Create Source Definitions

```yaml
# models/_sources.yml
sources:
  - name: bronze
    description: Raw data from ingestion layer
    database: data_platform
    schema: bronze
    tables:
      - name: sales_raw
        description: Raw sales transactions
        identifier: sales_raw
        freshness:
          warn_after: {count: 12, period: hour}
          error_after: {count: 24, period: hour}
        loaded_at_field: _etl_loaded_at
        
      - name: customers_raw
        description: Raw customer data
        identifier: customers_raw
        
      - name: products_raw
        description: Raw product catalog
        identifier: products_raw
```

## Step 7: Create Bronze Models (Staging)

```sql
-- models/bronze/stg_sales.sql
{{
    config(
        materialized='table',
        schema='bronze',
        tags=['bronze', 'sales']
    )
}}

SELECT
    -- Identification
    CAST(file_id AS STRING) AS file_id,
    CAST(row_num AS INT) AS row_num,
    
    -- Business keys
    CAST(order_id AS STRING) AS order_id,
    CAST(customer_id AS STRING) AS customer_id,
    CAST(product_id AS STRING) AS product_id,
    
    -- Order details
    CAST(order_date AS TIMESTAMP) AS order_date,
    CAST(ship_date AS TIMESTAMP) AS ship_date,
    CAST(order_status AS STRING) AS order_status,
    
    -- Financial
    CAST(sale_amount AS DECIMAL(18,2)) AS sale_amount,
    CAST(quantity AS INT) AS quantity,
    CAST(discount AS DECIMAL(5,2)) AS discount_pct,
    CAST(profit AS DECIMAL(18,2)) AS profit,
    
    -- Geography
    CAST(region AS STRING) AS region,
    CAST(country AS STRING) AS country,
    CAST(state AS STRING) AS state,
    CAST(city AS STRING) AS city,
    
    -- Product info
    CAST(category AS STRING) AS category,
    CAST(sub_category AS STRING) AS sub_category,
    CAST(product_name AS STRING) AS product_name,
    
    -- Metadata
    CAST(_file_name AS STRING) AS source_file,
    CURRENT_TIMESTAMP() AS _etl_loaded_at
    
FROM {{ source('bronze', 'sales_raw') }}
```

## Step 8: Create Silver Models (Cleaned)

```sql
-- models/silver/int_sales_cleaned.sql
{{
    config(
        materialized='table',
        schema='silver',
        tags=['silver', 'sales'],
        partition_by=['order_year', 'order_month']
    )
}}

WITH sales_cleaned AS (
    SELECT
        -- Business key with surrogate key generation
        order_id,
        customer_id,
        product_id,
        
        -- Date normalization
        DATE(order_date) AS order_date,
        DATE(ship_date) AS ship_date,
        DATE_DIFF(DATE(ship_date), DATE(order_date)) AS days_to_ship,
        
        -- Order status standardization
        LOWER(TRIM(order_status)) AS order_status,
        
        -- Financial calculations
        sale_amount,
        quantity,
        discount_pct,
        profit,
        sale_amount * (1 - discount_pct) AS net_amount,
        CASE 
            WHEN sale_amount > 0 THEN (profit / sale_amount) * 100 
            ELSE 0 
        END AS profit_margin_pct,
        
        -- Geography (cleaned)
        INITCAP(TRIM(region)) AS region,
        INITCAP(TRIM(country)) AS country,
        INITCAP(TRIM(state)) AS state,
        INITCAP(TRIM(city)) AS city,
        
        -- Product (cleaned)
        TRIM(category) AS category,
        TRIM(sub_category) AS sub_category,
        TRIM(product_name) AS product_name,
        
        -- Time dimensions
        YEAR(order_date) AS order_year,
        MONTH(order_date) AS order_month,
        DAYOFWEEK(order_date) AS order_day_of_week,
        
        -- Metadata
        source_file,
        _etl_loaded_at,
        CURRENT_TIMESTAMP() AS _silver_processed_at
        
    FROM {{ ref('stg_sales') }}
    WHERE order_id IS NOT NULL
      AND order_date IS NOT NULL
)

SELECT
    *,
    -- Data quality flags
    CASE WHEN days_to_ship < 0 THEN TRUE ELSE FALSE END AS is_shipped_before_ordered,
    CASE WHEN profit < 0 THEN TRUE ELSE FALSE END AS is_profit_negative,
    CASE WHEN quantity <= 0 THEN TRUE ELSE FALSE END AS is_invalid_quantity
    
FROM sales_cleaned
```

## Step 9: Create Gold Models (Business Metrics)

```sql
-- models/gold/fct_orders.sql
{{
    config(
        materialized='table',
        schema='gold',
        tags=['gold', 'orders'],
        partition_by=['order_year', 'order_month'],
        cluster_by=['customer_id']
    )
}}

SELECT
    -- Date dimensions
    order_date,
    order_year,
    order_month,
    
    -- Order metrics
    COUNT(DISTINCT order_id) AS total_orders,
    COUNT(*) AS total_line_items,
    SUM(quantity) AS total_units_sold,
    SUM(sale_amount) AS gross_revenue,
    SUM(net_amount) AS net_revenue,
    SUM(profit) AS total_profit,
    AVG(profit_margin_pct) AS avg_profit_margin_pct,
    
    -- Discount metrics
    AVG(discount_pct) AS avg_discount_pct,
    SUM(sale_amount - net_amount) AS total_discount_value,
    
    -- Shipping metrics
    AVG(days_to_ship) AS avg_days_to_ship,
    MAX(days_to_ship) AS max_days_to_ship,
    MIN(days_to_ship) AS min_days_to_ship,
    COUNTIF(days_to_ship < 0) AS count_late_shipments,
    COUNTIF(days_to_ship > 7) AS count_slow_shipments,
    
    -- Quality flags
    SUM(CASE WHEN is_profit_negative THEN 1 ELSE 0 END) AS count_negative_profit,
    SUM(CASE WHEN is_invalid_quantity THEN 1 ELSE 0 END) AS count_invalid_quantity,
    
    -- Metadata
    CURRENT_TIMESTAMP() AS _gold_processed_at
    
FROM {{ ref('int_sales_cleaned') }}
GROUP BY
    order_date,
    order_year,
    order_month
```

## Step 10: Test dbt Setup

```bash
# Test connection
dbt debug

# Compile project
dbt compile

# Run models
dbt run

# Run tests
dbt test

# Generate documentation
dbt docs generate

# Serve documentation locally
dbt docs serve
```

## Step 11: Create Semantic Layer (Optional)

```yaml
# models/metrics.yml
metrics:
  - name: total_revenue
    label: Total Revenue
    model: ref('fct_orders')
    description: Sum of all order revenues
    
    calculation_method: sum
    expression: net_revenue
    
    dimensions:
      - order_year
      - order_month
      - category

  - name: order_count
    label: Order Count
    model: ref('fct_orders')
    
    calculation_method: count
    expression: total_orders
    
    dimensions:
      - order_year
      - order_month
```

## Step 12: Schedule dbt in Airflow

```python
# airflow/dags/dbt_daily_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'data_platform',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'dbt_daily_transform',
    default_args=default_args,
    description='Run dbt transformations daily',
    schedule_interval='0 3 * * *',  # 3 AM daily
    catchup=False,
) as dag:
    
    # Run dbt models
    run_dbt_models = BashOperator(
        task_id='run_dbt_models',
        bash_command='''
            cd /path/to/data_platform_dbt &&
            source venv/bin/activate &&
            dbt run --target prod
        ''',
    )
    
    # Run dbt tests
    run_dbt_tests = BashOperator(
        task_id='run_dbt_tests',
        bash_command='''
            cd /path/to/data_platform_dbt &&
            source venv/bin/activate &&
            dbt test --target prod
        ''',
    )
    
    run_dbt_models >> run_dbt_tests
```

## Common dbt Commands

```bash
# Development
dbt debug                    # Check connection
dbt compile                  # Compile SQL
dbt run                      # Run models
dbt run --select sales+      # Run sales and downstream
dbt test                     # Run tests

# Production
dbt run --target prod        # Production target
dbt run --full-refresh       # Full refresh
dbt run --select +fct_orders # Run upstream + fct_orders

# Documentation
dbt docs generate            # Generate docs
dbt docs serve               # Serve docs locally

# Lineage
dbt list --resource-type model   # List all models
dbt list --select +fct_orders   # Show upstream of fct_orders
dbt list --select fct_orders+   # Show downstream of fct_orders
```

## Troubleshooting

### Lỗi "Connection refused"

```bash
# Check Databricks is running
databricks clusters list

# Verify credentials
export DATABRICKS_HOST=https://dbc-xxxxx.cloud.databricks.com
export DATABRICKS_TOKEN=dapi...
dbt debug
```

### Lỗi "Table not found"

```sql
-- Chạy trong Databricks Notebook trước
CREATE TABLE IF NOT EXISTS data_platform.bronze.sales_raw (
    file_id STRING,
    row_num INT,
    order_id STRING,
    customer_id STRING,
    ...
)
```

### Lỗi "Schema not found"

```sql
-- Tạo schemas trước
CREATE SCHEMA IF NOT EXISTS data_platform.bronze;
CREATE SCHEMA IF NOT EXISTS data_platform.silver;
CREATE SCHEMA IF NOT EXISTS data_platform.gold;
```

## Next Steps

1. ✅ dbt Setup → Xong
2. [dbt Modeling Guide](./dbt-modeling-guide.md) - Advanced patterns
3. [Ingestion Pipeline](../pipelines/ingestion-guide.md)
4. [Transformation Pipeline](../pipelines/transformation-guide.md)
