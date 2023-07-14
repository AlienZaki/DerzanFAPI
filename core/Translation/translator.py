from requests_html import HTMLSession
from fake_useragent import UserAgent
import re
import json
import time
from pathlib import Path
from core.models import Vendor
from bs4 import BeautifulSoup
from core.Translation.bing import BingTranslator
from concurrent.futures import wait, as_completed


if __name__ == '__main__':
    key = "d74339cf185c4d42896344bcbfbc61d6"
    location = "germanywestcentral"
    translator = BingTranslator(key, location, max_workers=25)

    languages = ['ar', 'en']
    to_lang = 'ar'

    vendors = Vendor.get_all()
    vendors = [vendors[0]]

    for to_lang in languages:
        for vendor in vendors:
            total_products = vendor.get_products_count()
            print('=> Vendor:', vendor, total_products)
            products = vendor.get_products(limit=50000, not_translated=True, lang=to_lang) #50000
            # products = [list(products)[1]]

            translated_products = []
            counter = 0

            futures = [translator.executor.submit(translator.translate_product, product, to_lang) for product in products]


            for i, future in enumerate(as_completed(futures), 1):
                counter += 1
                print(f'=> Products [{counter}/{total_products}] - {to_lang}')
                product = future.result()
                # print(product['translation']['description'])
                vendor.add_product_translation(product['_id'], to_lang, product['translation'])
                print(product['_id'])


