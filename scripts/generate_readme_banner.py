#!/usr/bin/env python3
"""
Beautiful README Banner - Glassmorphism Style
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, FancyArrowPatch
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

def create_beautiful_banner():
    fig = plt.figure(figsize=(16, 9), facecolor='#0f172a')
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    
    # Background gradient effect
    colors_bg = ['#0f172a', '#1e1b4b', '#312e81']
    for i, color in enumerate(colors_bg):
        rect = Rectangle((0, i * 3), 16, 3, facecolor=color, edgecolor='none')
        ax.add_patch(rect)
    
    # Add subtle grid pattern
    for x in np.arange(0, 16, 0.5):
        ax.axvline(x, color='white', alpha=0.02, linewidth=0.5)
    for y in np.arange(0, 9, 0.5):
        ax.axhline(y, color='white', alpha=0.02, linewidth=0.5)
    
    # ============ FLOATING ORBS FOR GLASSMORPHISM ============
    # Large gradient orb - top right
    for i in range(50):
        alpha = 0.02 + (i * 0.003)
        size = 1.5 + (i * 0.05)
        circle = Circle((12 + i*0.02, 6.5 + i*0.02), size, 
                       facecolor='#818cf8', edgecolor='none', alpha=alpha)
        ax.add_patch(circle)
    
    # Medium orb - bottom left  
    for i in range(40):
        alpha = 0.015 + (i * 0.003)
        size = 1.0 + (i * 0.04)
        circle = Circle((3 - i*0.015, 2.5 - i*0.015), size,
                       facecolor='#34d399', edgecolor='none', alpha=alpha)
        ax.add_patch(circle)
    
    # Small accent orb
    for i in range(30):
        alpha = 0.02 + (i * 0.004)
        size = 0.5 + (i * 0.03)
        circle = Circle((14, 1.5 + i*0.02), size,
                       facecolor='#f472b6', edgecolor='none', alpha=alpha)
        ax.add_patch(circle)
    
    # ============ MAIN TITLE ============
    ax.text(8, 7.2, 'DATA PLATFORM', fontsize=52, fontweight='bold',
            ha='center', va='center', color='white', fontfamily='sans-serif')
    
    ax.text(8, 6.3, 'Enterprise Data Engineering Platform', fontsize=18,
            ha='center', va='center', color='#94a3b8', fontfamily='sans-serif')
    
    # ============ TECH BADGES ROW ============
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
    
    badge_y = 5.0
    badge_width = 1.6
    badge_height = 0.45
    total_width = len(badges_data) * badge_width + (len(badges_data) - 1) * 0.15
    start_x = (16 - total_width) / 2
    
    for i, (name, color) in enumerate(badges_data):
        x = start_x + i * (badge_width + 0.15)
        
        # Badge with glass effect
        badge = FancyBboxPatch((x, badge_y), badge_width, badge_height,
                               boxstyle="round,pad=0.03",
                               facecolor=color, edgecolor='none', alpha=0.85)
        ax.add_patch(badge)
        
        ax.text(x + badge_width/2, badge_y + badge_height/2, name, 
                fontsize=10, fontweight='bold', ha='center', va='center', color='white')
    
    # ============ ARCHITECTURE FLOW ============
    flow_y = 3.5
    
    # Glass container
    container = FancyBboxPatch((1, 2.5), 14, 2.0,
                               boxstyle="round,pad=0.05",
                               facecolor='white', edgecolor='white', alpha=0.05)
    ax.add_patch(container)
    container_border = FancyBboxPatch((1, 2.5), 14, 2.0,
                                      boxstyle="round,pad=0.05",
                                      facecolor='none', edgecolor='white', alpha=0.15, linewidth=1)
    ax.add_patch(container_border)
    
    # Pipeline steps
    steps = [
        ('Data\nSources', '#4ade80', 'Google Drive, APIs'),
        ('Bronze\nLayer', '#fb923c', 'Raw Data'),
        ('Silver\nLayer', '#60a5fa', 'Cleaned Data'),
        ('Gold\nLayer', '#fbbf24', 'Business Ready'),
        ('Serving', '#c084fc', 'BI, API'),
    ]
    
    step_width = 2.2
    step_spacing = 0.4
    total_flow = len(steps) * step_width + (len(steps)-1) * step_spacing
    start_flow = (16 - total_flow) / 2
    
    for i, (label, color, desc) in enumerate(steps):
        x = start_flow + i * (step_width + step_spacing)
        
        # Step box with glass effect
        step_box = FancyBboxPatch((x, flow_y), step_width, 1.2,
                                   boxstyle="round,pad=0.05",
                                   facecolor=color, edgecolor='none', alpha=0.9)
        ax.add_patch(step_box)
        
        # Inner glow
        step_inner = FancyBboxPatch((x + 0.05, flow_y + 0.05), step_width - 0.1, 1.1,
                                    boxstyle="round,pad=0.03",
                                    facecolor='white', edgecolor='none', alpha=0.1)
        ax.add_patch(step_inner)
        
        ax.text(x + step_width/2, flow_y + 0.85, label, fontsize=12, fontweight='bold',
                ha='center', va='center', color='white')
        ax.text(x + step_width/2, flow_y + 0.3, desc, fontsize=8,
                ha='center', va='center', color='white', alpha=0.8)
        
        # Arrow
        if i < len(steps) - 1:
            arrow_x = x + step_width + 0.05
            arrow_y = flow_y + 0.6
            ax.annotate('', xy=(arrow_x + step_spacing - 0.15, arrow_y), 
                        xytext=(arrow_x, arrow_y),
                        arrowprops=dict(arrowstyle='->', color='white', lw=2.5))
    
    # ============ BOTTOM STATS ============
    stats = [
        ('100%', 'Open Source'),
        ('Cloud', 'Native'),
        ('Free', 'Tier Available'),
        ('ETL', 'Pipeline'),
    ]
    
    stats_y = 1.3
    stats_width = 3.0
    total_stats = len(stats) * stats_width + (len(stats)-1) * 0.5
    start_stats = (16 - total_stats) / 2
    
    for i, (value, label) in enumerate(stats):
        x = start_stats + i * (stats_width + 0.5)
        
        # Glass stat box
        stat_box = FancyBboxPatch((x, stats_y), stats_width, 0.8,
                                  boxstyle="round,pad=0.03",
                                  facecolor='white', edgecolor='white', alpha=0.08)
        ax.add_patch(stat_box)
        stat_border = FancyBboxPatch((x, stats_y), stats_width, 0.8,
                                     boxstyle="round,pad=0.03",
                                     facecolor='none', edgecolor='white', alpha=0.2, linewidth=1)
        ax.add_patch(stat_border)
        
        ax.text(x + stats_width/2, stats_y + 0.5, value, fontsize=16, fontweight='bold',
                ha='center', va='center', color='white')
        ax.text(x + stats_width/2, stats_y + 0.2, label, fontsize=9,
                ha='center', va='center', color='#94a3b8')
    
    # ============ FOOTER ============
    ax.text(8, 0.2, 'Built with passion | Databricks Community Edition',
            fontsize=10, ha='center', va='center', color='#64748b')
    
    plt.tight_layout()
    return fig

if __name__ == '__main__':
    fig = create_beautiful_banner()
    output_path = 'docs/architecture/diagrams/readme-banner.png'
    fig.savefig(output_path, dpi=200, bbox_inches='tight',
                facecolor='#0f172a', edgecolor='none')
    print(f'Banner saved to: {output_path}')
    plt.close()
