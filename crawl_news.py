"""
Main script to crawl news from multiple sources and upload to Google Drive
"""
import os
import sys
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawlers import (
    VNExpressCrawler,
    TuoiTreCrawler,
    VietnamNetCrawler,
    DanTriCrawler,
    NEWS_SOURCES,
    CRAWLER_SETTINGS,
)
from src.services import get_drive_service

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'./data/logs/crawl_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)


def crawl_source(source_id: str, source_config: Dict) -> Dict:
    """Crawl a single news source"""
    logger.info(f"Starting crawl for {source_config['name']}")
    
    try:
        # Get crawler instance
        if source_id == 'vnexpress':
            crawler = VNExpressCrawler()
        elif source_id == 'tuoitre':
            crawler = TuoiTreCrawler()
        elif source_id == 'vietnamnet':
            crawler = VietnamNetCrawler()
        elif source_id == 'dantri':
            crawler = DanTriCrawler()
        else:
            logger.warning(f"Unknown source: {source_id}")
            return {'source': source_id, 'status': 'error', 'message': 'Unknown source'}
        
        # Crawl all articles
        articles = crawler.crawl_all(max_workers=CRAWLER_SETTINGS['max_workers'])
        
        logger.info(f"Crawled {len(articles)} articles from {source_config['name']}")
        
        return {
            'source': source_id,
            'name': source_config['name'],
            'folder': source_config['folder_name'],
            'articles': articles,
            'count': len(articles),
            'status': 'success'
        }
        
    except Exception as e:
        logger.error(f"Error crawling {source_id}: {e}")
        return {
            'source': source_id,
            'status': 'error',
            'message': str(e)
        }


def upload_to_drive(results: List[Dict], drive_service):
    """Upload crawl results to Google Drive"""
    upload_results = []
    
    for result in results:
        if result.get('status') == 'success':
            try:
                upload_result = drive_service.upload_crawled_data(
                    articles=result['articles'],
                    source_name=result['name'],
                    folder_name=result['folder']
                )
                upload_results.append({
                    'source': result['name'],
                    'folder': result['folder'],
                    'folder_id': upload_result.get('folder_id'),
                    'file_id': upload_result.get('file_id'),
                    'articles_uploaded': result['count'],
                    'status': 'success'
                })
                logger.info(f"Uploaded {result['count']} articles from {result['name']} to Drive")
            except Exception as e:
                logger.error(f"Error uploading {result['name']}: {e}")
                upload_results.append({
                    'source': result['name'],
                    'status': 'error',
                    'message': str(e)
                })
    
    return upload_results


def run_crawler(sources: List[str] = None):
    """Main function to run crawler"""
    start_time = datetime.now()
    logger.info(f"Starting news crawler at {start_time}")
    
    # Determine which sources to crawl
    if sources is None:
        sources = list(NEWS_SOURCES.keys())
    
    logger.info(f"Crawling sources: {', '.join(sources)}")
    
    # Crawl all sources in parallel
    crawl_results = []
    
    with ThreadPoolExecutor(max_workers=len(sources)) as executor:
        futures = {
            executor.submit(crawl_source, source_id, NEWS_SOURCES[source_id]): source_id
            for source_id in sources
            if source_id in NEWS_SOURCES
        }
        
        for future in as_completed(futures):
            source_id = futures[future]
            try:
                result = future.result()
                crawl_results.append(result)
            except Exception as e:
                logger.error(f"Error in future for {source_id}: {e}")
                crawl_results.append({
                    'source': source_id,
                    'status': 'error',
                    'message': str(e)
                })
    
    # Summary
    success_count = sum(1 for r in crawl_results if r.get('status') == 'success')
    total_articles = sum(r.get('count', 0) for r in crawl_results if r.get('status') == 'success')
    
    logger.info(f"Crawl completed: {success_count}/{len(sources)} sources, {total_articles} total articles")
    
    # Upload to Drive
    try:
        drive_service = get_drive_service()
        upload_results = upload_to_drive(crawl_results, drive_service)
        
        upload_success = sum(1 for r in upload_results if r.get('status') == 'success')
        logger.info(f"Upload completed: {upload_success}/{len(upload_results)} sources")
        
    except Exception as e:
        logger.error(f"Error uploading to Drive: {e}")
        upload_results = []
    
    # Final summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    summary = {
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'duration_seconds': duration,
        'sources': {
            'total': len(sources),
            'success': success_count,
            'failed': len(sources) - success_count
        },
        'articles': {
            'total': total_articles,
            'by_source': {
                r['name']: r.get('count', 0) 
                for r in crawl_results 
                if r.get('status') == 'success'
            }
        },
        'uploads': upload_results
    }
    
    logger.info(f"Total duration: {duration:.2f} seconds")
    logger.info("Crawl complete!")
    
    return summary


def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Crawl news from multiple sources')
    parser.add_argument(
        '--sources',
        nargs='+',
        choices=['vnexpress', 'tuoitre', 'vietnamnet', 'dantri'],
        help='Sources to crawl (default: all)'
    )
    parser.add_argument(
        '--no-upload',
        action='store_true',
        help='Skip upload to Google Drive'
    )
    
    args = parser.parse_args()
    
    # Run crawler
    summary = run_crawler(sources=args.sources)
    
    # Print summary
    print("\n" + "="*50)
    print("CRAWL SUMMARY")
    print("="*50)
    print(f"Sources: {summary['sources']['success']}/{summary['sources']['total']} successful")
    print(f"Total articles: {summary['articles']['total']}")
    print(f"Duration: {summary['duration_seconds']:.2f}s")
    print("="*50)


if __name__ == '__main__':
    main()
