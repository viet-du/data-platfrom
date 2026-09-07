#!/usr/bin/env python3
"""
README Banner Generator
Creates a beautiful glassmorphism-style banner for README header
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle
import numpy as np

# Set style
plt.style.use('dark_background')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['SF Pro Display', 'Helvetica Neue', 'Arial']
plt.rcParams['font.size'] = 10

def create_readme_banner():
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Background gradient
    gradient = np.linspace(0, 1, 256).reshape(1, -1)
    gradient = np.vstack((gradient, gradient))
    
    # Create gradient effect with multiple rectangles
    for i in range(50):
        alpha = i / 50
        y_start = 10 - (i * 0.2)
        color = (0.05 + alpha * 0.05, 0.1 + alpha * 0.1, 0.2 + alpha * 0.3)
        rect = Rectangle((0, y_start - 0.2), 14, 0.2, facecolor=color, edgecolor='none')
        ax.add_patch(rect)
    
    # ============ HEADER ============
    # Main title
    ax.text(7, 8.8, 'DATA PLATFORM', fontsize=42, fontweight='bold',
            ha='center', va='center', color='white', 
            family='monospace')
    ax.text(7, 8.2, 'Enterprise Data Engineering Solution', fontsize=14,
            ha='center', va='center', color='#B0BEC5', style='italic')
    
    # Subtitle
    ax.text(7, 7.6, 'ETL → Data Warehouse → Business Intelligence → Machine Learning',
            fontsize=11, ha='center', va='center', color='#90A4AE')
    
    # ============ TECH BADGES ============
    badges = [
        ('Python', '3.11+', '#306998'),
        ('Django', '6.0.1', '#092E20'),
        ('MongoDB', '7.0+', '#00684A'),
        ('Pandas', '2.2+', '#130654'),
        ('Scikit-learn', '1.8+', '#F7931E'),
        ('XGBoost', '3.2+', '#0066CC'),
        ('LightGBM', '4.6+', '#9C27B0'),
        ('CatBoost', '1.2+', '#FF6F00'),
        ('Streamlit', '1.50+', '#FF4B4B'),
        ('Databricks', 'CE', '#FF3621'),
        ('dbt', 'Latest', '#FF694B'),
        ('Airflow', '2.10+', '#017CEE'),
    ]
    
    badge_width = 1.05
    badge_height = 0.45
    badge_spacing = 0.1
    start_x = (14 - (len(badges) * (badge_width + badge_spacing))) / 2
    
    for i, (name, version, color) in enumerate(badges):
        x = start_x + i * (badge_width + badge_spacing)
        y = 6.7
        # Badge box
        box = FancyBboxPatch((x, y), badge_width, badge_height, 
                             boxstyle="round,pad=0.02",
                             facecolor=color, edgecolor='none', alpha=0.85)
        ax.add_patch(box)
        ax.text(x + 0.5, y + badge_height/2, name, fontsize=8, fontweight='bold',
                ha='center', va='center', color='white')
        ax.text(x + badge_width - 0.05, y + badge_height/2, version, fontsize=7,
                ha='right', va='center', color='#E0E0E0')
    
    # Second row of badges
    badges2 = [
        ('Delta Lake', 'Lakehouse', '#0066CC'),
        ('Glassmorphism', 'UI', '#9C27B0'),
        ('Vietnamese', 'VI', '#DC143C'),
        ('English', 'EN', '#1976D2'),
    ]
    
    start_x2 = (14 - (len(badges2) * (badge_width + badge_spacing))) / 2
    
    for i, (name, version, color) in enumerate(badges2):
        x = start_x2 + i * (badge_width + badge_spacing)
        y = 6.1
        box = FancyBboxPatch((x, y), badge_width, badge_height, 
                             boxstyle="round,pad=0.02",
                             facecolor=color, edgecolor='none', alpha=0.85)
        ax.add_patch(box)
        ax.text(x + 0.5, y + badge_height/2, name, fontsize=8, fontweight='bold',
                ha='center', va='center', color='white')
        ax.text(x + badge_width - 0.05, y + badge_height/2, version, fontsize=7,
                ha='right', va='center', color='#E0E0E0')
    
    # ============ FEATURES ============
    features = [
        ('Multi-source', 'Google Drive'),
        ('Pipeline', 'dbt Transform'),
        ('Analytics', 'Metabase BI'),
        ('ML', 'Train & Predict'),
        ('Modern UI', 'Glassmorphism'),
    ]
    
    feature_y = 5.0
    feature_width = 2.5
    feature_spacing = 0.3
    start_xf = (14 - (len(features) * (feature_width + feature_spacing))) / 2
    
    for i, (title, desc) in enumerate(features):
        x = start_xf + i * (feature_width + feature_spacing)
        # Glass card effect
        box = FancyBboxPatch((x, feature_y), feature_width, 1.2,
                             boxstyle="round,pad=0.05",
                             facecolor='white', edgecolor='white', alpha=0.1)
        ax.add_patch(box)
        # Border highlight
        box_border = FancyBboxPatch((x, feature_y), feature_width, 1.2,
                                    boxstyle="round,pad=0.05",
                                    facecolor='none', edgecolor='white', linewidth=1, alpha=0.3)
        ax.add_patch(box_border)
        
        ax.text(x + feature_width/2, feature_y + 0.85, title, fontsize=10, fontweight='bold',
                ha='center', va='center', color='white')
        ax.text(x + feature_width/2, feature_y + 0.4, desc, fontsize=9,
                ha='center', va='center', color='#B0BEC5')
    
    # ============ ARCHITECTURE FLOW ============
    flow_y = 3.5
    
    # Pipeline visualization
    steps = [
        ('Data\nSources', '#4CAF50'),
        ('Bronze\nLayer', '#FF9800'),
        ('Silver\nLayer', '#2196F3'),
        ('Gold\nLayer', '#FFC107'),
        ('Serving\nLayer', '#9C27B0'),
    ]
    
    step_width = 1.8
    step_height = 1.0
    step_spacing = 0.5
    arrow_width = step_spacing - 0.1
    start_xs = (14 - (len(steps) * step_width + (len(steps)-1) * step_spacing)) / 2
    
    for i, (label, color) in enumerate(steps):
        x = start_xs + i * (step_width + step_spacing)
        y = flow_y
        # Step box
        box = FancyBboxPatch((x, y), step_width, step_height,
                             boxstyle="round,pad=0.05",
                             facecolor=color, edgecolor='white', linewidth=1, alpha=0.9)
        ax.add_patch(box)
        ax.text(x + step_width/2, y + step_height/2, label, fontsize=10, fontweight='bold',
                ha='center', va='center', color='white')
        
        # Arrow to next
        if i < len(steps) - 1:
            arrow_x = x + step_width + 0.05
            arrow_y = y + step_height/2
            ax.annotate('', xy=(arrow_x + arrow_width, arrow_y), xytext=(arrow_x, arrow_y),
                        arrowprops=dict(arrowstyle='->', color='white', lw=2.5))
    
    # ============ STATS / METRICS ============
    stats = [
        ('99.9%', 'Uptime'),
        ('24/7', 'Monitoring'),
        ('100%', 'Automated'),
        ('5+', 'Tech Stacks'),
    ]
    
    stats_y = 1.5
    stats_width = 2.8
    stats_spacing = 0.4
    start_xstat = (14 - (len(stats) * (stats_width + stats_spacing))) / 2
    
    for i, (value, label) in enumerate(stats):
        x = start_xstat + i * (stats_width + stats_spacing)
        # Glass card
        box = FancyBboxPatch((x, stats_y), stats_width, 1.0,
                             boxstyle="round,pad=0.05",
                             facecolor='white', edgecolor='white', alpha=0.1)
        ax.add_patch(box)
        box_border = FancyBboxPatch((x, stats_y), stats_width, 1.0,
                                    boxstyle="round,pad=0.05",
                                    facecolor='none', edgecolor='white', linewidth=1, alpha=0.3)
        ax.add_patch(box_border)
        
        ax.text(x + stats_width/2, stats_y + 0.65, value, fontsize=20, fontweight='bold',
                ha='center', va='center', color='white')
        ax.text(x + stats_width/2, stats_y + 0.2, label, fontsize=9,
                ha='center', va='center', color='#B0BEC5')
    
    # ============ FOOTER ============
    ax.text(7, 0.4, 'Built with ❤️ | Open Source | Databricks Community Edition',
            fontsize=10, ha='center', va='center', color='#78909C', style='italic')
    
    plt.tight_layout()
    return fig

if __name__ == '__main__':
    fig = create_readme_banner()
    output_path = 'docs/architecture/diagrams/readme-banner.png'
    fig.savefig(output_path, dpi=200, bbox_inches='tight', 
                facecolor='#0a1929', edgecolor='none')
    print(f'Readme banner saved to: {output_path}')
    plt.close()
