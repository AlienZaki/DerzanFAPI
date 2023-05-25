import pymongo.errors
from pymongo import MongoClient, ASCENDING, DESCENDING, errors
from bson import ObjectId
from dotenv import load_dotenv
import os
import pprint


load_dotenv()
config = os.environ
url = config['MONGO_URI'] + '?socketTimeoutMS=360000&connectTimeoutMS=360000'
client = MongoClient(url)
db = client['derzandb']
vendors_collection = db['vendors']
products_collection = db['products']
product_urls_collection = db['product_urls']


def migrate_vendor_collection():
    print('=> Migrating vendors..')
    try:
        vendors_collection = db.create_collection('vendors')
    except:
        vendors_collection = db.vendors
    vendor_validator = {
        '$jsonSchema': {
            'bsonType': 'object',
            'title': 'Vendor Object Validation',
            'required': ['name', 'nickname', 'category', 'language'],
            'properties': {
                'name': {
                    'bsonType': 'string',
                    'description': '"name" must be a string and is required'
                },
                'nickname': {
                    'bsonType': 'string',
                    'description': '"nickname" must be a string'
                },
                'category': {
                    'bsonType': 'string',
                    'description': '"category" must be a string'
                },
                'language': {
                    'bsonType': 'string',
                    'description': '"language" must be a string'
                },
            }
        }
    }
    # apply schema
    db.command('collMod', 'vendors', validator=vendor_validator)
    # index creation
    vendors_collection.create_index([('name', ASCENDING)], unique=True)


def migrate_product_collection():
    print('=> Migrating products..')
    try:
        products_collection = db.create_collection('products')
    except:
        products_collection = db.products
    product_validator = {
        '$jsonSchema': {
            'bsonType': 'object',
            'required': ['vendor_id', 'code', 'name', 'price', 'currency', 'main_category', 'category'],
            'properties': {
                'vendor_id': {
                    'bsonType': 'objectId',
                },
                'code': {
                    'bsonType': 'string',
                },
                'name': {
                    'bsonType': 'string',
                },
                'price': {
                    'bsonType': 'double',
                },
                'list_price': {
                    'bsonType': 'double',
                },
                'currency': {
                    'bsonType': 'string',
                },
                'subcategory': {
                    'bsonType': 'string',
                },
                'description': {
                    'bsonType': 'string',
                },
                'variant_group': {
                    'bsonType': 'string',
                },
                'variant_features': {
                    'bsonType': 'array'
                },
                'url': {
                    'bsonType': 'string',
                },
                'images': {
                    'bsonType': 'array',
                    'items': {
                        'bsonType': 'string'
                    }
                },
            }
        }
    }
    # apply schema
    db.command('collMod', 'products', validator=product_validator)
    # index creation
    products_collection.create_index([('vendor_id', ASCENDING)])
    products_collection.create_index([('vendor_id', ASCENDING), ('code', ASCENDING)], unique=True)


def migrate_product_urls_collection():
    print('=> Migrating product_urls..')
    try:
        product_urls_collection = db.create_collection('product_urls')
    except:
        product_urls_collection = db.product_urls
    product_url_validator = {
        '$jsonSchema': {
            'bsonType': 'object',
            'required': ['vendor_id', 'url', 'status'],
            'properties': {
                'vendor_id': {
                    'bsonType': 'objectId',
                },
                'url': {
                    'bsonType': 'string',
                },
                'status': {
                    'enum': [-1, 0, 1],
                }
            }
        }
    }
    # apply schema
    db.command('collMod', 'product_urls', validator=product_url_validator)
    # index creation
    product_urls_collection.create_index([('url', ASCENDING)], unique=True)
    product_urls_collection.create_index([('vendor_id', ASCENDING), ('status', ASCENDING)])

def migrate_translation_memory_collection():
    print('=> Migrating translation memory..')
    try:
        trans_memory_collection = db.create_collection('translation_memory')
    except:
        trans_memory_collection = db.translation_memory
    trans_memory_validator = {
        '$jsonSchema': {
            'bsonType': 'object',
            'required': ['source_text', 'source_lang', 'target_text', 'target_lang'],
        }
    }
    # apply schema
    db.command('collMod', 'translation_memory', validator=trans_memory_validator)
    # index creation
    trans_memory_collection.create_index([('source_text', ASCENDING), ('source_lang', ASCENDING), ('target_lang', ASCENDING)], unique=True)


def migrate_all_collections():
    # migrate vendor collection
    migrate_vendor_collection()

    # migrate product collection
    migrate_product_collection()

    # migrate product URLs collection
    migrate_product_urls_collection()

    # migrate translation memory collection
    migrate_translation_memory_collection()

    print('=> Migrations completed!')


if __name__ == '__main__':
    migrate_all_collections()