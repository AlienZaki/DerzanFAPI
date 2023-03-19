from dotenv import load_dotenv
from celery import Celery
from core.scraper import ScraperFactory
import os


load_dotenv()
config = os.environ
app = Celery('derzan', broker=config['CELERY_BROKER'], backend=config['CELERY_BACKEND'])


@app.task(name='Scraping Task')
def scraping_task(vendor_name, host, flush, proxy, workers):
    print(f'=> [{vendor_name}] Scraping Task Started...')
    scraper = ScraperFactory.get_vendor_scraper_by_name(vendor_name)
    scraper(host=host, max_workers=workers, proxy=proxy).run(flush)
    print(f'=> [{vendor_name}] Scraping Task Finished.')