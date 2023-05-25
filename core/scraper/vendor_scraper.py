import logging
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor
from core.models import Vendor


class Scraper:
    def __init__(self, vendor_name, max_workers=5, proxy=False, host='localhost:8000'):
        self.vendor_name = vendor_name
        self.host = host
        self.max_workers = max_workers
        self.proxy = proxy

        self.ua = UserAgent()
        logging.basicConfig(
            level=logging.DEBUG,
            datefmt='%Y-%m-%d %H:%M:%S',
            format='%(asctime)s %(levelname)s %(message)s',
            # filename='logs.log'
        )
        self.session.headers['user-agent'] = self.ua.google

        self.proxy_url_string = None
        self.proxies = {
            'http': f'http://{self.proxy_url_string}',
            'https': f'https://{self.proxy_url_string}'
        }
        self.update_session_proxy()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Create vendor if it doesn't exist
        vendor_nickname = 'Mobilya'
        category = 'Ev ve Bahçe / Mobilya'

        # Get or create vendor
        self.vendor = Vendor.find_by_name(vendor_name)
        if not self.vendor:
            # Create vendor
            self.vendor = Vendor(name=vendor_name, category=category, nickname=vendor_nickname)
            self.vendor.save()

    def scrape(self):
        raise NotImplementedError

    def save(self, data):
        # Connect to_lang database
        conn = sqlite3.connect('scraped_data.db')
        c = conn.cursor()

        # Create table if it doesn't exist
        c.execute('''CREATE TABLE IF NOT EXISTS scraped_data
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     source TEXT,
                     data TEXT)''')

        # Insert data into table
        c.execute('INSERT INTO scraped_data (source, data) VALUES (?, ?)', (self.source, data))

        # Commit changes and close connection
        conn.commit()
        conn.close()