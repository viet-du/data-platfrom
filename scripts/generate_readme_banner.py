#!/usr/bin/env python3
"""
Simple Clean README Banner v2
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

def create_simple_banner():
    fig = plt.figure(figsize=(12, 4), facecolor='white')
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.axis('off')
    
    # Top color bar
    bar = Rectangle((0, 3.2), 12, 0.8, facecolor='#2563eb', edgecolor='none')
    ax.add_patch(bar)
    
    # Title
    ax.text(6, 3.6, 'DATA PLATFORM', fontsize=38, fontweight='bold',
            ha='center', va='center', color='white')
    
    # Subtitle
    ax.text(6, 2.7, 'Enterprise Data Engineering Platform', fontsize=14,
            ha='center', va='center', color='#374151')
    
    # Tech badges - inline
    ax.text(6, 2.1, 'Python  |  Databricks  |  dbt  |  Airflow  |  Metabase  |  MongoDB', 
            fontsize=10, ha='center', va='center', color='#6b7280')
    
    # Line
    ax.axhline(y=1.7, xmin=0.1, xmax=0.9, color='#e5e7eb', linewidth=1)
    
    # Footer
    ax.text(6, 1.3, 'Open Source | Cloud Native | Databricks Community Edition',
            fontsize=9, ha='center', va='center', color='#9ca3af')
    
    plt.tight_layout()
    return fig

if __name__ == '__main__':
    fig = create_simple_banner()
    output_path = 'docs/architecture/diagrams/readme-banner.png'
    fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f'Banner saved: {output_path}')
    plt.close()
