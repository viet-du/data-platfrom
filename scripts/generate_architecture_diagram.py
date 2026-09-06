#!/usr/bin/env python3
"""
Data Platform Architecture Diagram Generator
Creates a professional, visually appealing architecture diagram
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, ConnectionPatch
import numpy as np

# Set style
plt.style.use('default')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['SF Pro Display', 'Helvetica Neue', 'Arial', 'DejaVu Sans']
plt.rcParams['font.size'] = 10

def create_architecture_diagram():
    fig, ax = plt.subplots(1, 1, figsize=(22, 16))
    ax.set_xlim(0, 22)
    ax.set_ylim(0, 16)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Color palette
    colors = {
        'source': '#2E7D32',        # Green
        'bronze': '#E65100',        # Orange
        'silver': '#1565C0',        # Blue
        'gold': '#F57F17',          # Yellow/Gold
        'serving': '#6A1B9A',       # Purple
        'orchestration': '#455A64', # Blue Grey
        'logging': '#5D4037',        # Brown
        'arrow': '#37474F',         # Dark Grey
        'bg': '#FAFAFA',            # Light Grey Background
        'white': '#FFFFFF',
        'text_dark': '#212121',
        'text_light': '#FFFFFF',
        'dbt': '#7B1FA2',           # Purple for dbt
    }
    
    # Background
    fig.patch.set_facecolor(colors['bg'])
    ax.set_facecolor(colors['bg'])
    
    # Title
    ax.text(11, 15.5, 'DATA PLATFORM ARCHITECTURE', fontsize=26, fontweight='bold',
            ha='center', va='center', color=colors['text_dark'])
    ax.text(11, 14.9, 'End-to-End Data Pipeline with Delta Lake', fontsize=14,
            ha='center', va='center', color='#616161', style='italic')
    
    # ============ DATA SOURCES LAYER ============
    source_box = FancyBboxPatch((0.3, 12.8), 3.2, 2, boxstyle="round,pad=0.05",
                                 facecolor=colors['source'], edgecolor='#1B5E20', linewidth=3)
    ax.add_patch(source_box)
    ax.text(1.9, 14.5, 'DATA SOURCES', fontsize=12, fontweight='bold',
            ha='center', va='center', color=colors['text_light'])
    
    # Source items with icons
    sources = [
        ('[G] Google Drive', 'CSV / Excel'),
        ('[API] REST APIs', 'JSON'),
        ('[+] Manual Upload', 'Via FastAPI'),
    ]
    for i, (name, format_) in enumerate(sources):
        ax.text(1.9, 13.9 - i*0.55, name, fontsize=9, fontweight='bold', ha='center', va='center', color=colors['text_light'])
        ax.text(1.9, 13.6 - i*0.55, format_, fontsize=8, ha='center', va='center', color='#C8E6C9')
    
    # ============ RAW LAYER (Google Drive) ============
    raw_box = FancyBboxPatch((4.2, 12.8), 3.8, 2, boxstyle="round,pad=0.05",
                             facecolor='#FFF3E0', edgecolor=colors['bronze'], linewidth=3)
    ax.add_patch(raw_box)
    ax.text(6.1, 14.5, 'RAW LAYER', fontsize=12, fontweight='bold',
            ha='center', va='center', color=colors['bronze'])
    ax.text(6.1, 13.9, 'Google Drive', fontsize=9, ha='center', va='center', color='#BF360C')
    
    raw_paths = ['/raw/sources/', '/raw/api_responses/', '/raw/manual_uploads/']
    for i, path in enumerate(raw_paths):
        ax.text(6.1, 13.3 - i*0.4, path, fontsize=7, ha='center', va='center', color='#E65100')
    
    # Arrow from sources to raw
    ax.annotate('', xy=(4.2, 13.8), xytext=(3.5, 13.8),
                arrowprops=dict(arrowstyle='->', color=colors['arrow'], lw=2.5))
    
    # ============ INGESTION ARROW ============
    ax.annotate('', xy=(8.5, 13.8), xytext=(8, 13.8),
                arrowprops=dict(arrowstyle='->', color=colors['arrow'], lw=2.5))
    ax.text(8.25, 14.4, 'Python', fontsize=9, ha='center', va='center', color='#616161', fontweight='bold')
    ax.text(8.25, 14.1, 'Scripts', fontsize=8, ha='center', va='center', color='#9E9E9E')
    
    # ============ DELTA LAKE LAYER ============
    # Bronze Box
    bronze_box = FancyBboxPatch((9, 10.5), 3.8, 4.3, boxstyle="round,pad=0.1",
                                facecolor='#FFF8E1', edgecolor=colors['bronze'], linewidth=3)
    ax.add_patch(bronze_box)
    ax.text(10.9, 14.4, 'BRONZE', fontsize=13, fontweight='bold',
            ha='center', va='center', color=colors['bronze'])
    ax.text(10.9, 13.8, '(Raw Tables)', fontsize=10, ha='center', va='center', color='#F57C00')
    
    # Bronze tables
    bronze_tables = ['stg_sales', 'stg_customers', 'stg_products']
    for i, table in enumerate(bronze_tables):
        table_box = FancyBboxPatch((9.2, 13.0 - i*0.65), 3.4, 0.5,
                                    boxstyle="round,pad=0.02",
                                    facecolor=colors['bronze'], edgecolor='#BF360C', linewidth=1.5)
        ax.add_patch(table_box)
        ax.text(10.9, 13.25 - i*0.65, table, fontsize=9, ha='center', va='center', color=colors['text_light'])
    
    ax.text(10.9, 11.0, '100% Raw Data', fontsize=8, ha='center', va='center', color='#BF360C', fontweight='bold')
    ax.text(10.9, 10.6, 'Schema-on-read', fontsize=7, ha='center', va='center', color='#795548')
    ax.text(10.9, 10.3, 'Add metadata', fontsize=7, ha='center', va='center', color='#795548')
    
    # Arrow Bronze -> Silver
    ax.annotate('', xy=(13.8, 14.5), xytext=(12.8, 14.5),
                arrowprops=dict(arrowstyle='->', color=colors['silver'], lw=3))
    ax.text(13.3, 14.9, 'dbt', fontsize=8, ha='center', va='center', color=colors['dbt'], fontweight='bold')
    
    # Silver Box
    silver_box = FancyBboxPatch((14.5, 10.5), 3.8, 4.3, boxstyle="round,pad=0.1",
                                 facecolor='#E3F2FD', edgecolor=colors['silver'], linewidth=3)
    ax.add_patch(silver_box)
    ax.text(16.4, 14.4, 'SILVER', fontsize=13, fontweight='bold',
            ha='center', va='center', color=colors['silver'])
    ax.text(16.4, 13.8, '(Cleaned)', fontsize=10, ha='center', va='center', color='#0D47A1')
    
    # Silver tables
    silver_tables = ['int_orders', 'int_customers', 'int_products']
    for i, table in enumerate(silver_tables):
        table_box = FancyBboxPatch((14.7, 13.0 - i*0.65), 3.4, 0.5,
                                    boxstyle="round,pad=0.02",
                                    facecolor=colors['silver'], edgecolor='#0D47A1', linewidth=1.5)
        ax.add_patch(table_box)
        ax.text(16.4, 13.25 - i*0.65, table, fontsize=9, ha='center', va='center', color=colors['text_light'])
    
    ax.text(16.4, 11.0, '95% Clean', fontsize=8, ha='center', va='center', color='#0D47A1', fontweight='bold')
    ax.text(16.4, 10.6, 'Validated & Deduplicated', fontsize=7, ha='center', va='center', color='#795548')
    
    # Arrow Silver -> Gold
    ax.annotate('', xy=(19.3, 14.5), xytext=(18.3, 14.5),
                arrowprops=dict(arrowstyle='->', color=colors['gold'], lw=3))
    
    # Gold Box
    gold_box = FancyBboxPatch((14.5, 4.5), 3.8, 4.3, boxstyle="round,pad=0.1",
                               facecolor='#FFFDE7', edgecolor=colors['gold'], linewidth=3)
    ax.add_patch(gold_box)
    ax.text(16.4, 8.4, 'GOLD', fontsize=13, fontweight='bold',
            ha='center', va='center', color='#E65100')
    ax.text(16.4, 7.8, '(Business Metrics)', fontsize=10, ha='center', va='center', color='#F57F17')
    
    # Gold tables
    gold_tables = ['dim_customers', 'dim_products', 'fct_orders', 'agg_metrics']
    for i, table in enumerate(gold_tables):
        table_box = FancyBboxPatch((14.7, 7.0 - i*0.55), 3.4, 0.45,
                                    boxstyle="round,pad=0.02",
                                    facecolor=colors['gold'], edgecolor='#E65100', linewidth=1.5)
        ax.add_patch(table_box)
        ax.text(16.4, 7.2 - i*0.55, table, fontsize=9, ha='center', va='center', color=colors['text_dark'])
    
    ax.text(16.4, 5.0, 'Business-Ready', fontsize=8, ha='center', va='center', color='#E65100', fontweight='bold')
    ax.text(16.4, 4.6, 'KPIs & Metrics', fontsize=7, ha='center', va='center', color='#795548')
    
    # Arrow Silver down to Gold
    ax.annotate('', xy=(16.4, 4.5), xytext=(16.4, 5.5),
                arrowprops=dict(arrowstyle='->', color=colors['gold'], lw=2.5))
    ax.text(16.9, 5.0, 'dbt', fontsize=7, ha='left', va='center', color=colors['dbt'], fontweight='bold')
    
    # ============ dbt TRANSFORMATION ============
    dbt_box = FancyBboxPatch((9, 4.5), 4.5, 4.3, boxstyle="round,pad=0.1",
                              facecolor='#F3E5F5', edgecolor=colors['dbt'], linewidth=3)
    ax.add_patch(dbt_box)
    ax.text(11.25, 8.4, 'dbt', fontsize=14, fontweight='bold',
            ha='center', va='center', color=colors['dbt'])
    ax.text(11.25, 7.8, 'Transformation', fontsize=10, ha='center', va='center', color='#4A148C')
    
    # dbt features
    dbt_features = ['Clean & Dedupe', 'Enrich & Join', 'Type Casting', 'Business Logic']
    for i, feature in enumerate(dbt_features):
        ax.text(11.25, 7.0 - i*0.55, f'> {feature}', fontsize=9, ha='center', va='center', color='#4A148C', family='monospace')
    
    ax.text(11.25, 5.0, 'SQL-based', fontsize=8, ha='center', va='center', color='#7B1FA2', fontweight='bold')
    ax.text(11.25, 4.6, 'Data Tests & Docs', fontsize=7, ha='center', va='center', color='#795548')
    
    # Arrow Bronze to dbt
    ax.annotate('', xy=(10.9, 10.5), xytext=(10.9, 10.8),
                arrowprops=dict(arrowstyle='->', color=colors['dbt'], lw=2))
    
    # Arrow dbt to Silver
    ax.annotate('', xy=(14.5, 7.5), xytext=(13.5, 7.5),
                arrowprops=dict(arrowstyle='->', color=colors['dbt'], lw=2))
    
    # Arrow dbt to Gold
    ax.annotate('', xy=(16.4, 4.8), xytext=(13.5, 4.8),
                arrowprops=dict(arrowstyle='->', color=colors['dbt'], lw=2))
    
    # ============ DATABRICKS BADGE ============
    databricks_box = FancyBboxPatch((0.3, 4.5), 7.5, 5.5, boxstyle="round,pad=0.1",
                                     facecolor='#1565C0', edgecolor='#0D47A1', linewidth=3)
    ax.add_patch(databricks_box)
    ax.text(4.05, 9.6, 'Databricks', fontsize=16, fontweight='bold',
            ha='center', va='center', color=colors['text_light'])
    ax.text(4.05, 8.9, 'Community Edition (Free)', fontsize=11, ha='center', va='center', color='#BBDEFB')
    
    # Databricks features
    dbx_features = [
        'Apache Spark 3.5',
        'Delta Lake',
        '20GB Free Storage',
        'SQL Warehouses',
        'Python & Scala',
        'ML Runtime',
    ]
    for i, feature in enumerate(dbx_features):
        ax.text(4.05, 8.1 - i*0.5, f'+ {feature}', fontsize=9, ha='center', va='center', color=colors['text_light'], family='monospace')
    
    # Connect Databricks to Bronze/Silver/Gold
    ax.annotate('', xy=(9, 13), xytext=(7.8, 13),
                arrowprops=dict(arrowstyle='->', color='#64B5F6', lw=2, linestyle='dashed'))
    ax.annotate('', xy=(14.5, 13), xytext=(12.8, 13),
                arrowprops=dict(arrowstyle='->', color='#64B5F6', lw=2, linestyle='dashed'))
    ax.annotate('', xy=(14.5, 7), xytext=(13.5, 7),
                arrowprops=dict(arrowstyle='->', color='#64B5F6', lw=2, linestyle='dashed'))
    ax.annotate('', xy=(14.5, 5.5), xytext=(13.5, 5.5),
                arrowprops=dict(arrowstyle='->', color='#64B5F6', lw=2, linestyle='dashed'))
    
    # ============ SERVING LAYER ============
    serving_box = FancyBboxPatch((19.5, 4.5), 2.2, 4.3, boxstyle="round,pad=0.1",
                                  facecolor='#E1BEE7', edgecolor=colors['serving'], linewidth=3)
    ax.add_patch(serving_box)
    ax.text(20.6, 8.4, 'SERVING', fontsize=11, fontweight='bold',
            ha='center', va='center', color=colors['serving'])
    
    serving_items = [
        ('Metabase', 'Dashboards'),
        ('FastAPI', 'REST API'),
        ('SQL', 'Queries'),
    ]
    for i, (tool, desc) in enumerate(serving_items):
        ax.text(20.6, 7.5 - i*0.9, tool, fontsize=9, fontweight='bold', ha='center', va='center', color='#4A148C')
        ax.text(20.6, 7.2 - i*0.9, desc, fontsize=7, ha='center', va='center', color='#7B1FA2')
    
    # Arrow from Gold to Serving
    ax.annotate('', xy=(19.5, 6.5), xytext=(18.3, 6.5),
                arrowprops=dict(arrowstyle='->', color=colors['serving'], lw=2.5))
    
    # ============ ORCHESTRATION LAYER ============
    orch_box = FancyBboxPatch((0.3, 0.3), 6.5, 3.8, boxstyle="round,pad=0.1",
                              facecolor='#ECEFF1', edgecolor=colors['orchestration'], linewidth=3)
    ax.add_patch(orch_box)
    ax.text(3.55, 3.8, 'ORCHESTRATION', fontsize=12, fontweight='bold',
            ha='center', va='center', color=colors['orchestration'])
    
    # Airflow section
    ax.text(1.7, 3.1, 'Apache Airflow', fontsize=10, fontweight='bold', ha='center', va='center', color='#455A64')
    
    dags = [
        ('daily_ingestion', 'Daily 2:00 AM'),
        ('dbt_transform', 'Daily 3:30 AM'),
        ('health_check', 'Every 15 min'),
    ]
    for i, (dag, schedule) in enumerate(dags):
        ax.text(1.7, 2.5 - i*0.5, f'DAG: {dag}', fontsize=8, ha='center', va='center', color='#78909C')
    
    ax.text(4.5, 3.1, 'Docker', fontsize=10, fontweight='bold', ha='center', va='center', color='#455A64')
    ax.text(4.5, 2.5, 'PostgreSQL', fontsize=8, ha='center', va='center', color='#78909C')
    ax.text(4.5, 2.1, 'Airflow', fontsize=8, ha='center', va='center', color='#78909C')
    ax.text(4.5, 1.7, 'Metabase', fontsize=8, ha='center', va='center', color='#78909C')
    
    # ============ LOGGING & MONITORING ============
    log_box = FancyBboxPatch((7.5, 0.3), 6.5, 3.8, boxstyle="round,pad=0.1",
                              facecolor='#EFEBE9', edgecolor=colors['logging'], linewidth=3)
    ax.add_patch(log_box)
    ax.text(10.75, 3.8, 'LOGGING & MONITORING', fontsize=12, fontweight='bold',
            ha='center', va='center', color=colors['logging'])
    
    logging_items = [
        ('Loguru', 'Application logs'),
        ('Loki', 'Log aggregation'),
        ('Grafana', 'Metrics dashboards'),
        ('Slack', 'Alert notifications'),
    ]
    for i, (tool, desc) in enumerate(logging_items):
        ax.text(8.5, 3.1 - i*0.5, f'{tool}', fontsize=8, fontweight='bold', ha='left', va='center', color='#4E342E')
        ax.text(11.5, 3.1 - i*0.5, f': {desc}', fontsize=8, ha='left', va='center', color='#795548')
    
    # ============ DATA INGESTION ============
    ingest_box = FancyBboxPatch((14.8, 0.3), 6.9, 3.8, boxstyle="round,pad=0.1",
                                 facecolor='#E8F5E9', edgecolor=colors['source'], linewidth=3)
    ax.add_patch(ingest_box)
    ax.text(18.25, 3.8, 'DATA INGESTION', fontsize=12, fontweight='bold',
            ha='center', va='center', color=colors['source'])
    
    ingest_items = [
        ('Google Drive API', 'Download CSV/Excel'),
        ('REST Client', 'Fetch JSON data'),
        ('Schema Validation', 'Pandera / Great Expectations'),
        ('Databricks SDK', 'Write to Delta Lake'),
    ]
    for i, (tool, desc) in enumerate(ingest_items):
        ax.text(15.5, 3.1 - i*0.5, f'{tool}', fontsize=8, fontweight='bold', ha='left', va='center', color='#1B5E20')
        ax.text(19.0, 3.1 - i*0.5, f': {desc}', fontsize=8, ha='left', va='center', color='#4CAF50')
    
    # ============ LEGEND ============
    legend_y = 0.0
    legend_items = [
        (colors['source'], 'Data Sources'),
        (colors['bronze'], 'Bronze (Raw)'),
        (colors['silver'], 'Silver (Clean)'),
        (colors['gold'], 'Gold (Metrics)'),
        (colors['dbt'], 'dbt Transform'),
        (colors['serving'], 'Serving'),
    ]
    
    for i, (color, label) in enumerate(legend_items):
        rect = FancyBboxPatch((1.5 + i*3.3, legend_y), 0.5, 0.3, boxstyle="round,pad=0.02",
                               facecolor=color, edgecolor='none')
        ax.add_patch(rect)
        ax.text(2.1 + i*3.3, legend_y, label, fontsize=8, ha='left', va='center', color='#616161')
    
    # Footer
    ax.text(11, -0.5, 'Built with love | Databricks Community Edition | Free & Open Source', 
            fontsize=10, ha='center', va='center', color='#9E9E9E', style='italic')
    
    plt.tight_layout()
    return fig

if __name__ == '__main__':
    fig = create_architecture_diagram()
    output_path = 'docs/architecture/diagrams/architecture-overview.png'
    fig.savefig(output_path, dpi=200, bbox_inches='tight', 
                facecolor='#FAFAFA', edgecolor='none')
    print(f'Architecture diagram saved to: {output_path}')
    plt.close()
