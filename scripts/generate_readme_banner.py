#!/usr/bin/env python3
"""
Bright & Beautiful README Banner - Modern Gradient Style
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, FancyArrowPatch
import numpy as np

def create_bright_banner():
    fig = plt.figure(figsize=(16, 9), facecolor='#f8fafc')
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    
    # ============ GRADIENT BACKGROUND ============
    # Top gradient bar
    gradient_colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c']
    for i in range(100):
        ratio = i / 100
        color_val = (0.4 + ratio * 0.1, 0.5 + ratio * 0.2, 0.92 - ratio * 0.3)
        rect = Rectangle((0, 7.5 + i*0.015), 16, 0.015, facecolor=color_val, edgecolor='none')
        ax.add_patch(rect)
    
    # ============ HEADER SECTION ============
    # Glass card for title
    title_card = FancyBboxPatch((2, 6.8), 12, 1.8,
                                boxstyle="round,pad=0.08",
                                facecolor='white', edgecolor='#e2e8f0', linewidth=2)
    ax.add_patch(title_card)
    
    # Main title
    ax.text(8, 7.9, 'DATA PLATFORM', fontsize=48, fontweight='bold',
            ha='center', va='center', color='#1e293b')
    
    ax.text(8, 7.2, 'Enterprise Data Engineering Platform', fontsize=16,
            ha='center', va='center', color='#64748b')
    
    # ============ TECH STACK BADGES ============
    badges_data = [
        ('Python', '#306998'),
        ('Databricks', '#FF3621'),
        ('dbt', '#FF694B'),
        ('Delta Lake', '#0066CC'),
        ('Airflow', '#017CEE'),
        ('Metabase', '#509EE3'),
        ('MongoDB', '#00684A'),
        ('FastAPI', '#009688'),
    ]
    
    badge_y = 5.5
    badge_width = 1.5
    badge_height = 0.5
    total_width = len(badges_data) * badge_width + (len(badges_data) - 1) * 0.2
    start_x = (16 - total_width) / 2
    
    for i, (name, color) in enumerate(badges_data):
        x = start_x + i * (badge_width + 0.2)
        
        badge = FancyBboxPatch((x, badge_y), badge_width, badge_height,
                               boxstyle="round,pad=0.05",
                               facecolor=color, edgecolor='none', alpha=0.9)
        ax.add_patch(badge)
        
        ax.text(x + badge_width/2, badge_y + badge_height/2, name, 
                fontsize=10, fontweight='bold', ha='center', va='center', color='white')
    
    # ============ PIPELINE FLOW ============
    flow_y = 3.8
    
    # Container card
    container = FancyBboxPatch((0.8, 2.8), 14.4, 2.2,
                               boxstyle="round,pad=0.08",
                               facecolor='white', edgecolor='#e2e8f0', linewidth=2)
    ax.add_patch(container)
    
    # Section title
    ax.text(8, 4.7, 'Data Pipeline', fontsize=14, fontweight='bold',
            ha='center', va='center', color='#1e293b')
    
    # Pipeline steps
    steps = [
        ('Data\nSources', '#22c55e', 'Google Drive\nAPIs'),
        ('Bronze\nLayer', '#f97316', 'Raw Data\nStorage'),
        ('Silver\nLayer', '#3b82f6', 'Cleaned\nData'),
        ('Gold\nLayer', '#eab308', 'Business\nReady'),
        ('Serving', '#a855f7', 'BI & API'),
    ]
    
    step_width = 2.0
    step_spacing = 0.6
    total_flow = len(steps) * step_width + (len(steps)-1) * step_spacing
    start_flow = (16 - total_flow) / 2
    
    for i, (label, color, desc) in enumerate(steps):
        x = start_flow + i * (step_width + step_spacing)
        
        # Step box
        step_box = FancyBboxPatch((x, flow_y), step_width, 1.0,
                                   boxstyle="round,pad=0.08",
                                   facecolor=color, edgecolor='none', alpha=0.95)
        ax.add_patch(step_box)
        
        # White inner glow
        step_inner = FancyBboxPatch((x + 0.05, flow_y + 0.05), step_width - 0.1, 0.9,
                                    boxstyle="round,pad=0.05",
                                    facecolor='white', edgecolor='none', alpha=0.15)
        ax.add_patch(step_inner)
        
        ax.text(x + step_width/2, flow_y + 0.7, label, fontsize=11, fontweight='bold',
                ha='center', va='center', color='white')
        ax.text(x + step_width/2, flow_y + 0.25, desc, fontsize=7,
                ha='center', va='center', color='white', alpha=0.9)
        
        # Arrow
        if i < len(steps) - 1:
            arrow_x = x + step_width + 0.1
            arrow_y = flow_y + 0.5
            ax.annotate('', xy=(arrow_x + step_spacing - 0.2, arrow_y), 
                        xytext=(arrow_x, arrow_y),
                        arrowprops=dict(arrowstyle='->', color='#1e293b', lw=2.5))
    
    # ============ FEATURES ROW ============
    features = [
        ('ETL Pipeline', 'Automated Data Processing'),
        ('Data Warehouse', 'Centralized Storage'),
        ('Business Intel', 'Real-time Analytics'),
        ('ML Ready', 'Predictive Analytics'),
    ]
    
    feat_y = 1.6
    feat_width = 3.4
    feat_spacing = 0.3
    total_feat = len(features) * feat_width + (len(features)-1) * feat_spacing
    start_feat = (16 - total_feat) / 2
    
    colors_feat = ['#22c55e', '#3b82f6', '#f97316', '#a855f7']
    
    for i, ((title, desc), color) in enumerate(zip(features, colors_feat)):
        x = start_feat + i * (feat_width + feat_spacing)
        
        # Feature box
        feat_box = FancyBboxPatch((x, feat_y), feat_width, 0.9,
                                  boxstyle="round,pad=0.06",
                                  facecolor=color, edgecolor='none', alpha=0.9)
        ax.add_patch(feat_box)
        
        ax.text(x + feat_width/2, feat_y + 0.55, title, fontsize=11, fontweight='bold',
                ha='center', va='center', color='white')
        ax.text(x + feat_width/2, feat_y + 0.25, desc, fontsize=8,
                ha='center', va='center', color='white', alpha=0.9)
    
    # ============ FOOTER ============
    ax.text(8, 0.3, 'Open Source | Cloud Native | Databricks Community Edition',
            fontsize=11, ha='center', va='center', color='#94a3b8', fontweight='bold')
    
    plt.tight_layout()
    return fig

if __name__ == '__main__':
    fig = create_bright_banner()
    output_path = 'docs/architecture/diagrams/readme-banner.png'
    fig.savefig(output_path, dpi=200, bbox_inches='tight',
                facecolor='#f8fafc', edgecolor='none')
    print(f'Banner saved to: {output_path}')
    plt.close()
