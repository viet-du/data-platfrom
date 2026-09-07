#!/usr/bin/env python3
"""
Data Platform README Banner
Simple & Professional Design
"""
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

def create_banner():
    fig = plt.figure(figsize=(12, 4), facecolor='white')
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.axis('off')
    
    # Top gradient bar
    for i in range(50):
        y = 3.2 + i * 0.016
        r = 0.15 + i * 0.004
        g = 0.15 + i * 0.003
        b = 0.35 + i * 0.004
        rect = Rectangle((0, y), 12, 0.016, facecolor=(r, g, b), edgecolor='none')
        ax.add_patch(rect)
    
    # Title
    ax.text(6, 2.7, 'DATA PLATFORM', fontsize=42, fontweight='bold',
            ha='center', va='center', color='#1e293b')
    
    # Subtitle
    ax.text(6, 2.0, 'Enterprise Data Engineering Platform', fontsize=15,
            ha='center', va='center', color='#64748b')
    
    # Tech badges - inline
    ax.text(6, 1.3, 'Databricks  |  dbt  |  Delta Lake  |  Airflow  |  Metabase  |  FastAPI  |  Docker', 
            fontsize=10, ha='center', va='center', color='#6366f1')
    
    # Footer
    ax.text(6, 0.5, 'Cloud Native  |  Open Source  |  Cost Effective',
            fontsize=9, ha='center', va='center', color='#94a3b8')
    
    plt.tight_layout()
    return fig

if __name__ == '__main__':
    fig = create_banner()
    output_path = 'docs/architecture/diagrams/readme-header.png'
    fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f'Banner saved: {output_path}')
    plt.close()
