"""
VNExpress Crawler
"""
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from .base_crawler import BaseCrawler


class VNExpressCrawler(BaseCrawler):
    """Crawler for VNExpress"""
    
    def __init__(self):
        super().__init__(
            name='VNExpress',
            base_url='https://vnexpress.net',
            folder_name='vnexpress-news',
            categories=['thoi-su', 'the-gioi', 'kinh-doanh', 'the-thao', 'so-hoa', 'giai-tri', 'suc-khoe', 'giao-duc']
        )
    
    def get_article_urls(self, category: str) -> List[str]:
        """Get article URLs from category page"""
        url = f"{self.base_url}/{category}"
        response = self._retry_request(url)
        
        if not response:
            return []
        
        soup = self._parse_html(response.text)
        urls = []
        
        # Find article links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/article/' in href or '/' in href:
                # Clean and validate URL
                if href.startswith('http'):
                    urls.append(href)
                elif href.startswith('/'):
                    urls.append(f"{self.base_url}{href}")
        
        # Remove duplicates and filter valid article URLs
        seen = set()
        valid_urls = []
        for url in urls:
            if url not in seen and self._is_valid_article_url(url):
                seen.add(url)
                valid_urls.append(url)
        
        return valid_urls[:20]  # Limit to 20 articles per category
    
    def _is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article URL"""
        invalid_patterns = ['/video/', '/photo/', '/podcast/', '/tag/', '/search/', '/author/']
        return not any(pattern in url for pattern in invalid_patterns)
    
    def parse_article(self, url: str) -> Optional[Dict]:
        """Parse a single article"""
        response = self._retry_request(url)
        
        if not response:
            return None
        
        soup = self._parse_html(response.text)
        
        # Extract article data
        article = {
            'url': url,
            'source': 'VNExpress',
        }
        
        # Title
        title_elem = soup.find('h1', class_='title-detail') or soup.find('h1')
        if title_elem:
            article['title'] = title_elem.get_text(strip=True)
        
        # Description/Summary
        desc_elem = soup.find('p', class_='description') or soup.find('meta', property='og:description')
        if desc_elem:
            article['description'] = desc_elem.get('content', '') or desc_elem.get_text(strip=True)
        
        # Content
        content_elem = soup.find('article', class_='fck_detail') or soup.find('div', class_='content-detail')
        if content_elem:
            paragraphs = content_elem.find_all('p')
            article['content'] = '\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        # Author
        author_elem = soup.find('p', class_='author') or soup.find('meta', attrs={'name': 'author'})
        if author_elem:
            article['author'] = author_elem.get('content', '') or author_elem.get_text(strip=True)
        
        # Published date
        date_elem = soup.find('span', class_='date') or soup.find('meta', property='article:published_time')
        if date_elem:
            article['published_date'] = date_elem.get('content', '') or date_elem.get_text(strip=True)
        
        # Tags
        tags = []
        for tag in soup.find_all('a', class_='tag-item'):
            tags.append(tag.get_text(strip=True))
        if tags:
            article['tags'] = tags
        
        return article if 'title' in article else None
