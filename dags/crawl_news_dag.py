"""
Airflow DAG for crawling news from multiple sources
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.utils.dates import days_ago

# Import crawl functions
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawlers import NEWS_SOURCES
from src.services import get_drive_service


# Default arguments
default_args = {
    'owner': 'data-platform',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def crawl_vnexpress(**context):
    """Crawl VNExpress"""
    from src.crawlers.vnexpress_crawler import VNExpressCrawler
    
    crawler = VNExpressCrawler()
    articles = crawler.crawl_all()
    
    # Push to XCom
    context['ti'].xcom_push(key='vnexpress_articles', value=articles)
    
    return len(articles)


def crawl_tuoitre(**context):
    """Crawl Tuổi Trẻ"""
    from src.crawlers.tuoitre_crawler import TuoiTreCrawler
    
    crawler = TuoiTreCrawler()
    articles = crawler.crawl_all()
    
    context['ti'].xcom_push(key='tuoitre_articles', value=articles)
    
    return len(articles)


def crawl_vietnamnet(**context):
    """Crawl VietnamNet"""
    from src.crawlers.vietnamnet_crawler import VietnamNetCrawler
    
    crawler = VietnamNetCrawler()
    articles = crawler.crawl_all()
    
    context['ti'].xcom_push(key='vietnamnet_articles', value=articles)
    
    return len(articles)


def crawl_dantri(**context):
    """Crawl Dân Trí"""
    from src.crawlers.dantri_crawler import DanTriCrawler
    
    crawler = DanTriCrawler()
    articles = crawler.crawl_all()
    
    context['ti'].xcom_push(key='dantri_articles', value=articles)
    
    return len(articles)


def upload_to_drive(**context):
    """Upload all crawled data to Google Drive"""
    from datetime import datetime
    
    # Pull all articles from XCom
    articles_data = {}
    for source in ['vnexpress', 'tuoitre', 'vietnamnet', 'dantri']:
        articles = context['ti'].xcom_pull(key=f'{source}_articles', task_ids=f'crawl_{source}')
        if articles:
            articles_data[source] = articles
    
    # Upload to Drive
    drive_service = get_drive_service()
    
    results = []
    for source_id, articles in articles_data.items():
        config = NEWS_SOURCES.get(source_id, {})
        
        result = drive_service.upload_crawled_data(
            articles=articles,
            source_name=config.get('name', source_id),
            folder_name=config.get('folder_name', f'{source_id}-news')
        )
        
        results.append({
            'source': source_id,
            'file_id': result.get('file_id'),
            'article_count': len(articles)
        })
    
    return results


# Define DAG
dag = DAG(
    'crawl_news_dag',
    default_args=default_args,
    description='Crawl news from multiple Vietnamese news sources',
    schedule_interval='0 6,18 * * *',  # Run at 6 AM and 6 PM daily
    catchup=False,
    tags=['crawler', 'news', 'vietnam'],
)

# Task definitions
start_task = PythonOperator(
    task_id='start',
    python_callable=lambda: print("Starting news crawl..."),
    dag=dag,
)

crawl_vnexpress_task = PythonOperator(
    task_id='crawl_vnexpress',
    python_callable=crawl_vnexpress,
    dag=dag,
)

crawl_tuoitre_task = PythonOperator(
    task_id='crawl_tuoitre',
    python_callable=crawl_tuoitre,
    dag=dag,
)

crawl_vietnamnet_task = PythonOperator(
    task_id='crawl_vietnamnet',
    python_callable=crawl_vietnamnet,
    dag=dag,
)

crawl_dantri_task = PythonOperator(
    task_id='crawl_dantri',
    python_callable=crawl_dantri,
    dag=dag,
)

upload_task = PythonOperator(
    task_id='upload_to_drive',
    python_callable=upload_to_drive,
    dag=dag,
)

end_task = PythonOperator(
    task_id='end',
    python_callable=lambda: print("News crawl completed!"),
    dag=dag,
)

# Task dependencies
start_task >> [crawl_vnexpress_task, crawl_tuoitre_task, crawl_vietnamnet_task, crawl_dantri_task]
[crawl_vnexpress_task, crawl_tuoitre_task, crawl_vietnamnet_task, crawl_dantri_task] >> upload_task >> end_task
