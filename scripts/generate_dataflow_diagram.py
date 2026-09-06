#!/usr/bin/env python3
"""
Data Flow Diagram Generator
Creates a professional data flow visualization
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Set style
plt.style.use('default')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['SF Pro Display', 'Helvetica Neue', 'Arial']
plt.rcParams['font.size'] = 10

def create_data_flow_diagram():
    fig, ax = plt.subplots(1, 1, figsize=(18, 14))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 14)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Color palette
    colors = {
        'source': '#2E7D32',        # Green
        'bronze': '#E65100',        # Orange
        'silver': '#1565C0',        # Blue
        'gold': '#F57F17',          # Gold
        'serving': '#6A1B9A',       # Purple
        'step': '#455A64',          # Blue Grey
        'arrow': '#37474F',         # Dark Grey
        'bg': '#FAFAFA',            # Light Grey Background
        'white': '#FFFFFF',
        'text_dark': '#212121',
        'text_light': '#FFFFFF',
        'dbt': '#7B1FA2',           # Purple for dbt
        'python': '#306998',         # Python blue
    }
    
    # Background
    fig.patch.set_facecolor(colors['bg'])
    ax.set_facecolor(colors['bg'])
    
    # Title
    ax.text(9, 13.5, 'DATA FLOW', fontsize=26, fontweight='bold',
            ha='center', va='center', color=colors['text_dark'])
    ax.text(9, 12.9, 'Step-by-Step Data Pipeline', fontsize=14,
            ha='center', va='center', color='#616161', style='italic')
    
    # ============ STEP 1: INGESTION ============
    step1_box = FancyBboxPatch((0.3, 10.5), 17.4, 2.2, boxstyle="round,pad=0.05",
                               facecolor='#E8F5E9', edgecolor=colors['source'], linewidth=2)
    ax.add_patch(step1_box)
    ax.text(0.8, 12.4, 'STEP 1', fontsize=10, fontweight='bold',
            ha='left', va='center', color=colors['source'])
    ax.text(1.8, 12.4, 'INGESTION', fontsize=12, fontweight='bold',
            ha='left', va='center', color=colors['text_dark'])
    
    # Step 1 components
    comps1 = [
        ('Google Drive', 'CSV/Excel\nFiles', colors['source']),
        ('REST APIs', 'JSON\nResponses', colors['source']),
        ('Python\nScripts', 'Download &\nValidate', colors['python']),
        ('Databricks\nSDK', 'Write to\nBronze', '#1E88E5'),
    ]
    
    for i, (name, desc, color) in enumerate(comps1):
        x = 2.5 + i * 4
        box = FancyBboxPatch((x, 10.7), 2.5, 1.6, boxstyle="round,pad=0.05",
                            facecolor=color, edgecolor='none', linewidth=0)
        ax.add_patch(box)
        ax.text(x + 1.25, 11.7, name, fontsize=9, fontweight='bold',
                ha='center', va='center', color=colors['text_light'])
        ax.text(x + 1.25, 11.1, desc, fontsize=7,
                ha='center', va='center', color=colors['text_light'])
        
        if i < len(comps1) - 1:
            ax.annotate('', xy=(x + 2.5, 11.5), xytext=(x + 2.5, 11.5),
                        arrowprops=dict(arrowstyle='->', color=colors['arrow'], lw=2))
            ax.annotate('', xy=(x + 2.6, 11.5), xytext=(x + 2.5, 11.5),
                        arrowprops=dict(arrowstyle='->', color=colors['arrow'], lw=2))
    
    # Arrows between step 1 components
    for i in range(len(comps1) - 1):
        x_start = 2.5 + i * 4 + 2.5
        x_end = 2.5 + (i + 1) * 4
        ax.annotate('', xy=(x_end, 11.5), xytext=(x_start, 11.5),
                    arrowprops=dict(arrowstyle='->', color=colors['arrow'], lw=2.5))
    
    # ============ STEP 2: BRONZE TO SILVER ============
    step2_box = FancyBboxPatch((0.3, 7.5), 17.4, 2.2, boxstyle="round,pad=0.05",
                               facecolor='#FFF3E0', edgecolor=colors['bronze'], linewidth=2)
    ax.add_patch(step2_box)
    ax.text(0.8, 9.4, 'STEP 2', fontsize=10, fontweight='bold',
            ha='left', va='center', color=colors['bronze'])
    ax.text(1.8, 9.4, 'BRONZE TO SILVER', fontsize=12, fontweight='bold',
            ha='left', va='center', color=colors['text_dark'])
    
    # Bronze box
    bronze_in = FancyBboxPatch((1.5, 7.7), 2.5, 1.8, boxstyle="round,pad=0.05",
                               facecolor=colors['bronze'], edgecolor='none')
    ax.add_patch(bronze_in)
    ax.text(2.75, 9.0, 'BRONZE', fontsize=10, fontweight='bold',
            ha='center', va='center', color=colors['text_light'])
    ax.text(2.75, 8.5, 'stg_sales\nstg_customers\nstg_products', fontsize=7,
            ha='center', va='center', color=colors['text_light'], linespacing=1.3)
    
    # Arrow to dbt
    ax.annotate('', xy=(5.5, 8.6), xytext=(4.0, 8.6),
                arrowprops=dict(arrowstyle='->', color=colors['dbt'], lw=3))
    
    # dbt box
    dbt_box = FancyBboxPatch((5.5, 7.7), 2.8, 1.8, boxstyle="round,pad=0.05",
                             facecolor=colors['dbt'], edgecolor='none')
    ax.add_patch(dbt_box)
    ax.text(6.9, 9.0, 'dbt', fontsize=12, fontweight='bold',
            ha='center', va='center', color=colors['text_light'])
    ax.text(6.9, 8.5, 'Clean & Dedupe\nValidate & Cast\nEnrich & Join', fontsize=7,
            ha='center', va='center', color=colors['text_light'], linespacing=1.3)
    
    # Arrow to Silver
    ax.annotate('', xy=(9.8, 8.6), xytext=(8.3, 8.6),
                arrowprops=dict(arrowstyle='->', color=colors['silver'], lw=3))
    
    # Silver box
    silver_in = FancyBboxPatch((9.8, 7.7), 2.5, 1.8, boxstyle="round,pad=0.05",
                               facecolor=colors['silver'], edgecolor='none')
    ax.add_patch(silver_in)
    ax.text(11.05, 9.0, 'SILVER', fontsize=10, fontweight='bold',
            ha='center', va='center', color=colors['text_light'])
    ax.text(11.05, 8.5, 'int_orders\nint_customers\nint_products', fontsize=7,
            ha='center', va='center', color=colors['text_light'], linespacing=1.3)
    
    # dbt tests
    ax.text(13.5, 9.0, 'dbt tests:', fontsize=9, fontweight='bold', ha='left', va='center', color='#7B1FA2')
    ax.text(13.5, 8.5, 'not_null, unique\naccepted_values\nrelationships', fontsize=7, ha='left', va='center', color='#9E9E9E', linespacing=1.3)
    
    # ============ STEP 3: SILVER TO GOLD ============
    step3_box = FancyBboxPatch((0.3, 4.5), 17.4, 2.2, boxstyle="round,pad=0.05",
                               facecolor='#FFF8E1', edgecolor=colors['gold'], linewidth=2)
    ax.add_patch(step3_box)
    ax.text(0.8, 6.4, 'STEP 3', fontsize=10, fontweight='bold',
            ha='left', va='center', color=colors['gold'])
    ax.text(1.8, 6.4, 'SILVER TO GOLD', fontsize=12, fontweight='bold',
            ha='left', va='center', color=colors['text_dark'])
    
    # Silver box (output)
    silver_out = FancyBboxPatch((1.5, 4.7), 2.5, 1.8, boxstyle="round,pad=0.05",
                                facecolor=colors['silver'], edgecolor='none')
    ax.add_patch(silver_out)
    ax.text(2.75, 6.0, 'SILVER', fontsize=10, fontweight='bold',
            ha='center', va='center', color=colors['text_light'])
    ax.text(2.75, 5.5, 'int_orders\nint_customers\nint_products', fontsize=7,
            ha='center', va='center', color=colors['text_light'], linespacing=1.3)
    
    # Arrow to dbt
    ax.annotate('', xy=(5.5, 5.6), xytext=(4.0, 5.6),
                arrowprops=dict(arrowstyle='->', color=colors['dbt'], lw=3))
    
    # dbt box
    dbt_box2 = FancyBboxPatch((5.5, 4.7), 2.8, 1.8, boxstyle="round,pad=0.05",
                              facecolor=colors['dbt'], edgecolor='none')
    ax.add_patch(dbt_box2)
    ax.text(6.9, 6.0, 'dbt', fontsize=12, fontweight='bold',
            ha='center', va='center', color=colors['text_light'])
    ax.text(6.9, 5.5, 'Business Logic\nAggregations\nDimensions', fontsize=7,
            ha='center', va='center', color=colors['text_light'], linespacing=1.3)
    
    # Arrow to Gold
    ax.annotate('', xy=(9.8, 5.6), xytext=(8.3, 5.6),
                arrowprops=dict(arrowstyle='->', color=colors['gold'], lw=3))
    
    # Gold box
    gold_in = FancyBboxPatch((9.8, 4.7), 2.5, 1.8, boxstyle="round,pad=0.05",
                             facecolor=colors['gold'], edgecolor='none')
    ax.add_patch(gold_in)
    ax.text(11.05, 6.0, 'GOLD', fontsize=10, fontweight='bold',
            ha='center', va='center', color=colors['text_dark'])
    ax.text(11.05, 5.5, 'dim_customers\ndim_products\nfct_orders', fontsize=7,
            ha='center', va='center', color=colors['text_dark'], linespacing=1.3)
    
    # Business metrics
    ax.text(13.5, 6.0, 'Business Metrics:', fontsize=9, fontweight='bold', ha='left', va='center', color='#E65100')
    ax.text(13.5, 5.5, 'KPIs, Revenue\nCustomer LTV\nProduct Perf', fontsize=7, ha='left', va='center', color='#9E9E9E', linespacing=1.3)
    
    # ============ STEP 4: VISUALIZATION ============
    step4_box = FancyBboxPatch((0.3, 1.5), 17.4, 2.2, boxstyle="round,pad=0.05",
                               facecolor='#F3E5F5', edgecolor=colors['serving'], linewidth=2)
    ax.add_patch(step4_box)
    ax.text(0.8, 3.4, 'STEP 4', fontsize=10, fontweight='bold',
            ha='left', va='center', color=colors['serving'])
    ax.text(1.8, 3.4, 'VISUALIZATION & SERVING', fontsize=12, fontweight='bold',
            ha='left', va='center', color=colors['text_dark'])
    
    # Gold box (output)
    gold_out = FancyBboxPatch((1.5, 1.7), 2.5, 1.8, boxstyle="round,pad=0.05",
                              facecolor=colors['gold'], edgecolor='none')
    ax.add_patch(gold_out)
    ax.text(2.75, 3.0, 'GOLD', fontsize=10, fontweight='bold',
            ha='center', va='center', color=colors['text_dark'])
    ax.text(2.75, 2.5, 'dim_*\nfct_*\nagg_*', fontsize=7,
            ha='center', va='center', color=colors['text_dark'], linespacing=1.3)
    
    # Arrow to serving
    ax.annotate('', xy=(5.5, 2.6), xytext=(4.0, 2.6),
                arrowprops=dict(arrowstyle='->', color=colors['arrow'], lw=3))
    
    # Serving tools
    serving_tools = [
        ('Metabase', 'Dashboards', '#1E88E5'),
        ('FastAPI', 'REST API', '#008970'),
        ('SQL', 'Ad-hoc\nQueries', '#336791'),
    ]
    
    for i, (name, desc, color) in enumerate(serving_tools):
        x = 5.5 + i * 4
        box = FancyBboxPatch((x, 1.7), 2.5, 1.8, boxstyle="round,pad=0.05",
                            facecolor=color, edgecolor='none')
        ax.add_patch(box)
        ax.text(x + 1.25, 3.0, name, fontsize=10, fontweight='bold',
                ha='center', va='center', color=colors['text_light'])
        ax.text(x + 1.25, 2.5, desc, fontsize=7,
                ha='center', va='center', color=colors['text_light'], linespacing=1.3)
        
        if i > 0:
            ax.annotate('', xy=(x, 2.6), xytext=(x - 1.5, 2.6),
                        arrowprops=dict(arrowstyle='->', color=colors['arrow'], lw=2))
    
    # End users
    ax.text(17, 3.0, 'End\nUsers', fontsize=9, fontweight='bold', ha='center', va='center', color='#616161')
    ax.annotate('', xy=(16.3, 2.6), xytext=(15.5, 2.6),
                arrowprops=dict(arrowstyle='->', color=colors['arrow'], lw=2))
    
    # ============ LEGEND ============
    legend_y = 0.5
    legend_items = [
        (colors['source'], 'Data Sources'),
        (colors['bronze'], 'Bronze'),
        (colors['silver'], 'Silver'),
        (colors['gold'], 'Gold'),
        (colors['dbt'], 'dbt'),
        (colors['serving'], 'Serving'),
    ]
    
    for i, (color, label) in enumerate(legend_items):
        rect = FancyBboxPatch((1 + i*2.8, legend_y), 0.4, 0.25, boxstyle="round,pad=0.02",
                               facecolor=color, edgecolor='none')
        ax.add_patch(rect)
        ax.text(1.5 + i*2.8, legend_y, label, fontsize=8, ha='left', va='center', color='#616161')
    
    plt.tight_layout()
    return fig

if __name__ == '__main__':
    fig = create_data_flow_diagram()
    output_path = 'docs/architecture/diagrams/data-flow.png'
    fig.savefig(output_path, dpi=200, bbox_inches='tight', 
                facecolor='#FAFAFA', edgecolor='none')
    print(f'Data flow diagram saved to: {output_path}')
    plt.close()
