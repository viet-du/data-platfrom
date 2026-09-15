"""
Crawl raw data - không upload Drive
Lưu vào data/raw/
"""
import sys
import os
sys.path.insert(0, '/app')

from src.crawlers import (
    VNExpressCrawler, 
    VietnamNetCrawler, 
    DanTriCrawler, 
    TuoiTreCrawler
)
from datetime import datetime
import json

os.makedirs('/app/data/raw', exist_ok=True)

all_articles = []

sources = [
    (VNExpressCrawler, 'VNExpress'),
    (VietnamNetCrawler, 'VietnamNet'),
    (DanTriCrawler, 'DanTri'),
    (TuoiTreCrawler, 'TuoiTre'),
]

for Crawler, name in sources:
    try:
        c = Crawler()
        articles = c.crawl_all(today_only=True)
        all_articles.extend(articles)
        print(f'{name}: {len(articles)} articles')
    except Exception as e:
        print(f'{name}: Error - {e}')

# Save raw data
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_path = f'/app/data/raw/raw_crawl_{timestamp}.json'

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump({
        'crawled_at': datetime.now().isoformat(),
        'total_articles': len(all_articles),
        'articles': all_articles
    }, f, ensure_ascii=False, indent=2)

print(f'Total: {len(all_articles)} articles')
print(f'Saved to: {output_path}')
