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
        self.name = name
        self.nickname = nickname
        self.category = category
        self.language = language
        self.id = id

    @staticmethod
    def from_dict(vendor_dict):
        return Vendor(
            vendor_dict['name'],
            vendor_dict.get('nickname'),
            vendor_dict.get('category'),
            vendor_dict.get('language'),
            vendor_dict.get('_id')
        )

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

    @classmethod
    def find_by_name(cls, name):
        vendor_dict = vendors_collection.find_one({'name': name})
        return cls.from_dict(vendor_dict) if vendor_dict else None

    @classmethod
    def find_by_id(cls, id):
        vendor_dict = vendors_collection.find_one({'_id': ObjectId(id)})
        return cls.from_dict(vendor_dict) if vendor_dict else None

    @classmethod
    def find_all(cls):
        vendor_dicts = vendors_collection.find({})
        return [cls.from_dict(vendor_dict) for vendor_dict in vendor_dicts]

    def save(self):
        vendor_dict = self.to_dict()

        if self.id:
            vendors_collection.replace_one({'_id': self.id}, vendor_dict)
        else:
            result = vendors_collection.insert_one(vendor_dict)
            self.id = result.inserted_id

    def delete(self):
        vendors_collection.delete_one({'_id': self.id})

    def get_product_urls(self, status=None):
        query = {'vendor_id': self.id}
        if status is not None:
            query['status'] = status
        cursor = product_urls_collection.find(query).batch_size(1000)
        # for doc in cursor:
        #     yield doc
        return cursor

    def get_product_urls_count(self):
        return product_urls_collection.count_documents({'vendor_id': self.id})

    def get_products(self):
        query = {'vendor_id': self.id}
        product_dicts = products_collection.find(query).batch_size(1000)
        return product_dicts

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
                docs.remove(error['op'])    # remove failed docs
        print(f'=> {len(products)} documents - {len(docs)} inserted - {len(products)-len(docs)} failed')

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
        print(f'=> {len(product_urls)} documents - {len(docs)} inserted - {len(product_urls)-len(docs)} failed')

    def bulk_update_product_urls_status(self, urls, status):
        # print('=> Updating product urls status...')
        try:
            product_urls_collection.update_many({'url': {'$in': urls}}, {'$set': {'status': status}})
        except errors.BulkWriteError as bwe:
            print('ERROR:', bwe)

    def delete_all_vendor_products(self):
        # delete all vendor products
        return products_collection.delete_many({'vendor_id': self.id})

    def delete_all_vendor_product_urls(self):
        # delete all vendor product urls
        return product_urls_collection.delete_many({'vendor_id': self.id})

    def __str__(self):
        return self.name


class ProductImage:
    def __init__(self, url, product_id):
        self.url = url
        self.product_id = product_id

    def save(self):
        # save the image to the database
        db.images.insert_one({
            'url': self.url,
            'product_id': self.product_id
        })

    @staticmethod
    def find_by_product(product_id):
        # find all images for a given product
        return db.images.find({'product_id': product_id})


class ProductURL:
    def __init__(self, vendor_id, url, status=0):
        self.vendor_id = vendor_id
        self.url = url
        self.status = status

    def save(self):
        # save the product URL to the database
        product_urls_collection.insert_one({
            'vendor_id': self.vendor_id,
            'url': self.url,
            'status': self.status
        })

    @staticmethod
    def find_by_vendor(vendor_id):
        # find all product URLs for a given vendor
        return product_urls_collection.find({'vendor_id': vendor_id})

    @staticmethod
    def find_by_status(status):
        # find all product URLs with a given status
        return product_urls_collection.find({'status': status})

    @staticmethod
    def find_by_url(url):
        # find a product URL by URL
        return product_urls_collection.find_one({'url': url})

    def to_dict(self):
        produc_url_dict = {
            'vendor_id': self.vendor_id,
            'url': self.url,
            'status': self.status,
        }
        return produc_url_dict


if __name__ == '__main__':
    vendor_name = 'Vivense'
    vendor = Vendor.find_by_name(vendor_name)
    if not vendor:
        vendor = Vendor(name=vendor_name)
        vendor.save()

    print(vendor.id)
    #
    products = vendor.get_product_urls()
    # # print(products.batch_size())
    # for p in products:
    #     print(p)

    urls = [i['url'] for i in products]
    vendor.bulk_update_product_urls_status(urls, 0)
    vendor.delete_all_vendor_products()

    #
    # products = [{'code': 'SV4-284', 'name': 'Fineroom Living Porto Keten Kare Kırlent 50X50 Lacivert', 'url': 'https://app.vivense.com/products/vsin/SV4-284', 'variant_group': '608f12ef64ce585a6479f513', 'main_category': 'Ev ve Bahçe / Mobilya', 'vendor_id': ObjectId('641190097cdd1365fa324f0d'), 'category': 'Ev Tekstili///Kırlent + Minder', 'price': 234.0, 'list_price': 234.0, 'currency': 'TL', 'images': ['https://img.vivense.com/images/a11ed60e8d27492597914ef3d07ca5aa.jpg', 'https://img.vivense.com/images/ae89286c45194bd48843b269fabff0a0.jpg'], 'description': '<div class="panel-body" style="display: block;">\n                                        <table class="table">\n                                            <tbody id="producttables" class="desctab">\n                                                <tr><th>Malzeme</th><td>Keten</td></tr>\n<tr><th>Ürün Tipleri</th><td>Kırlent</td></tr>\n<tr><th>Ürün Özelliği</th><td>İç Dolgusuz</td></tr>\n<tr><th>Renk</th><td>Mavi</td></tr>\n<tr><th>Marka</th><td>FİNEROOM LİVİNG</td></tr>\n<tr><th>Ek Bilgiler</th><td>İç yastık ile gönderilmektedir</td></tr>\n<tr><th>Kumaş Bakım/Temizlik Önerisi</th><td>30 derecede hassas yıkama yapmanız tavsiye edilir.</td></tr>\n<tr><th>Ölçü</th><td>-</td></tr>\n<tr><th>Ürün Kodu</th><td>SV4-284</td></tr>\n                                            </tbody>\n                                        </table>\n                                    </div><br>\n                <div class="panel panel-default custom-panel" id="part87">\n                    <div class="panel-heading pd-productsize open">Ürün Boyutları</div>\n                    <div class="panel-body nopadding" style="display: block;">\n                        <table class="table product-feature">\n                            <thead><tr><th class="main-header">&nbsp;</th><th>Genişlik</th><th>Derinlik</th><th>Yükseklik</th></tr></thead>\n                            <tbody>\n                                <tr><th>FİNEROOM LİVİNG PORTO KETEN KARE KIRLENT 50X50 LACİVERT</th><td>50.0 cm</td><td>50.0 cm</td><td>3.0 cm</td></tr>\n                            </tbody>\n                        </table>\n                    </div>\n                </div>\n                '}, {'code': 'SV4-285', 'name': 'Fineroom Living Porto Keten Kare Kırlent 50X50 Su Yeşili', 'url': 'https://app.vivense.com/products/vsin/SV4-285', 'variant_group': '608f12ef64ce585a6479f513', 'main_category': 'Ev ve Bahçe / Mobilya', 'vendor_id': ObjectId('641190097cdd1365fa324f0d'), 'category': 'Ev Tekstili///Kırlent + Minder', 'price': 234.0, 'list_price': 234.0, 'currency': 'TL', 'images': ['https://img.vivense.com/images/43ec4753c9d046bcadf02a1283475cff.jpg', 'https://img.vivense.com/images/494468e8e78a4284b7d572d55a32a93f.jpg'], 'description': '<div class="panel-body" style="display: block;">\n                                        <table class="table">\n                                            <tbody id="producttables" class="desctab">\n                                                <tr><th>Malzeme</th><td>Keten</td></tr>\n<tr><th>Ürün Tipleri</th><td>Kırlent</td></tr>\n<tr><th>Ürün Özelliği</th><td>İç Dolgusuz</td></tr>\n<tr><th>Renk</th><td>Mavi</td></tr>\n<tr><th>Marka</th><td>FİNEROOM LİVİNG</td></tr>\n<tr><th>Ek Bilgiler</th><td>İç yastık ile gönderilmektedir</td></tr>\n<tr><th>Kumaş Bakım/Temizlik Önerisi</th><td>30 derecede hassas yıkama yapmanız tavsiye edilir.</td></tr>\n<tr><th>Ölçü</th><td>-</td></tr>\n<tr><th>Ürün Kodu</th><td>SV4-285</td></tr>\n                                            </tbody>\n                                        </table>\n                                    </div><br>\n                <div class="panel panel-default custom-panel" id="part87">\n                    <div class="panel-heading pd-productsize open">Ürün Boyutları</div>\n                    <div class="panel-body nopadding" style="display: block;">\n                        <table class="table product-feature">\n                            <thead><tr><th class="main-header">&nbsp;</th><th>Genişlik</th><th>Derinlik</th><th>Yükseklik</th></tr></thead>\n                            <tbody>\n                                <tr><th>FİNEROOM LİVİNG PORTO KETEN KARE KIRLENT 50X50 SU YEŞİLİ</th><td>50.0 cm</td><td>50.0 cm</td><td>3.0 cm</td></tr>\n                            </tbody>\n                        </table>\n                    </div>\n                </div>\n                '}, {'code': 'SV4-286', 'name': 'Fineroom Living Porto Keten Kare Kırlent 50X50 Mor', 'url': 'https://app.vivense.com/products/vsin/SV4-286', 'variant_group': '608f12ef64ce585a6479f513', 'main_category': 'Ev ve Bahçe / Mobilya', 'vendor_id': ObjectId('641190097cdd1365fa324f0d'), 'category': 'Ev Tekstili///Kırlent + Minder', 'price': 234.0, 'list_price': 234.0, 'currency': 'TL', 'images': ['https://img.vivense.com/images/9231ab9c44174b0693f4256e4617a053.jpg', 'https://img.vivense.com/images/d6197baf3a304b099ae35d08bf267c4b.jpg'], 'description': '<div class="panel-body" style="display: block;">\n                                        <table class="table">\n                                            <tbody id="producttables" class="desctab">\n                                                <tr><th>Malzeme</th><td>Keten</td></tr>\n<tr><th>Ürün Tipleri</th><td>Kırlent</td></tr>\n<tr><th>Ürün Özelliği</th><td>İç Dolgusuz</td></tr>\n<tr><th>Renk</th><td>Mavi</td></tr>\n<tr><th>Marka</th><td>FİNEROOM LİVİNG</td></tr>\n<tr><th>Ek Bilgiler</th><td>İç yastık ile gönderilmektedir</td></tr>\n<tr><th>Kumaş Bakım/Temizlik Önerisi</th><td>30 derecede hassas yıkama yapmanız tavsiye edilir.</td></tr>\n<tr><th>Ölçü</th><td>-</td></tr>\n<tr><th>Ürün Kodu</th><td>SV4-286</td></tr>\n                                            </tbody>\n                                        </table>\n                                    </div><br>\n                <div class="panel panel-default custom-panel" id="part87">\n                    <div class="panel-heading pd-productsize open">Ürün Boyutları</div>\n                    <div class="panel-body nopadding" style="display: block;">\n                        <table class="table product-feature">\n                            <thead><tr><th class="main-header">&nbsp;</th><th>Genişlik</th><th>Derinlik</th><th>Yükseklik</th></tr></thead>\n                            <tbody>\n                                <tr><th>FİNEROOM LİVİNG PORTO KETEN KARE KIRLENT 50X50 MOR</th><td>50.0 cm</td><td>50.0 cm</td><td>3.0 cm</td></tr>\n                            </tbody>\n                        </table>\n                    </div>\n                </div>\n                '}, {'code': 'SV4-287', 'name': 'Fineroom Living Porto Keten Kare Kırlent 50X50 Pembe', 'url': 'https://app.vivense.com/products/vsin/SV4-287', 'variant_group': '608f12ef64ce585a6479f513', 'main_category': 'Ev ve Bahçe / Mobilya', 'vendor_id': ObjectId('641190097cdd1365fa324f0d'), 'category': 'Ev Tekstili///Kırlent + Minder', 'price': 234.0, 'list_price': 234.0, 'currency': 'TL', 'images': ['https://img.vivense.com/images/c94b7f50c3544a589a2219de6c75517f.jpg', 'https://img.vivense.com/images/ee34846a615f4d8fb4a6c445a2d1c430.jpg'], 'description': '<div class="panel-body" style="display: block;">\n                                        <table class="table">\n                                            <tbody id="producttables" class="desctab">\n                                                <tr><th>Malzeme</th><td>Keten</td></tr>\n<tr><th>Ürün Tipleri</th><td>Kırlent</td></tr>\n<tr><th>Ürün Özelliği</th><td>İç Dolgusuz</td></tr>\n<tr><th>Renk</th><td>Mavi</td></tr>\n<tr><th>Marka</th><td>FİNEROOM LİVİNG</td></tr>\n<tr><th>Ek Bilgiler</th><td>İç yastık ile gönderilmektedir</td></tr>\n<tr><th>Kumaş Bakım/Temizlik Önerisi</th><td>30 derecede hassas yıkama yapmanız tavsiye edilir.</td></tr>\n<tr><th>Ölçü</th><td>-</td></tr>\n<tr><th>Ürün Kodu</th><td>SV4-287</td></tr>\n                                            </tbody>\n                                        </table>\n                                    </div><br>\n                <div class="panel panel-default custom-panel" id="part87">\n                    <div class="panel-heading pd-productsize open">Ürün Boyutları</div>\n                    <div class="panel-body nopadding" style="display: block;">\n                        <table class="table product-feature">\n                            <thead><tr><th class="main-header">&nbsp;</th><th>Genişlik</th><th>Derinlik</th><th>Yükseklik</th></tr></thead>\n                            <tbody>\n                                <tr><th>FİNEROOM LİVİNG PORTO KETEN KARE KIRLENT 50X50 PEMBE</th><td>50.0 cm</td><td>50.0 cm</td><td>3.0 cm</td></tr>\n                            </tbody>\n                        </table>\n                    </div>\n                </div>\n                '}]
    # # vendor.bulk_create_products(products)
    # print(products[0])
    # products_collection.insert_one(products[0])