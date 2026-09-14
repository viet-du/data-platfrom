"""
Base Crawler - Abstract class for all news crawlers
"""
import os
import json
import re
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import time
import requests
from bs4 import BeautifulSoup


class BaseCrawler(ABC):
    """Abstract base class for news crawlers"""
    
    def __init__(
        self,
        name: str,
        base_url: str,
        folder_name: str,
        categories: List[str],
        timeout: int = 30,
        retry_count: int = 3
    ):
        self.name = name
        self.base_url = base_url
        self.folder_name = folder_name
        self.categories = categories
        self.timeout = timeout
        self.retry_count = retry_count
        
        # Setup logging
        self.logger = logging.getLogger(f"crawler.{name}")
        
        # Session for requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def _retry_request(self, url: str, method: str = 'GET') -> Optional[requests.Response]:
        """Make request with retry logic"""
        for attempt in range(self.retry_count):
            try:
                if method == 'GET':
                    response = self.session.get(url, timeout=self.timeout)
                else:
                    response = self.session.post(url, timeout=self.timeout)
                
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1}/{self.retry_count} failed for {url}: {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                
        return None
    
    def _parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content"""
        return BeautifulSoup(html, 'html.parser')
    
    def _is_today(self, date_str: str) -> bool:
        """Check if the date string is from today"""
        if not date_str:
            return True  # If no date, include it
        
        today = datetime.now().date()
        
        # Common date patterns
        patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',   # YYYY-MM-DD
            r'(\d{1,2})-(\d{1,2})-(\d{4})',   # DD-MM-YYYY
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if pattern == r'(\d{1,2})/(\d{1,2})/(\d{4})':
                        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    elif pattern == r'(\d{4})-(\d{1,2})-(\d{1,2})':
                        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    else:
                        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    
                    article_date = datetime(year, month, day).date()
                    return article_date == today
                except ValueError:
                    continue
        
        return True  # If can't parse, include it
    
    @abstractmethod
    def get_article_urls(self, category: str) -> List[str]:
        """Get list of article URLs from a category page"""
        pass
    
    @abstractmethod
    def parse_article(self, url: str) -> Optional[Dict]:
        """Parse a single article and return article data"""
        pass
    
    def crawl_category(self, category: str, today_only: bool = True) -> List[Dict]:
        """Crawl all articles from a category"""
        self.logger.info(f"Crawling category: {category}")
        articles = []
        
        urls = self.get_article_urls(category)
        self.logger.info(f"Found {len(urls)} articles in {category}")
        
        for url in urls:
            try:
                article = self.parse_article(url)
                if article:
                    article['category'] = category
                    article['crawled_at'] = datetime.now().isoformat()
                    
                    # Filter by today's date if enabled
                    if today_only:
                        published_date = article.get('published_date', '')
                        if self._is_today(published_date):
                            articles.append(article)
                            self.logger.info(f"Crawled (today): {article.get('title', 'Unknown')[:50]}...")
                    else:
                        articles.append(article)
                        self.logger.info(f"Crawled: {article.get('title', 'Unknown')[:50]}...")
            except Exception as e:
                self.logger.error(f"Error crawling {url}: {e}")
        
        return articles
    
    def crawl_all(self, max_workers: int = 4, today_only: bool = True) -> List[Dict]:
        """Crawl all categories using multi-threading"""
        self.logger.info(f"Starting crawl for {self.name} with {max_workers} workers (today_only={today_only})")
        all_articles = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.crawl_category, cat, today_only): cat 
                for cat in self.categories
            }
            
            for future in as_completed(futures):
                category = futures[future]
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                    self.logger.info(f"Completed {category}: {len(articles)} articles")
                except Exception as e:
                    self.logger.error(f"Error in category {category}: {e}")
        
        self.logger.info(f"Total articles crawled: {len(all_articles)}")
        return all_articles
    
    def save_to_json(self, articles: List[Dict], output_path: str):
        """Save articles to JSON file"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'source': self.name,
                'crawled_at': datetime.now().isoformat(),
                'article_count': len(articles),
                'articles': articles
            }, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Saved {len(articles)} articles to {output_path}")
    
    def get_folder_name(self) -> str:
        """Get the Drive folder name for this source"""
        return self.folder_name
