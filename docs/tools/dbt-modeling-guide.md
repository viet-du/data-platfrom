# dbt Modeling Guide

## Overview

Hướng dẫn chi tiết về dbt modeling patterns cho Data Platform.

## 📐 Modeling Layers (Medallion Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│  BRONZE LAYER (Staging)                                    │
│  - Raw data, minimal transformation                        │
│  - Schema-on-read                                          │
│  - Type casting & rename columns                           │
│  - Add metadata columns                                   │
│  - Materialized: TABLE                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  SILVER LAYER (Intermediate)                              │
│  - Cleaned & validated                                    │
│  - Deduplicated                                           │
│  - Business logic initial layer                           │
│  - Data quality checks                                    │
│  - Materialized: TABLE                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  GOLD LAYER (Business Metrics)                             │
│  - Business-ready dimensions & facts                      │
│  - KPIs & metrics                                         │
│  - Materialized: TABLE                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  MART LAYER (Analytics)                                    │
│  - Pre-aggregated views                                   │
│  - Dashboard-ready datasets                                │
│  - Materialized: VIEW (or TABLE)                          │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Naming Conventions

### Table Naming

| Layer | Prefix | Example | Materialization |
|-------|--------|---------|----------------|
| Bronze | `stg_` | `stg_sales` | TABLE |
| Silver | `int_` | `int_orders_enriched` | TABLE |
| Gold | `fct_` / `dim_` | `fct_orders`, `dim_customers` | TABLE |
| Mart | `rpt_` / `agg_` | `rpt_sales_dashboard` | VIEW/TABLE |

### Column Naming

```sql
-- Standard prefixes
sale_amount              -- Measures (nouns)
total_revenue            -- Aggregates (total_ prefix)
avg_days_to_ship         -- Aggregates (avg_ prefix)
is_profit_negative       -- Booleans (is_/has_ prefix)
order_date               -- Dates (suffix _date)
created_at               -- Timestamps (suffix _at)
customer_id              -- Foreign keys (_id suffix)
```

## 🔨 Model Patterns

### Pattern 1: Staging Model (Bronze)

```sql
-- models/bronze/stg_sales.sql
{{
    config(
        materialized='table',
        schema='bronze',
        tags=['bronze', 'staging'],
        pre_hook=[
            'CREATE TABLE IF NOT EXISTS {{ target_schema }}.{{ this.name }} ({{
                dbt_utils.star(from=ref('source_sales'), except=['extra_col'])
            }})'
        ]
    )
}}

SELECT
    -- Direct mapping with alias
    file_id,
    row_num,
    
    -- Type casting
    CAST(order_id AS STRING) AS order_id,
    CAST(order_date AS TIMESTAMP) AS order_date,
    CAST(sale_amount AS DECIMAL(18,2)) AS sale_amount,
    CAST(quantity AS INT) AS quantity,
    
    -- Rename for consistency
    order_status AS source_order_status,
    region AS source_region,
    
    -- Add metadata
    _file_name AS source_file,
    _etl_loaded_at,
    CURRENT_TIMESTAMP() AS _stg_processed_at
    
FROM {{ source('bronze', 'sales_raw') }}
```

### Pattern 2: Intermediate Model (Silver)

```sql
-- models/silver/int_orders_base.sql
{{
    config(
        materialized='table',
        schema='silver',
        tags=['silver', 'intermediate'],
        partition_by=['order_year', 'order_month']
    )
}}

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sales') }}
),

deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY order_id 
            ORDER BY _etl_loaded_at DESC
        ) AS _rn
    FROM source_data
),

cleaned AS (
    SELECT
        -- Business keys
        order_id,
        customer_id,
        product_id,
        
        -- Date fields (standardized)
        DATE(order_date) AS order_date,
        COALESCE(DATE(ship_date), DATE(order_date) + INTERVAL '7' DAY) AS ship_date,
        
        -- Status standardization
        LOWER(TRIM(order_status)) AS order_status,
        
        -- Geography (cleaned)
        INITCAP(TRIM(region)) AS region,
        TRIM(country) AS country,
        TRIM(state) AS state,
        TRIM(city) AS city,
        
        -- Financial (calculated)
        sale_amount,
        quantity,
        sale_amount * quantity AS gross_line_amount,
        sale_amount * (1 - COALESCE(discount_pct, 0)) AS net_line_amount,
        
        -- Time dimensions
        YEAR(order_date) AS order_year,
        MONTH(order_date) AS order_month,
        CONCAT(
            YEAR(order_date), '-',
            LPAD(MONTH(order_date), 2, '0')
        ) AS order_year_month,
        
        -- Quality flag
        CASE 
            WHEN order_id IS NULL THEN TRUE 
            ELSE FALSE 
        END AS is_missing_order_id,
        
        -- Metadata
        source_file,
        _etl_loaded_at
        
    FROM deduplicated
    WHERE _rn = 1  -- Deduplication
)

SELECT * FROM cleaned
```

### Pattern 3: Dimension Model (Gold)

```sql
-- models/gold/dim_customers.sql
{{
    config(
        materialized='table',
        schema='gold',
        tags=['gold', 'dimension'],
        cluster_by=['customer_id']
    )
}}

WITH customer_source AS (
    SELECT * FROM {{ ref('int_customers_base') }}
    WHERE is_current = TRUE
),

customer_aggregates AS (
    SELECT
        customer_id,
        COUNT(*) AS total_orders,
        SUM(total_amount) AS lifetime_value,
        AVG(total_amount) AS avg_order_value,
        MIN(first_order_date) AS first_order_date,
        MAX(last_order_date) AS last_order_date,
        DATEDIFF(MAX(last_order_date), MIN(first_order_date)) AS customer_tenure_days
    FROM {{ ref('int_orders_base') }}
    GROUP BY customer_id
),

enriched AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.email,
        c.phone,
        c.city,
        c.state,
        c.country,
        c.segment,
        
        -- From aggregates
        COALESCE(a.total_orders, 0) AS total_orders,
        COALESCE(a.lifetime_value, 0) AS lifetime_value,
        COALESCE(a.avg_order_value, 0) AS avg_order_value,
        a.first_order_date,
        a.last_order_date,
        a.customer_tenure_days,
        
        -- Calculated metrics
        CASE 
            WHEN a.customer_tenure_days > 0 
            THEN ROUND(a.total_orders / (a.customer_tenure_days / 365.0), 2)
            ELSE 0 
        END AS orders_per_year,
        
        CASE 
            WHEN a.first_order_date IS NOT NULL 
            THEN DATEDIFF(CURRENT_DATE, a.first_order_date)
            ELSE 0 
        END AS days_since_first_order,
        
        -- Customer segment
        CASE
            WHEN COALESCE(a.lifetime_value, 0) >= 10000 THEN 'VIP'
            WHEN COALESCE(a.lifetime_value, 0) >= 5000 THEN 'Premium'
            WHEN COALESCE(a.lifetime_value, 0) >= 1000 THEN 'Regular'
            ELSE 'New'
        END AS customer_tier,
        
        -- Metadata
        CURRENT_TIMESTAMP() AS _dim_processed_at,
        CURRENT_TIMESTAMP() AS valid_from,
        NULL AS valid_to
        
    FROM customer_source c
    LEFT JOIN customer_aggregates a ON c.customer_id = a.customer_id
)

SELECT * FROM enriched
```

### Pattern 4: Fact Model (Gold)

```sql
-- models/gold/fct_orders.sql
{{
    config(
        materialized='table',
        schema='gold',
        tags=['gold', 'fact'],
        partition_by=['order_year', 'order_month'],
        unique_key=['order_id', 'line_item_id']
    )
}}

WITH order_lines AS (
    SELECT * FROM {{ ref('int_orders_clean') }}
),

daily_aggregates AS (
    SELECT
        -- Date
        order_date,
        order_year,
        order_month,
        DAYOFWEEK(order_date) AS day_of_week,
        
        -- Product dimensions
        product_id,
        category,
        sub_category,
        
        -- Customer dimensions
        customer_id,
        customer_segment,
        customer_tier,
        
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
        SUM(net_amount) AS net_revenue,
        SUM(profit) AS total_profit,
        AVG(profit_margin_pct) AS avg_profit_margin,
        SUM(discount_amount) AS total_discount,
        
        -- Shipping
        AVG(days_to_ship) AS avg_days_to_ship,
        MAX(days_to_ship) AS max_days_to_ship,
        
        -- Quality metrics
        SUM(CASE WHEN is_profit_negative THEN 1 ELSE 0 END) AS negative_profit_count,
        SUM(CASE WHEN is_late_shipment THEN 1 ELSE 0 END) AS late_shipment_count,
        
        -- Metadata
        CURRENT_TIMESTAMP() AS _fct_processed_at
        
    FROM order_lines
    GROUP BY
        order_date, order_year, order_month, DAYOFWEEK(order_date),
        product_id, category, sub_category,
        customer_id, customer_segment, customer_tier,
        region, country, state, city
)

SELECT * FROM daily_aggregates
```

### Pattern 5: Mart/Report Model

```sql
-- models/mart/rpt_sales_dashboard.sql
{{
    config(
        materialized='view',
        schema='analytics',
        tags=['mart', 'dashboard']
    )
}}

WITH sales_summary AS (
    SELECT
        order_year,
        order_month,
        category,
        region,
        SUM(net_revenue) AS revenue,
        SUM(total_profit) AS profit,
        COUNT(DISTINCT order_id) AS orders
    FROM {{ ref('fct_orders') }}
    GROUP BY
        order_year, order_month, category, region
),

ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY order_year, order_month
            ORDER BY revenue DESC
        ) AS revenue_rank,
        ROW_NUMBER() OVER (
            PARTITION BY order_year, order_month
            ORDER BY profit DESC
        ) AS profit_rank
    FROM sales_summary
)

SELECT
    order_year,
    order_month,
    category,
    region,
    revenue,
    profit,
    orders,
    ROUND(profit / NULLIF(revenue, 0) * 100, 2) AS profit_margin_pct,
    revenue_rank,
    profit_rank
FROM ranked
```

## 🧪 Testing Patterns

### Not Null Tests

```yaml
# models/_schema.yml
models:
  - name: dim_customers
    columns:
      - name: customer_id
        tests:
          - not_null
          - unique
          
      - name: customer_name
        tests:
          - not_null
          
      - name: email
        tests:
          - not_null
          - unique
```

### Relationship Tests

```yaml
models:
  - name: fct_orders
    columns:
      - name: customer_id
        tests:
          - relationships:
              to: ref('dim_customers')
              field: customer_id
              severity: error
```

### Custom Generic Tests

```sql
-- macros/custom_tests.sql
{% test no_future_dates(model, column_name) %}
SELECT
    *
FROM {{ model }}
WHERE {{ column_name }} > CURRENT_DATE()
{% endtest %}

{% test positive_values(model, column_name) %}
SELECT
    *
FROM {{ model }}
WHERE {{ column_name }} < 0
{% endtest %}
```

## 🔄 Incremental Models

```sql
-- models/gold/fct_orders_incremental.sql
{{
    config(
        materialized='incremental',
        schema='gold',
        unique_key='order_id',
        partition_by=['order_year', 'order_month'],
        incremental_strategy='merge'
    )
}}

WITH source_data AS (
    SELECT * FROM {{ ref('int_orders_clean') }}
    {% if is_incremental() %}
    WHERE order_date > (SELECT MAX(order_date) FROM {{ this }})
    {% endif %}
),

aggregated AS (
    SELECT
        order_date,
        order_year,
        order_month,
        order_id,
        customer_id,
        product_id,
        SUM(net_amount) AS net_revenue,
        SUM(profit) AS profit
    FROM source_data
    GROUP BY
        order_date, order_year, order_month,
        order_id, customer_id, product_id
)

SELECT * FROM aggregated
```

## 📊 Data Quality Framework

```python
# macros/run_data_quality.py
{% macro run_data_quality_check(model_name) %}
    
    {% set query = "
        SELECT 
            COUNT(*) as total_rows,
            COUNT(DISTINCT order_id) as unique_orders,
            SUM(CASE WHEN order_id IS NULL THEN 1 ELSE 0 END) as null_order_ids
        FROM " + model_name %}
    
    {{ log('Running data quality check for: ' + model_name, info=True) }}
    
{% endmacro %}
```

## 🎯 Best Practices

### 1. Use Descriptive Aliases

```sql
-- ❌ Bad
SELECT a.id, b.id FROM table1 a, table2 b

-- ✅ Good
SELECT 
    customers.customer_id,
    orders.order_id
FROM dim_customers customers
JOIN fct_orders orders ON customers.customer_id = orders.customer_id
```

### 2. Comment Complex Logic

```sql
-- Calculate customer lifetime value using 3-year window
-- LTV = SUM(orders) * (avg_order_value) * (expected_lifetime_years)
lifetime_value AS (
    SELECT
        customer_id,
        SUM(total_amount) * AVG(order_value) * 3 AS ltv_3year
    FROM orders
    GROUP BY customer_id
)
```

### 3. Handle NULLs Explicitly

```sql
-- Always use COALESCE for important fields
COALESCE(discount_pct, 0) AS discount_pct
COALESCE(sale_amount, 0) AS sale_amount
```

### 4. Use Config Blocks Consistently

```sql
{{
    config(
        materialized='table',        -- Required
        schema='gold',                 -- Required
        tags=['gold', 'sales'],        -- Recommended
        partition_by=['order_date'],  -- For large tables
        cluster_by=['customer_id']     -- For JOIN performance
    )
}}
```

## Related Documentation

- [dbt Quickstart](./dbt-quickstart.md) - Basic setup
- [Transformation Pipeline](../pipelines/transformation-guide.md)
- [Data Quality Strategy](../testing/strategy.md)
