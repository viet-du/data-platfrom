#!/usr/bin/env python3
"""
Clean & Professional README Banner
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle
import numpy as np

def create_clean_banner():
    fig = plt.figure(figsize=(14, 6), facecolor='white')
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6)
    ax.axis('off')
    ax.set_facecolor('white')
    
    # ============ BACKGROUND ============
    # Top gradient bar
    for i in range(50):
        ratio = i / 50
        r = 0.4 + ratio * 0.15
        g = 0.55 + ratio * 0.2
        b = 0.9 - ratio * 0.3
        rect = Rectangle((0, 5.2 + i*0.016), 14, 0.016, facecolor=(r, g, b), edgecolor='none')
        ax.add_patch(rect)
    
    # ============ TITLE SECTION ============
    # Title card
    title_box = FancyBboxPatch((0.5, 4.2), 13, 1.3,
                               boxstyle="round,pad=0.1",
                               facecolor='white', edgecolor='#e2e8f0', linewidth=2)
    ax.add_patch(title_box)
    
    # Shadow effect
    shadow = FancyBboxPatch((0.55, 4.15), 13, 1.3,
                            boxstyle="round,pad=0.1",
                            facecolor='#f1f5f9', edgecolor='none')
    ax.add_patch(shadow)
    
    # Title
    ax.text(7, 5.1, 'DATA PLATFORM', fontsize=36, fontweight='bold',
            ha='center', va='center', color='#1e293b')
    ax.text(7, 4.55, 'Enterprise Data Engineering Platform', fontsize=12,
            ha='center', va='center', color='#64748b')
    
    # ============ TECH STACK BADGES ============
    badges = [
        ('Python', '#3776ab'),
        ('Databricks', '#ff3621'),
        ('dbt', '#ff694b'),
        ('Delta Lake', '#0066cc'),
        ('Airflow', '#017cee'),
        ('Metabase', '#509ee3'),
        ('MongoDB', '#00684a'),
        ('FastAPI', '#009688'),
    ]
    
    badge_w = 1.35
    badge_h = 0.35
    total_w = len(badges) * badge_w + (len(badges) - 1) * 0.12
    start_x = (14 - total_w) / 2
    
    for i, (name, color) in enumerate(badges):
        x = start_x + i * (badge_w + 0.12)
        y = 3.65
        
        badge = FancyBboxPatch((x, y), badge_w, badge_h,
                               boxstyle="round,pad=0.04",
                               facecolor=color, edgecolor='none')
        ax.add_patch(badge)
        ax.text(x + badge_w/2, y + badge_h/2, name,
                fontsize=8, fontweight='bold', ha='center', va='center', color='white')
    
    # ============ PIPELINE FLOW ============
    # Section label
    ax.text(7, 3.2, 'Data Pipeline', fontsize=11, fontweight='bold',
            ha='center', va='center', color='#475569')
    
    steps = [
        ('Sources', '#22c55e', 'Google Drive'),
        ('Bronze', '#f97316', 'Raw Data'),
        ('Silver', '#3b82f6', 'Cleaned'),
        ('Gold', '#eab308', 'Business'),
        ('Serving', '#a855f7', 'BI & API'),
    ]
    
    box_w = 2.0
    box_h = 0.75
    gap = 0.5
    total = len(steps) * box_w + (len(steps) - 1) * gap
    start = (14 - total) / 2
    
    for i, (label, color, desc) in enumerate(steps):
        x = start + i * (box_w + gap)
        y = 1.95
        
        box = FancyBboxPatch((x, y), box_w, box_h,
                             boxstyle="round,pad=0.06",
                             facecolor=color, edgecolor='none')
        ax.add_patch(box)
        
        ax.text(x + box_w/2, y + 0.45, label, fontsize=10, fontweight='bold',
                ha='center', va='center', color='white')
        ax.text(x + box_w/2, y + 0.18, desc, fontsize=7,
                ha='center', va='center', color='white', alpha=0.85)
        
        if i < len(steps) - 1:
            ax.annotate('', xy=(x + box_w + gap - 0.08, y + box_h/2),
                        xytext=(x + box_w + 0.02, y + box_h/2),
                        arrowprops=dict(arrowstyle='->', color='#64748b', lw=1.5))
    
    # ============ FOOTER ============
    ax.text(7, 0.5, 'Open Source  |  Cloud Native  |  Databricks Community Edition',
            fontsize=9, ha='center', va='center', color='#94a3b8', fontweight='bold')
    
    plt.tight_layout()
    return fig

if __name__ == '__main__':
    fig = create_clean_banner()
    output_path = 'docs/architecture/diagrams/readme-banner.png'
    fig.savefig(output_path, dpi=180, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    print(f'Banner saved to: {output_path}')
    plt.close()
