from dotenv import load_dotenv
from celery import Celery
from .db import db
from core.scraper.vivense import VivenseScraper
import os


load_dotenv()
config = os.environ
app = Celery('derzan', broker=config['CELERY_BROKER'], backend=config['CELERY_BACKEND'])


@app.task(name='Vivense Scraper')
def vivense_scraper_task(host, workers, flush, proxy):
    print('Task Started...')
    VivenseScraper(host=host, max_workers=workers, proxy=proxy).run(flush)
    print('Task Finished.')