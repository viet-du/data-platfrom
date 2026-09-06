# Analytics Dashboard Guide

## Overview

Hướng dẫn thiết kế và xây dựng Analytics Dashboard cho Data Platform.

## Dashboard Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ANALYTICS DASHBOARD LAYER                             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      METABASE (Mac-Friendly)                        │   │
│  │                                                                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │   │
│  │  │   Overview   │  │    Sales    │  │  Customer   │             │   │
│  │  │  Dashboard   │  │  Dashboard   │  │  Dashboard   │             │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │   │
│  │                                                                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │   │
│  │  │   Product    │  │  Marketing  │  │ Operations  │             │   │
│  │  │  Dashboard   │  │  Dashboard   │  │  Dashboard   │             │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    DATABRICKS GOLD LAYER                             │   │
│  │                                                                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │   │
│  │  │  dim_*      │  │   fct_*     │  │   agg_*     │             │   │
│  │  │  Tables     │  │   Tables    │  │   Views     │             │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Dashboard Categories

### 1. Executive Overview Dashboard

```markdown
# Executive Overview Dashboard

## KPIs (Key Performance Indicators)
┌─────────────────────────────────────────────────────────────────────────────┐
│  💰 Total Revenue    │  📦 Total Orders   │  👥 Customers  │  📊 Avg Order  │
│  $1,500,000          │  25,000            │  12,500        │  $85.50        │
│  ▲ +12% vs last mo   │  ▲ +8% vs last mo  │  ▲ +5%         │  ▲ +3%         │
└─────────────────────────────────────────────────────────────────────────────┘

## Charts
1. Revenue Trend (Line Chart) - Last 12 months
2. Orders by Day of Week (Bar Chart)
3. Top 10 Products (Horizontal Bar)
4. Revenue by Region (Map or Pie Chart)

## Filters
- Date Range (Last 30/60/90 days, Custom)
- Region
- Product Category
```

### 2. Sales Analytics Dashboard

```markdown
# Sales Analytics Dashboard

## Metrics
- Daily/Weekly/Monthly Revenue
- Order Count
- Average Order Value
- Discount Rate
- Return Rate

## Charts
1. Revenue by Product Category (Pie Chart)
2. Sales Trend by Region (Line Chart)
3. Top 10 Customers by Revenue (Table)
4. Order Status Distribution (Donut Chart)
5. Monthly Revenue Comparison (Bar Chart)

## Tables
- Daily Sales Detail
- Top Products by Revenue
- Customer Purchase History
```

### 3. Customer Analytics Dashboard

```markdown
# Customer Analytics Dashboard

## Customer Metrics
- Total Customers
- New Customers (this month)
- Active Customers (last 30 days)
- Churn Rate
- Customer Lifetime Value

## Charts
1. Customer Growth Trend (Area Chart)
2. Customer Segmentation (Pie Chart)
3. Cohort Retention (Heatmap)
4. LTV Distribution (Histogram)
5. Customer Acquisition by Channel (Bar Chart)

## Tables
- Top 100 Customers by LTV
- At-Risk Customers
- New Customers This Month
```

## Chart Types by Data

| Data Type | Best Chart Types |
|-----------|----------------|
| Trends over time | Line, Area |
| Part-to-whole | Pie, Donut, Stacked Bar |
| Ranking | Bar, Horizontal Bar |
| Distribution | Histogram, Box Plot |
| Relationship | Scatter Plot |
| Geographic | Map |
| Progress | Gauge, Progress Bar |
| Multiple metrics | Combo Chart |

## Dashboard Design Principles

### 1. Information Hierarchy

```
┌─────────────────────────────────────────────┐
│              HEADER                          │
│  Dashboard Title | Filters | Date Range     │
└─────────────────────────────────────────────┘
┌─────────────────────────────────────────────┐
│              KPI CARDS (Row 1)              │
│  [ KPI 1 ] [ KPI 2 ] [ KPI 3 ] [ KPI 4 ]  │
└─────────────────────────────────────────────┘
┌─────────────────────────────────────────────┐
│              CHARTS (Row 2)                │
│  ┌───────────────┐  ┌───────────────┐      │
│  │   Chart 1    │  │   Chart 2    │      │
│  └───────────────┘  └───────────────┘      │
└─────────────────────────────────────────────┘
┌─────────────────────────────────────────────┐
│              CHARTS (Row 3)                │
│  ┌───────────────┐  ┌───────────────┐      │
│  │   Chart 3    │  │   Table 1    │      │
│  └───────────────┘  └───────────────┘      │
└─────────────────────────────────────────────┘
```

### 2. Color Palette

| Purpose | Color | Hex |
|---------|-------|-----|
| Primary | Blue | #4285F4 |
| Success | Green | #34A853 |
| Warning | Yellow | #FBBC05 |
| Danger | Red | #EA4335 |
| Neutral | Gray | #9AA0A6 |
| Background | White | #FFFFFF |
| Text | Dark Gray | #202124 |

### 3. Best Practices

- **Position KPIs at top** - Most important metrics first
- **Use consistent colors** - Same metrics = same color across dashboards
- **Add context** - Include comparisons (vs last period, vs target)
- **Use filters** - Allow users to slice data
- **Limit charts per dashboard** - 6-8 charts max
- **Add tooltips** - Explain what each metric means
- **Mobile responsive** - Test on different screen sizes

## Interactive Features

### Filters

| Filter Type | Use Case |
|-------------|----------|
| Date Range | Time-based analysis |
| Dropdown | Single-select categories |
| Multi-select | Multiple categories |
| Search | Large lists |
| Slider | Numeric ranges |
| Button Group | Quick toggle options |

### Drill-down

```sql
-- Example drill-down query
-- Level 1: Total Revenue
SELECT SUM(net_revenue) AS total_revenue 
FROM data_platform.gold.fct_orders

-- Level 2: Revenue by Category
SELECT category, SUM(net_revenue) AS revenue 
FROM data_platform.gold.fct_orders 
GROUP BY category

-- Level 3: Revenue by Product
SELECT product_name, SUM(net_revenue) AS revenue 
FROM data_platform.gold.fct_orders 
GROUP BY product_name
ORDER BY revenue DESC LIMIT 20
```

### Click-through

```markdown
# Click-through Example

Sales Overview Dashboard
    │
    ├── Click on Region → Region Detail Dashboard
    │
    ├── Click on Customer → Customer Profile
    │
    ├── Click on Product → Product Analysis
    │
    └── Click on Date → Daily Detail View
```

## Metabase Specific Features

### Collections

```
📁 Data Platform
├── 📊 Executive
│   └── Overview Dashboard
├── 📊 Sales
│   ├── Sales Overview
│   ├── Revenue Analysis
│   └── Top Products
├── 📊 Customers
│   ├── Customer Overview
│   └── Cohort Analysis
└── 📁 Reports
    ├── Monthly Report
    └── Weekly Summary
```

### Permissions

| Role | Permissions |
|------|------------|
| Admin | Full access |
| Analyst | View + Edit dashboards |
| Business User | View dashboards |
| Guest | View only public dashboards |

## Dashboard Maintenance

### Regular Tasks

1. **Weekly**
   - Check data freshness
   - Verify filters work
   - Review for outdated content

2. **Monthly**
   - Review performance
   - Archive unused dashboards
   - Update documentation

3. **Quarterly**
   - Review dashboard relevance
   - Gather user feedback
   - Plan improvements

## Performance Tips

| Issue | Solution |
|-------|----------|
| Slow loading | Use summarized tables |
| Too many queries | Cache results |
| Large datasets | Add filters |
| Complex joins | Pre-compute aggregations |

## Related Documentation

- [Metabase Setup Guide](./metabase-setup.md)
- [dbt Modeling Guide](../tools/dbt-modeling-guide.md)
- [Gold Layer Models](../pipelines/transformation-guide.md)
