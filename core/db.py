from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId
from dotenv import load_dotenv
import os

load_dotenv()
config = os.environ
client = MongoClient(config['MONGO_URI'])
db = client['derzandb']


def migrate_collections():
    # Vendors
    print('=> Migrating vendors..')
    try:
        vendors_collection = db.create_collection('vendors')
    except:
        vendors_collection = db.vendors
    vendor_validator = {
        '$jsonSchema': {
            'bsonType': 'object',
            'title': 'Vendor Object Validation',
            'required': ['name'],
            'properties': {
                'name': {
                    'bsonType': 'string',
                    'description': '"name" must be a string and is required'
                },
                'nickname': {
                    'bsonType': 'string',
                },
                'website': {
                    'bsonType': 'string',
                },
            }
        }
    }
    db.command('collMod', 'vendors', validator=vendor_validator)
    vendors_collection.create_index([('name', ASCENDING)], unique=True)

    # Products
    print('=> Migrating products..')
    try:
        products_collection = db.create_collection('products')
    except:
        products_collection = db.products
    product_validator = {
        '$jsonSchema': {
            'bsonType': 'object',
            'required': ['code', 'name', 'vendor_id', 'category', 'price'],
            'properties': {
                'code': {
                    'bsonType': 'string',
                },
                'name': {
                    'bsonType': 'string',
                },
                'vendor_id': {
                    'bsonType': 'objectId',
                },
                'category': {
                    'bsonType': 'string',
                },
                'price': {
                    'bsonType': 'double',
                },
            }
        }
    }
    db.command('collMod', 'products', validator=product_validator)
    products_collection.create_index([('vendor_id', ASCENDING)])
    products_collection.create_index([('vendor_id', ASCENDING), ('code', ASCENDING)], unique=True)

    # Images
    print('=> Migrating images..')
    try:
        images_collection = db.create_collection('images')
    except:
        images_collection = db.images
    image_validator = {
        '$jsonSchema': {
            'bsonType': 'object',
            'required': ['url', 'product_id'],
            'properties': {
                'url': {
                    'bsonType': 'string',
                },
                'product_id': {
                    'bsonType': 'objectId',
                }
            }
        }
    }
    db.command('collMod', 'images', validator=image_validator)

    # Product URLs
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
    db.command('collMod', 'product_urls', validator=product_validator)
    product_urls_collection.create_index([('url', ASCENDING)], unique=True)
    product_urls_collection.create_index([('vendor_id', ASCENDING), ('status', ASCENDING)])

    print('=> Migrations completed!')


if __name__ == '__main__':
    migrate_collections()