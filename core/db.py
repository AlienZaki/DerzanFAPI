from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()
config = os.environ
client = MongoClient(config['MONGO_URI'])
db = client['derzandb']


