import pprint
from bson import ObjectId
from pymongo import errors
from core.db import (
    db,
    vendors_collection,
    products_collection,
    product_urls_collection,
)


class Vendor:
    def __init__(self, name, nickname='', category='', language='tr', id=''):
        self.name = name.lower()
        self.nickname = nickname
        self.category = category
        self.language = language
        self.id = id

    def get_product_urls(self, status=None):
        query = {'vendor_id': self.id}
        if status is not None:
            query['status'] = status
        cursor = product_urls_collection.find(query).batch_size(1000)

        return cursor

    def get_product_urls_count(self, status=None):
        query = {'vendor_id': self.id}
        if status is not None:
            query['status'] = status
        return product_urls_collection.count_documents(query)

    def get_products(self, offset=0, limit=1000, not_translated=False, lang=None):
        if limit == -1:
            limit = self.get_products_count()

        query = [
            {
                '$match': {
                    'vendor_id': self.id
                }
            },
            {
                '$lookup': {
                    'from': 'vendors',
                    'localField': 'vendor_id',
                    'foreignField': '_id',
                    'as': 'vendor'
                }
            },
            {
                '$unwind': {
                    'path': '$vendor',
                    'preserveNullAndEmptyArrays': True
                }
            },
            {
                '$project': {
                    'vendor_id': 0,
                }
            },
            {
                '$addFields': {
                    'features_html': {
                        '$reduce': {
                            'input': '$variant_features',
                            'initialValue': '',
                            'in': {
                                '$concat': [
                                    '$$value',
                                    '<',
                                    {'$replaceAll': {'input': '$$this.key', 'find': ' ', 'replacement': '_'}},
                                    '><![CDATA[',
                                    {'$toString': '$$this.value'},
                                    ']]></',
                                    {'$replaceAll': {'input': '$$this.key', 'find': ' ', 'replacement': '_'}},
                                    '>',
                                ]
                            }
                        }
                    }
                }
            }
        ]

        if not_translated:
            query.append({
                '$match': {
                    f'translation.{lang}': {'$exists': False}
                }
            })

        query.append({'$skip': offset})
        query.append({'$limit': limit})

        products = products_collection.aggregate(query)
        return products

    def get_translated_products(self, lang, offset=0, limit=1000):
        query = [
            {
                '$match': {
                    'vendor_id': self.id,
                    'translation': {'$exists': True},
                    f'translation.{lang}': {'$exists': True}
                }
            },
            {
                '$project': {
                    '_id': 1,
                    'code': 1,
                    'name': 1,
                    'description': 1,
                    'translation': 1,
                }
            },
            {
                '$skip': offset
             }
        ]

        if limit:
            query.append({'$limit': limit})

        products = products_collection.aggregate(query)
        return products

    def get_products_count(self):
        return products_collection.count_documents({'vendor_id': self.id})

    def bulk_create_products(self, products):
        # print('=> Inserting products...')
        docs = products.copy()
        for d in docs:
            d['vendor_id'] = self.id
        try:
            products_collection.insert_many(docs, ordered=False)
        except errors.BulkWriteError as bwe:
            for error in bwe.details['writeErrors']:
                if error['code'] != 11000:  # duplicate error
                    print('ERROR:', error)
                    raise bwe

                docs.remove(error['op'])  # remove failed docs
        print(f'=> {len(products)} documents - {len(docs)} inserted - {len(products) - len(docs)} failed')

    def bulk_create_product_urls(self, product_urls):
        # print('=> inserting product urls...')
        docs = product_urls.copy()
        for d in docs:
            d['vendor_id'] = self.id
            if 'status' not in d:
                d['status'] = 0
        try:
            product_urls_collection.insert_many(docs, ordered=False)
        except errors.BulkWriteError as bwe:
            for error in bwe.details['writeErrors']:
                print(error['errmsg'])
                docs.remove(error['op'])  # remove failed docs
        print(f'=> {len(product_urls)} documents - {len(docs)} inserted - {len(product_urls) - len(docs)} failed')

    def bulk_update_product_urls_status(self, urls, status):
        # print('=> Updating product urls status...')
        try:
            product_urls_collection.update_many({'url': {'$in': urls}}, {'$set': {'status': status}})
        except errors.BulkWriteError as bwe:
            print('ERROR:', bwe)

    def add_product_translation(self, proudct_id, lang, translation):
        try:
            products_collection.update_one({'_id': proudct_id}, {'$set': {f'translation.{lang}': translation}})
        except errors.BulkWriteError as bwe:
            print('ERROR:', bwe)

    def delete_all_products(self):
        # delete all vendor products
        return products_collection.delete_many({'vendor_id': self.id})

    def delete_all_product_urls(self):
        # delete all vendor product urls
        return product_urls_collection.delete_many({'vendor_id': self.id})

    def save(self):
        vendor_dict = self.to_dict()
        if self.id:
            vendors_collection.replace_one({'_id': self.id}, vendor_dict)
        else:
            result = vendors_collection.insert_one(vendor_dict)
            self.id = result.inserted_id

    def to_dict(self):
        vendor_dict = {
            'name': self.name,
            'nickname': self.nickname,
            'category': self.category,
            'language': self.language,
        }
        if self.id:
            vendor_dict['_id'] = self.id
        return vendor_dict

    @staticmethod
    def from_dict(vendor_dict):
        return Vendor(
            vendor_dict['name'],
            vendor_dict.get('nickname'),
            vendor_dict.get('category'),
            vendor_dict.get('language'),
            vendor_dict.get('_id')
        )

    @classmethod
    def find_by_name(cls, name):
        vendor_dict = vendors_collection.find_one({'name': name.lower()})
        return cls.from_dict(vendor_dict) if vendor_dict else None

    @classmethod
    def find_by_id(cls, id):
        vendor_dict = vendors_collection.find_one({'_id': ObjectId(id)})
        return cls.from_dict(vendor_dict) if vendor_dict else None

    @classmethod
    def get_all(cls):
        vendor_dict_list = vendors_collection.find()
        return [cls.from_dict(vendor_dict) for vendor_dict in vendor_dict_list] if vendor_dict_list else None

    def __str__(self):
        return self.name


if __name__ == '__main__':
    # vendor_name = 'vivense'
    # vendor = Vendor.find_by_name(vendor_name)
    # if not vendor:
    #     vendor = Vendor(name=vendor_name)
    #     vendor.save()
    #
    # print(vendor.id)

    # for p in vendor.get_translated_products('ar'):
    #     print(p)

    # from bson.objectid import ObjectId

    # products_collection.update_many(
    #     {"vendor_id": ObjectId('641251775981a1a080731f28')},
    #     {"$unset": {"translation.ar": ""}}
    # )


    #
    # product_links = vendor.get_product_urls(status=0)
    # total_products = vendor.get_product_urls_count(status=0)
    # print(total_products)

    # id = ObjectId('641255a6ff9cbf6d76d8e307')
    # translation = {
    #     'name': 'Name2',
    #     'description': 'Description2'
    # }
    # vendor.add_product_translation(id, 'ar', translation)

    # products = vendor.get_product_urls()
    # # print(products.batch_size())
    # for product in products:
    #     print(product)

    # urls = [i['url'] for i in products]
    # vendor.bulk_update_product_urls_status(urls, 0)
    # vendor.delete_all_products()





    translation_memory_collection = db['translation_memory']
    # Retrieve all translation_memory documents
    translation_memory_documents = translation_memory_collection.find()

    # Iterate over each translation_memory document
    for tm_document in translation_memory_documents:
        source_text = tm_document["source_text"]

        # Search for products that contain the source_text in their name or description
        product_filter = {
            "$or": [
                {"name": {"$regex": source_text, "$options": "i"}},
                {"description": {"$regex": source_text, "$options": "i"}}
            ]
        }
        matching_products = products_collection.find(product_filter)

        # Get the list of matching product IDs
        matching_product_ids = [str(product["_id"]) for product in matching_products]

        print('=>', source_text, matching_product_ids)
        # Update the translation_memory document with the matching product IDs
        translation_memory_collection.update_one(
            {"_id": ObjectId(tm_document["_id"])},
            {"$set": {"products": matching_product_ids}}
        )
