"""
Tuổi Trẻ Crawler - Fixed URL structure
"""
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from .base_crawler import BaseCrawler


class TuoiTreCrawler(BaseCrawler):
    """Crawler for Tuổi Trẻ"""
    
    def __init__(self):
        super().__init__(
            name='TuoiTre',
            base_url='https://tuoitre.vn',
            folder_name='tuoitre-news',
            categories=['thoi-su', 'the-gioi', 'kinh-te', 'the-thao', 'cong-nghe', 'van-hoa', 'giao-duc']
        )
    
    def get_article_urls(self, category: str) -> List[str]:
        """Get article URLs from category page"""
        # TuoiTre uses /<category>.htm format
        url = f"{self.base_url}/{category}.htm"
        response = self._retry_request(url)
        
        if not response:
            return []
        
        soup = self._parse_html(response.text)
        urls = []
        
        # Find article links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('http') and 'tuoitre.vn' in href:
                urls.append(href)
            elif href.startswith('/'):
                urls.append(f"{self.base_url}{href}")
        
        # Remove duplicates
        seen = set()
        valid_urls = []
        for url in urls:
            if url not in seen and self._is_valid_article_url(url):
                seen.add(url)
                valid_urls.append(url)
        
        return valid_urls[:20]
    
    def _is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article URL"""
        invalid_patterns = ['/video/', '/album/', '/tag/', '/search/', '/error/', '/author/']
        return not any(pattern in url for pattern in invalid_patterns)
    
    def parse_article(self, url: str) -> Optional[Dict]:
        """Parse a single article"""
        response = self._retry_request(url)
        
        if not response:
            return None
        
        soup = self._parse_html(response.text)
        
        article = {
            'url': url,
            'source': 'TuoiTre',
        }
        
        # Title
        title_elem = soup.find('h1', class_='article-title') or soup.find('h1', class_='title')
        if not title_elem:
            title_elem = soup.find('meta', property='og:title')
        if title_elem:
            article['title'] = title_elem.get('content', '') or title_elem.get_text(strip=True)
        
        # Description
        desc_elem = soup.find('h2', class_='article-summary') or soup.find('meta', property='og:description')
        if desc_elem:
            article['description'] = desc_elem.get('content', '') or desc_elem.get_text(strip=True)
        
        # Content
        content_elem = soup.find('div', class_='article-content') or soup.find('div', id='maincontent')
        if content_elem:
            paragraphs = content_elem.find_all('p')
            article['content'] = '\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        # Author
        author_elem = soup.find('span', class_='author') or soup.find('meta', attrs={'name': 'author'})
        if author_elem:
            article['author'] = author_elem.get('content', '') or author_elem.get_text(strip=True)
        
        # Published date
        date_elem = soup.find('span', class_='date') or soup.find('time')
        if date_elem:
            article['published_date'] = date_elem.get('content', '') or date_elem.get_text(strip=True)
        
        return article if 'title' in article else None
