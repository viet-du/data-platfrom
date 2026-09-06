# DATA STRUCTURE DIAGRAM
# Sơ đồ cấu trúc data từng layer - Dùng để vẽ

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              DATA STRUCTURE - ALL LAYERS                             │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1️⃣ BRONZE LAYER - Data Structure

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              BRONZE LAYER - Data Structure                            │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  sales_raw                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  file_id │ row_num │ order_id │ customer_id │ product_id │ ...      ││
│  ├─────────────────────────────────────────────────────────────────────┤│
│  │  file_001│  1     │ A001    │ C001       │ P001      │          ││
│  │  file_001│  2     │ A002    │ C002       │ P002      │          ││
│  │  file_001│  3     │ A003    │ C003       │ P003      │          ││
│  │  file_002│  1     │ A004    │ C001       │ P002      │          ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  📋 Schema:                                                             │
│  ├── order_id       STRING        NOT NULL                               │
│  ├── customer_id    STRING        NOT NULL                               │
│  ├── product_id     STRING        NOT NULL                               │
│  ├── order_date     TIMESTAMP                                           │
│  ├── ship_date      TIMESTAMP                                           │
│  ├── sale_amount    DECIMAL(18,2)                                      │
│  ├── quantity       INT                                                  │
│  ├── discount       DECIMAL(5,4)                                        │
│  ├── region         STRING                                              │
│  ├── country        STRING                                              │
│  ├── state          STRING                                              │
│  ├── city           STRING                                              │
│  ├── category       STRING                                              │
│  ├── sub_category   STRING                                              │
│  ├── product_name   STRING                                              │
│  ├── _file_name     STRING        (Metadata - source file)               │
│  ├── _etl_loaded_at TIMESTAMP     (Metadata - load timestamp)           │
│  └── _batch_id      STRING        (Metadata - batch identifier)          │
│                                                                         │
│  📊 Statistics:                                                          │
│  ├── Row count: 150,000                                                │
│  ├── File count: 12                                                     │
│  ├── Partition: _etl_loaded_at                                          │
│  └── Last updated: 2024-01-15 02:00:00                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  customers_raw                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  file_id │ row_num │ customer_id │ name │ email │ phone │ ...     ││
│  ├─────────────────────────────────────────────────────────────────────┤│
│  │  cust_001│  1     │ C001       │ John │ john@ │ 1234  │          ││
│  │  cust_001│  2     │ C002       │ Jane │ jane@ │ 5678  │          ││
│  │  cust_001│  3     │ C003       │ Bob  │ bob@  │ 9012  │          ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  📋 Schema:                                                             │
│  ├── customer_id    STRING        NOT NULL, UNIQUE                       │
│  ├── name          STRING                                              │
│  ├── email         STRING                                              │
│  ├── phone         STRING                                              │
│  ├── address       STRING                                              │
│  ├── city          STRING                                              │
│  ├── state         STRING                                              │
│  ├── country       STRING                                              │
│  ├── postal_code   STRING                                              │
│  ├── segment       STRING        (Customer segment)                     │
│  ├── _file_name    STRING        (Metadata)                           │
│  ├── _etl_loaded_at TIMESTAMP     (Metadata)                           │
│  └── _batch_id     STRING        (Metadata)                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  products_raw                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  file_id │ row_num │ product_id │ name │ category │ price │ stock ││
│  ├─────────────────────────────────────────────────────────────────────┤│
│  │  prod_001│  1     │ P001      │ ProdA│ Cat1    │ 99.99│ 100   ││
│  │  prod_001│  2     │ P002      │ ProdB│ Cat1    │ 49.99│ 200   ││
│  │  prod_001│  3     │ P003      │ ProdC│ Cat2    │ 149.9│ 50    ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  📋 Schema:                                                             │
│  ├── product_id     STRING        NOT NULL, UNIQUE                       │
│  ├── product_name   STRING                                              │
│  ├── category       STRING                                              │
│  ├── sub_category   STRING                                              │
│  ├── price         DECIMAL(10,2)                                       │
│  ├── stock_quantity INT                                                 │
│  ├── supplier       STRING                                              │
│  ├── _file_name     STRING        (Metadata)                           │
│  ├── _etl_loaded_at TIMESTAMP     (Metadata)                           │
│  └── _batch_id      STRING        (Metadata)                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2️⃣ SILVER LAYER - Data Structure

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              SILVER LAYER - Data Structure                              │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  stg_sales (Staged Sales - Type Casted)                               │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  order_id │ customer_id │ product_id │ order_date │ net_amount │   ││
│  ├─────────────────────────────────────────────────────────────────────┤│
│  │  A001    │ C001       │ P001      │ 2024-01-01 │ 99.99      │   ││
│  │  A002    │ C002       │ P002      │ 2024-01-02 │ 49.99      │   ││
│  │  A003    │ C003       │ P003      │ 2024-01-03 │ 149.90     │   ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  📋 Schema:                                                             │
│  ├── order_id       STRING        NOT NULL                              │
│  ├── customer_id    STRING        NOT NULL                              │
│  ├── product_id     STRING        NOT NULL                              │
│  ├── order_date     DATE         NOT NULL  ← Type casted               │
│  ├── ship_date      DATE                  ← Type casted                  │
│  ├── order_status   STRING        ← Normalized (lowercase)              │
│  ├── sale_amount    DECIMAL(18,2) ← Type casted                        │
│  ├── quantity       INT           ← Type casted                         │
│  ├── discount_pct   DECIMAL(5,4)  ← Renamed, type casted               │
│  ├── net_amount     DECIMAL(18,2) ← Calculated: amount * (1-discount)  │
│  ├── region         STRING        ← INITCAP                            │
│  ├── country        STRING        ← INITCAP                            │
│  ├── state          STRING        ← INITCAP                            │
│  ├── city           STRING        ← INITCAP                            │
│  ├── category       STRING        ← TRIM                              │
│  ├── sub_category   STRING        ← TRIM                              │
│  ├── order_year     INT           ← Extracted: YEAR(order_date)        │
│  ├── order_month    INT           ← Extracted: MONTH(order_date)        │
│  ├── is_weekend     BOOLEAN      ← Calculated                         │
│  ├── source_file    STRING        ← From _file_name                    │
│  ├── _stg_loaded   TIMESTAMP     ← Metadata                          │
│  └── _bronze_loaded TIMESTAMP     ← From source                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  int_orders_base (Intermediate - Deduplicated)                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  order_id │ customer_id │ product_id │ order_date │ net_amount │   ││
│  ├─────────────────────────────────────────────────────────────────────┤│
│  │  A001    │ C001       │ P001      │ 2024-01-01 │ 99.99      │   ││
│  │  A002    │ C002       │ P002      │ 2024-01-02 │ 49.99      │   ││
│  │  A003    │ C003       │ P003      │ 2024-01-03 │ 149.90     │   ││
│  │  A004    │ C001       │ P002      │ 2024-01-04 │ 45.99      │   ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  📋 Schema:                                                            │
│  ├── order_id         STRING      NOT NULL, UNIQUE ← Deduplicated      │
│  ├── customer_id      STRING      NOT NULL                              │
│  ├── product_id       STRING      NOT NULL                              │
│  ├── order_date       DATE        NOT NULL                              │
│  ├── ship_date        DATE                                           │
│  ├── days_to_ship    INT         ← Calculated: ship_date - order_date │
│  ├── order_status     STRING      ← 'pending', 'shipped', 'delivered' │
│  ├── gross_amount     DECIMAL     ← sale_amount * quantity              │
│  ├── discount_amount  DECIMAL     ← Calculated                         │
│  ├── net_amount       DECIMAL     ← After discount                     │
│  ├── profit           DECIMAL     ← net_amount - cost                  │
│  ├── profit_margin    DECIMAL     ← (profit / net_amount) * 100        │
│  ├── region           STRING                                           │
│  ├── category         STRING                                           │
│  ├── order_year       INT                                             │
│  ├── order_month      INT                                             │
│  ├── order_year_month STRING      ← '2024-01'                         │
│  ├── is_future_date   BOOLEAN    ← Quality flag                       │
│  ├── is_negative_amt  BOOLEAN    ← Quality flag                       │
│  ├── is_invalid_qty   BOOLEAN    ← Quality flag                       │
│  └── _int_processed   TIMESTAMP                                       │
│                                                                         │
│  ✅ Quality Flags:                                                     │
│  ├── is_future_date   → TRUE if order_date > TODAY                     │
│  ├── is_negative_amt  → TRUE if net_amount < 0                        │
│  └── is_invalid_qty  → TRUE if quantity <= 0                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  int_customers_enriched (Intermediate - With Aggregates)                 │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  customer_id │ name │ email │ city │ segment │ total_orders │ ltv ││
│  ├─────────────────────────────────────────────────────────────────────┤│
│  │  C001      │ John │ john@ │ NYC  │ Regular │ 5           │ 500 ││
│  │  C002      │ Jane │ jane@ │ LA   │ Premium │ 12          │1200 ││
│  │  C003      │ Bob  │ bob@  │ CHI  │ VIP     │ 25          │2500 ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  📋 Schema:                                                            │
│  ├── customer_id          STRING      NOT NULL, UNIQUE                  │
│  ├── full_name           STRING                                         │
│  ├── email               STRING      ← Validated format                 │
│  ├── phone               STRING      ← Standardized format               │
│  ├── city                STRING                                         │
│  ├── state               STRING                                         │
│  ├── country             STRING                                         │
│  ├── segment             STRING      ← 'Regular', 'Premium', 'VIP'       │
│  ├── first_order_date    DATE        ← MIN(order_date)                  │
│  ├── last_order_date     DATE        ← MAX(order_date)                  │
│  ├── total_orders        INT         ← COUNT(DISTINCT order_id)          │
│  ├── total_line_items    INT         ← COUNT(*)                          │
│  ├── lifetime_value      DECIMAL     ← SUM(net_amount)                   │
│  ├── avg_order_value    DECIMAL     ← AVG(net_amount)                   │
│  ├── avg_days_to_ship   DECIMAL     ← AVG(days_to_ship)                 │
│  ├── delivered_orders    INT         ← COUNT WHERE status='delivered'    │
│  ├── customer_tenure_days INT        ← DATEDIFF(last, first)            │
│  ├── days_since_last_ord INT        ← DATEDIFF(TODAY, last)           │
│  ├── customer_tier       STRING      ← 'New', 'Active', 'At Risk'       │
│  ├── is_churned          BOOLEAN    ← TRUE if days > 90                 │
│  └── _int_processed      TIMESTAMP                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3️⃣ GOLD LAYER - Data Structure

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              GOLD LAYER - Data Structure                                │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  dim_customers (Dimension Table - Slowly Changing)                     │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  customer_key │ customer_id │ full_name │ email │ city │ ltv │tier││
│  ├─────────────────────────────────────────────────────────────────────┤│
│  │  1001       │ C001       │ John Doe  │ john@ │ NYC  │ 500 │Reg ││
│  │  1002       │ C002       │ Jane Doe  │ jane@ │ LA   │1200 │Prem││
│  │  1003       │ C003       │ Bob Smith │ bob@  │ CHI  │2500 │ VIP ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  📋 Schema:                                                            │
│  ├── customer_key       BIGINT   NOT NULL, UNIQUE ← Surrogate Key      │
│  ├── customer_id       STRING   NOT NULL, UNIQUE ← Business Key       │
│  ├── full_name         STRING   NOT NULL                               │
│  ├── email             STRING   NOT NULL                               │
│  ├── phone             STRING                                           │
│  ├── address           STRING                                           │
│  ├── city              STRING                                           │
│  ├── state             STRING                                           │
│  ├── country           STRING                                           │
│  ├── postal_code       STRING                                           │
│  ├── segment           STRING      ← 'Regular', 'Premium', 'VIP'        │
│  ├── first_order_date  DATE                                           │
│  ├── last_order_date   DATE                                           │
│  ├── total_orders      INT                                             │
│  ├── lifetime_value    DECIMAL                                        │
│  ├── avg_order_value   DECIMAL                                        │
│  ├── customer_tenure   INT        ← Days since first order             │
│  ├── days_since_last   INT        ← Days since last order              │
│  ├── customer_tier     STRING      ← 'New', 'Active', 'At Risk'        │
│  ├── is_active         BOOLEAN    ← TRUE if days_since_last <= 30      │
│  ├── is_churned        BOOLEAN    ← TRUE if days_since_last > 90       │
│  ├── valid_from        TIMESTAMP  ← SCD Type 2                         │
│  ├── valid_to          TIMESTAMP  ← SCD Type 2 (NULL = current)         │
│  └── _dim_processed    TIMESTAMP                                       │
│                                                                         │
│  🎯 Key Design:                                                        │
│  ├── Surrogate Key (customer_key) - Internal use                       │
│  ├── Business Key (customer_id) - External reference                    │
│  └── SCD Type 2 - Track historical changes                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  dim_products (Dimension Table)                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  product_key │ product_id │ product_name │ cat │ sub_cat │ price │  ││
│  ├─────────────────────────────────────────────────────────────────────┤│
│  │  2001       │ P001       │ Product A   │ Elec│ Laptop  │ 999  │  ││
│  │  2002       │ P002       │ Product B   │ Elec│ Phone  │ 699  │  ││
│  │  2003       │ P003       │ Product C   │ Furn│ Chair  │ 199  │  ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  📋 Schema:                                                            │
│  ├── product_key       BIGINT   NOT NULL, UNIQUE ← Surrogate Key      │
│  ├── product_id       STRING   NOT NULL, UNIQUE ← Business Key        │
│  ├── product_name     STRING   NOT NULL                               │
│  ├── category_key     BIGINT   ← FK to dim_categories                │
│  ├── category         STRING   NOT NULL                               │
│  ├── sub_category     STRING                                           │
│  ├── standard_price   DECIMAL                                        │
│  ├── cost             DECIMAL                                        │
│  ├── margin_pct       DECIMAL     ← (price - cost) / price * 100     │
│  ├── stock_quantity   INT                                           │
│  ├── is_active        BOOLEAN    ← TRUE if in stock                   │
│  ├── supplier         STRING                                           │
│  ├── created_date     DATE                                           │
│  ├── valid_from       TIMESTAMP  ← SCD Type 2                        │
│  ├── valid_to         TIMESTAMP  ← SCD Type 2                        │
│  └── _dim_processed   TIMESTAMP                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  dim_dates (Date Dimension - Pre-populated)                           │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  date_key │ date       │ day │ month │ quarter │ year │ is_weekend││
│  ├─────────────────────────────────────────────────────────────────────┤│
│  │  20240101 │ 2024-01-01│  1  │  1   │   Q1   │ 2024│ TRUE      ││
│  │  20240102 │ 2024-01-02│  2  │  1   │   Q1   │ 2024│ FALSE     ││
│  │  20240103 │ 2024-01-03│  3  │  1   │   Q1   │ 2024│ FALSE     ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  📋 Schema:                                                            │
│  ├── date_key          INT      NOT NULL, UNIQUE ← YYYYMMDD format   │
│  ├── date              DATE     NOT NULL                               │
│  ├── day_of_week       INT      ← 1=Sunday, 7=Saturday               │
│  ├── day_name          STRING    ← 'Monday', 'Tuesday', ...           │
│  ├── day_of_month      INT      ← 1-31                               │
│  ├── day_of_year       INT      ← 1-366                             │
│  ├── week_of_year      INT      ← 1-53                               │
│  ├── month             INT      ← 1-12                               │
│  ├── month_name        STRING    ← 'January', 'February', ...         │
│  ├── month_short       STRING    ← 'Jan', 'Feb', ...                 │
│  ├── quarter           INT      ← 1-4                                │
│  ├── quarter_name      STRING    ← 'Q1', 'Q2', 'Q3', 'Q4'           │
│  ├── year              INT      ← 2024                              │
│  ├── year_month       STRING    ← '2024-01'                         │
│  ├── year_quarter      STRING    ← '2024-Q1'                        │
│  ├── is_weekend        BOOLEAN                                     │
│  ├── is_month_start    BOOLEAN                                     │
│  ├── is_month_end      BOOLEAN                                     │
│  ├── is_quarter_start  BOOLEAN                                     │
│  ├── is_quarter_end    BOOLEAN                                     │
│  ├── is_year_start     BOOLEAN                                     │
│  ├── is_year_end       BOOLEAN                                     │
│  ├── fiscal_year       INT      ← If using fiscal calendar           │
│  ├── fiscal_quarter    INT      ← If using fiscal calendar           │
│  └── fiscal_period     INT      ← If using fiscal calendar           │
│                                                                         │
│  💡 Usage:                                                             │
│  └── JOIN fact tables on date_key for time intelligence               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  fct_orders (Fact Table - Daily Aggregates)                           │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  date_key │ cust_key │ loc_key │ orders │ revenue │ profit │margins││
│  ├─────────────────────────────────────────────────────────────────────┤│
│  │  20240101 │  1001   │  3001   │  150  │ 15000  │ 3000  │ 20%  ││
│  │  20240102 │  1002   │  3002   │  175  │ 17500  │ 3500  │ 20%  ││
│  │  20240103 │  1003   │  3003   │  200  │ 20000  │ 4000  │ 20%  ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  📋 Schema:                                                            │
│  ├── date_key          INT      NOT NULL ← FK to dim_dates             │
│  ├── customer_key      BIGINT   ← FK to dim_customers                │
│  ├── product_key      BIGINT   ← FK to dim_products                 │
│  ├── location_key     BIGINT   ← FK to dim_locations                │
│  ├── order_key        BIGINT   ← FK to fct_order_items (if needed)  │
│                                                                         │
│  ├── order_count       INT      ← COUNT(DISTINCT order_id)           │
│  ├── line_item_count   INT      ← COUNT(*)                           │
│  ├── total_quantity    INT      ← SUM(quantity)                      │
│  ├── gross_revenue     DECIMAL  ← SUM(gross_amount)                 │
│  ├── discount_amount   DECIMAL  ← SUM(discount)                     │
│  ├── net_revenue       DECIMAL  ← SUM(net_amount)                    │
│  ├── cost_of_goods     DECIMAL  ← SUM(cost)                          │
│  ├── profit            DECIMAL  ← net_revenue - cost                  │
│  ├── profit_margin_pct DECIMAL  ← (profit / net_revenue) * 100       │
│  ├── avg_order_value   DECIMAL  ← net_revenue / order_count          │
│  ├── avg_quantity      DECIMAL  ← total_quantity / line_item_count    │
│                                                                         │
│  ├── avg_days_to_ship  DECIMAL  ← AVG(days_to_ship)                  │
│  ├── max_days_to_ship  INT      ← MAX(days_to_ship)                  │
│  ├── min_days_to_ship  INT      ← MIN(days_to_ship)                  │
│  ├── late_orders       INT      ← COUNT WHERE days > SLA             │
│                                                                         │
│  ├── negative_profit_cnt INT   ← COUNT WHERE profit < 0              │
│  ├── returned_orders   INT      ← COUNT WHERE status = 'returned'    │
│  └── _fct_processed    TIMESTAMP                                    │
│                                                                         │
│  🎯 Partitioning:                                                     │
│  ├── Partition by: order_year, order_month                           │
│  └── Cluster by: customer_key, product_key                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  agg_daily_metrics (Pre-aggregated for Dashboards)                    │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  date_key │ revenue │ orders │ customers │ avg_order │ profit_margin││
│  ├─────────────────────────────────────────────────────────────────────┤│
│  │  20240101 │ 15000   │  150   │   120     │   100     │    20%     ││
│  │  20240102 │ 17500   │  175   │   140     │   100     │    21%     ││
│  │  20240103 │ 20000   │  200   │   160     │   100     │    22%     ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  📋 Schema:                                                            │
│  ├── date_key          INT      NOT NULL ← FK to dim_dates            │
│  ├── order_year        INT                                           │
│  ├── order_month       INT                                           │
│  ├── order_quarter     INT                                           │
│  ├── order_week        INT                                           │
│                                                                         │
│  ├── total_revenue     DECIMAL                                        │
│  ├── total_orders     INT                                            │
│  ├── total_customers  INT        ← COUNT(DISTINCT customer_id)        │
│  ├── total_quantity   INT                                            │
│  ├── total_profit     DECIMAL                                        │
│                                                                         │
│  ├── avg_order_value   DECIMAL  ← total_revenue / total_orders        │
│  ├── avg_items_per_order DECIMAL ← total_quantity / total_orders       │
│  ├── avg_profit_margin DECIMAL  ← (total_profit / total_revenue) * 100 │
│  ├── conversion_rate   DECIMAL  ← (orders / visitors) * 100          │
│                                                                         │
│  ├── new_customers     INT        ← COUNT WHERE is_new_customer        │
│  ├── returning_customers INT     ← COUNT - new_customers              │
│  ├── repeat_rate       DECIMAL  ← returning / total_customers * 100   │
│                                                                         │
│  ├── online_orders     INT        ← COUNT WHERE channel = 'online'     │
│  ├── offline_orders   INT        ← COUNT WHERE channel = 'offline'    │
│  └── online_pct       DECIMAL    ← online / total_orders * 100        │
│                                                                         │
│  💡 Purpose:                                                          │
│  └── Pre-computed for fast dashboard queries                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4️⃣ DATA RELATIONSHIP DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              DATA RELATIONSHIPS                                        │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                    dim_customers
                    ┌─────────────────┐
                    │ customer_key (PK)│◄──────────┐
                    │ customer_id (BK) │           │
                    │ full_name       │           │
                    │ email           │           │
                    │ ...             │           │
                    └─────────────────┘           │
                           │                     │
                           │ 1:N               │
                           ▼                     │
┌───────────────┐   ┌─────────────────┐         │
│ dim_locations │   │   fct_orders   │         │
│┌─────────────┐│   │ (date_key,    │         │
││location_key ││   │  cust_key,    │         │
││(PK)         ││   │  prod_key,    │         │
││location_id  ││   │  loc_key)      │         │
││(BK)         ││   │                │         │
│└─────────────┘│   │ order_count    │         │
│      ▲        │   │ net_revenue    │         │
│      │        │   │ profit         │         │
│      │ 1:N    │   │ ...           │         │
│      │        │   └───────┬───────┘         │
│      │        │           │                 │
│      │        │           │ 1:N             │
│      │        │           ▼                 │
└──────┼────────┘   ┌─────────────────┐      │
       │            │ dim_products     │      │
       │            │┌───────────────┐│      │
       │            ││ product_key   ││      │
       │            ││ (PK)         ││      │
       │            ││ product_id   ││      │
       │            ││ (BK)         ││      │
       │            │└───────────────┘│      │
       │            └─────────────────┘      │
       │                  ▲                 │
       │                  │ 1:N             │
       │                  │                 │
       │            ┌─────┴─────────┐       │
       │            │ fct_order_items │      │
       │            │               │       │
       │            │ order_item_key │       │
       │            │ order_key (FK) │───────┘
       │            │ product_key(FK) │
       │            │ quantity        │
       │            │ unit_price      │
       │            │ line_amount     │
       │            │ discount        │
       │            │ profit          │
       │            └─────────────────┘
       │
       │
┌──────┴──────────┐
│  dim_dates      │
│┌───────────────┐│
││ date_key (PK)││◄────────────────────┐
││ date          ││                    │
││ day_of_week  ││                    │
││ month         ││                    │
││ quarter       ││                    │
││ year          ││                    │
││ ...           ││                    │
│└───────────────┘│                    │
└────────────────┘                    │
       ▲                              │
       │ 1:N                          │
       │                              │
       │            ┌─────────────────┴───────┐
       │            │                         │
       │            │   fct_orders            │
       │            │   fct_order_items      │
       │            │   agg_daily_metrics    │
       │            │   agg_monthly_revenue  │
       │            └─────────────────────────┘
       │
       │
       └──────────────────────────────────
                    All facts JOIN to dim_dates
```

---

## 5️⃣ COLUMN LINEAGE

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              COLUMN LINEAGE - Example: net_revenue                      │
└─────────────────────────────────────────────────────────────────────────────────────────┘

    BRONZE           SILVER              SILVER               GOLD
    ┌────────┐      ┌────────────┐      ┌─────────────┐     ┌────────────┐
    │sales_raw│      │  stg_sales │      │int_orders   │     │ fct_orders │
    ├────────┤      ├────────────┤      ├─────────────┤     ├────────────┤
    │        │      │            │      │             │     │            │
    │sale_amt│      │sale_amount│─────▶│sale_amount  │     │            │
    │        │      │            │      │             │     │            │
    │quantity│      │quantity   │─────▶│quantity     │     │            │
    │        │      │            │      │             │     │            │
    │discount│      │discount_pct│─────▶│discount_pct │────▶│            │
    │        │      │            │      │             │     │            │
    │        │      │            │      │             │     │            │
    │        │      │            │      │gross_amount│     │            │
    │        │      │            │      │sale_amount │     │            │
    │        │      │            │      │  * qty     │     │            │
    │        │      │            │      │             │     │            │
    │        │      │            │      │             │     │            │
    │        │      │            │      │net_amount  │────▶│ net_revenue│
    │        │      │            │      │gross -     │     │            │
    │        │      │            │      │(gross *    │     │            │
    │        │      │            │      │ discount)  │     │            │
    │        │      │            │      │             │     │            │
    │        │      │            │      │             │     │            │
    │        │      │            │      │             │     │  SUM()     │
    │        │      │            │      │             │────▶│GROUP BY    │
    │        │      │            │      │             │     │ date_key   │
    │        │      │            │      │             │     │            │
    └────────┘      └────────────┘      └─────────────┘     └────────────┘
    
    Transformations:
    1. sale_amount = CAST(sale_amt AS DECIMAL)
    2. discount_pct = CAST(discount AS DECIMAL) / 100
    3. gross_amount = sale_amount * quantity
    4. net_amount = gross_amount * (1 - discount_pct)
    5. net_revenue = SUM(net_amount) GROUP BY date_key
```
