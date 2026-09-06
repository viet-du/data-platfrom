# Transformation Pipeline Guide

## Overview

Hướng dẫn thiết kế và vận hành data transformation pipeline sử dụng dbt và Databricks.

## Transformation Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TRANSFORMATION PIPELINE                              │
│                                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐               │
│  │   BRONZE     │────▶│   SILVER    │────▶│    GOLD     │               │
│  │   (Raw)      │     │  (Cleaned)  │     │  (Metrics)  │               │
│  │              │     │              │     │              │               │
│  │ stg_sales   │     │ int_orders   │     │ dim_*       │               │
│  │ stg_cust    │     │ int_cust    │     │ fct_*       │               │
│  │ stg_prod    │     │ int_prod    │     │ agg_*       │               │
│  └──────────────┘     └──────────────┘     └──────────────┘               │
│         │                   │                    │                          │
│         ▼                   ▼                    ▼                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    DATA QUALITY CHECKS                               │   │
│  │  - Not null tests    - Unique tests    - Relationship tests          │   │
│  │  - Accepted ranges   - String patterns  - Custom validations         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    MONITORING & LOGGING                              │   │
│  │  - Row counts        - Column stats       - Processing time          │   │
│  │  - Error rates       - Success/failure    - SLA compliance           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## dbt Project Structure

```
data_platform_dbt/
├── dbt_project.yml
├── profiles.yml
├── packages.yml
│
├── models/
│   ├── _sources.yml              # Source definitions
│   ├── _schema.yml               # Schema tests
│   ├── _metrics.yml              # Metrics definitions
│   │
│   ├── bronze/                   # Staging layer
│   │   ├── stg_sales.sql
│   │   ├── stg_customers.sql
│   │   ├── stg_products.sql
│   │   └── _bronze_config.yml
│   │
│   ├── silver/                   # Intermediate layer
│   │   ├── int_orders_base.sql
│   │   ├── int_customers_base.sql
│   │   ├── int_products_base.sql
│   │   ├── int_orders_enriched.sql
│   │   └── _silver_config.yml
│   │
│   ├── gold/                     # Business layer
│   │   ├── dim_customers.sql
│   │   ├── dim_products.sql
│   │   ├── dim_dates.sql
│   │   ├── fct_orders.sql
│   │   ├── fct_order_items.sql
│   │   ├── agg_daily_metrics.sql
│   │   └── _gold_config.yml
│   │
│   └── mart/                     # Analytics layer
│       ├── rpt_sales_dashboard.sql
│       ├── rpt_customer_analysis.sql
│       └── _mart_config.yml
│
├── macros/
│   ├── _utils.sql
│   ├── data_quality_tests.sql
│   ├── audit_columns.sql
│   └── get_column_list.sql
│
├── seeds/
│   └── dim_date_seed.csv         # Date dimension seed
│
├── tests/
│   ├── bronze/
│   ├── silver/
│   └── gold/
│
└── logs/
```

## Bronze Layer (Staging)

```sql
-- models/bronze/stg_sales.sql
{{
    config(
        materialized = 'table',
        schema = 'bronze',
        tags = ['bronze', 'sales'],
        pre_hook = [
            "ALTER TABLE {{ target_database }}.{{ target_schema }}.{{ this.name }}
             SET TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = true)"
        ]
    )
}}

SELECT
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
    CAST(discount AS DECIMAL(5,4)) AS discount,
    
    -- Geography
    CAST(region AS STRING) AS region,
    CAST(country AS STRING) AS country,
    CAST(state AS STRING) AS state,
    CAST(city AS STRING) AS city,
    CAST(postal_code AS STRING) AS postal_code,
    
    -- Product
    CAST(category AS STRING) AS category,
    CAST(sub_category AS STRING) AS sub_category,
    CAST(product_name AS STRING) AS product_name,
    
    -- Metadata
    _file_name AS source_file,
    _etl_loaded_at,
    CURRENT_TIMESTAMP() AS _bronze_processed_at
    
FROM {{ source('bronze', 'sales_raw') }}
WHERE order_id IS NOT NULL
```

## Silver Layer (Cleaned)

```sql
-- models/silver/int_orders_base.sql
{{
    config(
        materialized = 'table',
        schema = 'silver',
        tags = ['silver', 'orders'],
        partition_by = ['order_year', 'order_month'],
        cluster_by = ['customer_id']
    )
}}

WITH deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY order_id
            ORDER BY _etl_loaded_at DESC
        ) AS _rn
    FROM {{ ref('stg_sales') }}
),

cleaned AS (
    SELECT
        -- Keys
        order_id,
        customer_id,
        product_id,
        
        -- Date standardization
        DATE(FROM_UTC_TIMESTAMP(order_date, 'UTC')) AS order_date,
        DATE(FROM_UTC_TIMESTAMP(ship_date, 'UTC')) AS ship_date,
        
        -- Status standardization
        LOWER(TRIM(order_status)) AS order_status,
        
        -- Financial calculations
        sale_amount,
        quantity,
        sale_amount * quantity AS gross_amount,
        sale_amount * COALESCE(discount, 0) AS discount_amount,
        sale_amount * (1 - COALESCE(discount, 0)) AS net_amount,
        
        -- Geography (cleaned)
        INITCAP(TRIM(region)) AS region,
        INITCAP(TRIM(country)) AS country,
        INITCAP(TRIM(state)) AS state,
        INITCAP(TRIM(city)) AS city,
        TRIM(postal_code) AS postal_code,
        
        -- Product (cleaned)
        TRIM(category) AS category,
        TRIM(sub_category) AS sub_category,
        TRIM(product_name) AS product_name,
        
        -- Time dimensions
        YEAR(order_date) AS order_year,
        MONTH(order_date) AS order_month,
        CONCAT(
            YEAR(order_date), '-',
            LPAD(MONTH(order_date), 2, '0')
        ) AS year_month,
        DAYOFWEEK(order_date) AS day_of_week,
        CASE 
            WHEN DAYOFWEEK(order_date) IN (1, 7) THEN TRUE 
            ELSE FALSE 
        END AS is_weekend,
        
        -- Quality flags
        CASE WHEN order_date > CURRENT_DATE() THEN TRUE ELSE FALSE END AS is_future_date,
        CASE WHEN sale_amount < 0 THEN TRUE ELSE FALSE END AS is_negative_amount,
        CASE WHEN quantity <= 0 THEN TRUE ELSE FALSE END AS is_invalid_quantity,
        
        -- Metadata
        source_file,
        _etl_loaded_at,
        _bronze_processed_at
        
    FROM deduplicated
    WHERE _rn = 1
)

SELECT * FROM cleaned
```

## Gold Layer (Business Metrics)

### Dimension Tables

```sql
-- models/gold/dim_customers.sql
{{
    config(
        materialized = 'table',
        schema = 'gold',
        tags = ['gold', 'dimension'],
        cluster_by = ['customer_id'],
        pre_hook = [
            "OPTIMIZE {{ this }} ZORDER BY (customer_id)"
        ]
    )
}}

WITH customer_orders AS (
    SELECT
        customer_id,
        MIN(order_date) AS first_order_date,
        MAX(order_date) AS last_order_date,
        COUNT(DISTINCT order_id) AS total_orders,
        COUNT(*) AS total_line_items,
        SUM(net_amount) AS lifetime_value,
        AVG(net_amount) AS avg_order_value,
        SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END) AS delivered_orders
    FROM {{ ref('int_orders_base') }}
    GROUP BY customer_id
),

final AS (
    SELECT
        customer_id,
        
        -- Order metrics
        total_orders,
        total_line_items,
        lifetime_value,
        avg_order_value,
        delivered_orders,
        
        -- Date metrics
        first_order_date,
        last_order_date,
        DATEDIFF(last_order_date, first_order_date) AS customer_tenure_days,
        DATEDIFF(CURRENT_DATE, last_order_date) AS days_since_last_order,
        
        -- Calculated metrics
        ROUND(
            lifetime_value / NULLIF(total_orders, 0), 2
        ) AS avg_order_value_calc,
        
        CASE
            WHEN lifetime_value >= 10000 THEN 'VIP'
            WHEN lifetime_value >= 5000 THEN 'Premium'
            WHEN lifetime_value >= 1000 THEN 'Regular'
            ELSE 'New'
        END AS customer_tier,
        
        CASE
            WHEN days_since_last_order <= 30 THEN 'Active'
            WHEN days_since_last_order <= 90 THEN 'At Risk'
            ELSE 'Churned'
        END AS customer_status,
        
        -- Metadata
        CURRENT_TIMESTAMP() AS _dim_processed_at
        
    FROM customer_orders
)

SELECT * FROM final
```

### Fact Tables

```sql
-- models/gold/fct_orders.sql
{{
    config(
        materialized = 'table',
        schema = 'gold',
        tags = ['gold', 'fact'],
        partition_by = ['order_year', 'order_month'],
        pre_hook = [
            "OPTIMIZE {{ this }} ZORDER BY (order_id, customer_id)"
        ]
    )
}}

WITH daily_orders AS (
    SELECT
        -- Date dimensions
        order_date,
        order_year,
        order_month,
        
        -- Customer dimensions
        customer_id,
        
        -- Product dimensions
        product_id,
        category,
        sub_category,
        
        -- Geography
        region,
        country,
        state,
        city,
        
        -- Metrics
        COUNT(DISTINCT order_id) AS order_count,
        COUNT(*) AS line_item_count,
        SUM(quantity) AS total_quantity,
        SUM(gross_amount) AS gross_revenue,
        SUM(discount_amount) AS total_discount,
        SUM(net_amount) AS net_revenue,
        
        -- Quality metrics
        SUM(CASE WHEN is_negative_amount THEN 1 ELSE 0 END) AS negative_amount_count,
        SUM(CASE WHEN is_invalid_quantity THEN 1 ELSE 0 END) AS invalid_quantity_count,
        
        -- Metadata
        CURRENT_TIMESTAMP() AS _fct_processed_at
        
    FROM {{ ref('int_orders_base') }}
    WHERE order_date IS NOT NULL
    GROUP BY
        order_date, order_year, order_month,
        customer_id, product_id, category, sub_category,
        region, country, state, city
)

SELECT * FROM daily_orders
```

## Data Quality Tests

```yaml
# models/_schema.yml
version: 2

models:
  - name: stg_sales
    description: Staged sales data
    columns:
      - name: order_id
        tests:
          - not_null
          - unique
      - name: customer_id
        tests:
          - not_null
      - name: sale_amount
        tests:
          - not_null
      - name: quantity
        tests:
          - not_null

  - name: int_orders_base
    description: Cleaned orders data
    columns:
      - name: order_id
        tests:
          - not_null
          - unique
      - name: net_amount
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min: 0
      - name: order_date
        tests:
          - not_null
          - dbt_utils.recency:
              datepart: day
              interval: 1
              field: order_date
```

## Transformation Scheduling

```bash
# Shell script: run_transformation.sh
#!/bin/bash
set -e

export DBT_TARGET=${1:-prod}
export DATABRICKS_HOST=$DATABRICKS_HOST
export DATABRICKS_TOKEN=$DATABRICKS_TOKEN

cd /path/to/data_platform_dbt

# Activate virtual environment
source ../venv/bin/activate

# Run Bronze (staging)
echo "Running Bronze layer..."
dbt run --target $DBT_TARGET --select tag:bronze

# Run tests on Bronze
echo "Testing Bronze layer..."
dbt test --target $DBT_TARGET --select tag:bronze

# Run Silver
echo "Running Silver layer..."
dbt run --target $DBT_TARGET --select tag:silver

# Run tests on Silver
echo "Testing Silver layer..."
dbt test --target $DBT_TARGET --select tag:silver

# Run Gold
echo "Running Gold layer..."
dbt run --target $DBT_TARGET --select tag:gold

# Run tests on Gold
echo "Testing Gold layer..."
dbt test --target $DBT_TARGET --select tag:gold

# Generate documentation
echo "Generating documentation..."
dbt docs generate --target $DBT_TARGET

echo "Transformation complete!"
```

## Monitoring Transformations

```python
# pipelines/monitor_transformation.py
"""
Monitor dbt transformation runs
"""
import logging
from datetime import datetime
from typing import Dict, List

from src.utils.logging_config import get_logger
from src.utils.alerting import send_alert

logger = get_logger(__name__)


class TransformationMonitor:
    """Monitor dbt transformation results"""
    
    def __init__(self):
        self.run_history = []
    
    def on_run_start(self, target: str):
        """Called when dbt run starts"""
        logger.info(f"dbt run started: target={target}")
        self.current_run = {
            'target': target,
            'start_time': datetime.now(),
            'models': []
        }
    
    def on_model_complete(self, model: str, status: str, duration: float):
        """Called when a model completes"""
        logger.info(f"Model {model}: {status} ({duration:.1f}s)")
        self.current_run['models'].append({
            'model': model,
            'status': status,
            'duration': duration
        })
    
    def on_run_complete(self):
        """Called when dbt run completes"""
        self.current_run['end_time'] = datetime.now()
        self.current_run['duration'] = (
            self.current_run['end_time'] - self.current_run['start_time']
        ).total_seconds()
        
        # Calculate metrics
        total_models = len(self.current_run['models'])
        successful = sum(
            1 for m in self.current_run['models'] 
            if m['status'] == 'success'
        )
        failed = sum(
            1 for m in self.current_run['models'] 
            if m['status'] == 'error'
        )
        
        self.current_run['summary'] = {
            'total': total_models,
            'successful': successful,
            'failed': failed
        }
        
        # Store in history
        self.run_history.append(self.current_run)
        
        # Alert on failures
        if failed > 0:
            send_alert(
                severity='error',
                title=f"dbt Run Failed: {failed}/{total_models} models",
                message=f"Target: {self.current_run['target']}\n"
                        f"Failed models: {[m['model'] for m in self.current_run['models'] if m['status'] == 'error']}"
            )
        
        logger.info(
            f"dbt run complete: {successful}/{total_models} successful "
            f"in {self.current_run['duration']:.1f}s"
        )
```

## Performance Tuning

### Partitioning Strategy

```sql
-- Partition by date for time-series data
{{ config(
    partition_by = ['order_year', 'order_month']
) }}

-- Use Z-ORDER for frequently filtered columns
-- In post-hook
"OPTIMIZE {{ this }} ZORDER BY (customer_id, product_id)"
```

### Clustering Strategy

```sql
-- Cluster by high-cardinality columns used in JOINs
{{ config(
    cluster_by = ['customer_id', 'product_id']
) }}
```

### Materialization Strategy

| Layer | Materialization | When |
|-------|----------------|------|
| Bronze | TABLE | Always full reload |
| Silver | TABLE | Daily refresh |
| Gold | TABLE | Daily refresh |
| Mart | VIEW | Always current |

## Related Documentation

- [dbt Modeling Guide](../tools/dbt-modeling-guide.md)
- [dbt Quickstart](../tools/dbt-quickstart.md)
- [Airflow DAG Guide](../tools/airflow-dag-guide.md)
