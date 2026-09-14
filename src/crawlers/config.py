"""
Crawler Configuration - All news sources configuration
"""
from typing import Dict, List


# News sources configuration
NEWS_SOURCES: Dict[str, Dict] = {
    'vnexpress': {
        'name': 'VNExpress',
        'base_url': 'https://vnexpress.net',
        'folder_name': 'vnexpress-news',
        'categories': [
            {'id': 'thoi-su', 'name': 'Thời sự', 'url': 'https://vnexpress.net/thoi-su'},
            {'id': 'the-gioi', 'name': 'Thế giới', 'url': 'https://vnexpress.net/the-gioi'},
            {'id': 'kinh-doanh', 'name': 'Kinh tế', 'url': 'https://vnexpress.net/kinh-doanh'},
            {'id': 'the-thao', 'name': 'Thể thao', 'url': 'https://vnexpress.net/the-thao'},
            {'id': 'cong-nghe', 'name': 'Công nghệ', 'url': 'https://vnexpress.net/so-hoa'},
            {'id': 'giai-tri', 'name': 'Giải trí', 'url': 'https://vnexpress.net/giai-tri'},
            {'id': 'suc-khoe', 'name': 'Sức khỏe', 'url': 'https://vnexpress.net/suc-khoe'},
            {'id': 'giao-duc', 'name': 'Giáo dục', 'url': 'https://vnexpress.net/giao-duc'},
        ],
    },
    'tuoitre': {
        'name': 'Tuổi Trẻ',
        'base_url': 'https://tuoitre.vn',
        'folder_name': 'tuoitre-news',
        'categories': [
            {'id': 'thoi-su', 'name': 'Thời sự', 'url': 'https://tuoitre.vn/timeline/0/tin-tuc.htm'},
            {'id': 'the-gioi', 'name': 'Thế giới', 'url': 'https://tuoitre.vn/timeline/7/the-gioi.htm'},
            {'id': 'kinh-te', 'name': 'Kinh tế', 'url': 'https://tuoitre.vn/timeline/1/kinh-te.htm'},
            {'id': 'the-thao', 'name': 'Thể thao', 'url': 'https://tuoitre.vn/timeline/6/the-thao.htm'},
            {'id': 'cong-nghe', 'name': 'Công nghệ', 'url': 'https://tuoitre.vn/timeline/19/cong-nghe.htm'},
            {'id': 'van-hoa', 'name': 'Văn hóa', 'url': 'https://tuoitre.vn/timeline/3/van-hoa-xa-hoi.htm'},
            {'id': 'giao-duc', 'name': 'Giáo dục', 'url': 'https://tuoitre.vn/timeline/4/giao-duc.htm'},
        ],
    },
    'vietnamnet': {
        'name': 'VietnamNet',
        'base_url': 'https://vietnamnet.vn',
        'folder_name': 'vietnamnet-news',
        'categories': [
            {'id': 'thoi-su', 'name': 'Thời sự', 'url': 'https://vietnamnet.vn/thoi-su'},
            {'id': 'the-gioi', 'name': 'Thế giới', 'url': 'https://vietnamnet.vn/the-gioi'},
            {'id': 'kinh-te', 'name': 'Kinh tế', 'url': 'https://vietnamnet.vn/kinh-te'},
            {'id': 'the-thao', 'name': 'Thể thao', 'url': 'https://vietnamnet.vn/the-thao'},
            {'id': 'cong-nghe', 'name': 'Công nghệ', 'url': 'https://vietnamnet.vn/cong-nghe'},
            {'id': 'giai-tri', 'name': 'Giải trí', 'url': 'https://vietnamnet.vn/giai-tri'},
            {'id': 'giao-duc', 'name': 'Giáo dục', 'url': 'https://vietnamnet.vn/giao-duc'},
        ],
    },
    'dantri': {
        'name': 'Dân Trí',
        'base_url': 'https://dantri.com.vn',
        'folder_name': 'dantri-news',
        'categories': [
            {'id': 'thoi-su', 'name': 'Thời sự', 'url': 'https://dantri.com.vn/thoi-su.htm'},
            {'id': 'the-gioi', 'name': 'Thế giới', 'url': 'https://dantri.com.vn/the-gioi.htm'},
            {'id': 'kinh-te', 'name': 'Kinh tế', 'url': 'https://dantri.com.vn/kinh-te.htm'},
            {'id': 'the-thao', 'name': 'Thể thao', 'url': 'https://dantri.com.vn/the-thao.htm'},
            {'id': 'cong-nghe', 'name': 'Công nghệ', 'url': 'https://dantri.com.vn/cong-nghe.htm'},
            {'id': 'giai-tri', 'name': 'Giải trí', 'url': 'https://dantri.com.vn/giai-tri.htm'},
            {'id': 'giao-duc', 'name': 'Giáo dục', 'url': 'https://dantri.com.vn/giao-duc.htm'},
        ],
    },
}


# Crawler settings
CRAWLER_SETTINGS = {
    'timeout': 30,
    'retry_count': 3,
    'max_workers': 4,
    'delay_between_requests': 1,  # seconds
}


# Get all source IDs
def get_all_source_ids() -> List[str]:
    return list(NEWS_SOURCES.keys())


def get_source_config(source_id: str) -> Dict:
    return NEWS_SOURCES.get(source_id)


# Data output
DATA_OUTPUT_PATH = './data/raw'
