from dotenv import load_dotenv
from celery import Celery
from .db import db
import time
import os


load_dotenv()
config = os.environ
app = Celery('derzan', broker=config['CELERY_BROKER'], backend=config['CELERY_BACKEND'])



@app.task(name='add task')
def add(x, y):
    print('=> Started..')
    time.sleep(10)
    db['products'].insert_one({'num1': x, 'num2': y})
    print('=> Finished.')
    return x + y