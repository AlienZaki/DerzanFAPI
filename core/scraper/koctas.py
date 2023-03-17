import logging
import traceback
from requests_html import HTMLSession
from concurrent.futures import ThreadPoolExecutor, as_completed
from fake_useragent import UserAgent
from core.models import Vendor
from core.db import client
from requests.exceptions import ProxyError
from urllib3.exceptions import MaxRetryError


import string
import random


class KoctasScraper:
    USER_AGENT = UserAgent()
    PROXIES = {
        'http': 'http://brd-customer-hl_24995ae6-zone-data_center:n4r98tzbvxik@zproxy.lum-superproxy.io:22225',
        'https': 'https://brd-customer-hl_24995ae6-zone-data_center:n4r98tzbvxik@zproxy.lum-superproxy.io:22225'
    }

    def __init__(self, host='localhost:8000', max_workers=10, proxy=False):
        self.session = self.create_session()
        self.host = host
        self.configure_logging()
        self.proxy = proxy
        self.update_session_proxy()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.vendor = self.get_or_create_vendor()

    def configure_logging(self):
        logging.basicConfig(
            level=logging.DEBUG,
            datefmt='%Y-%m-%d %H:%M:%S',
            format='%(asctime)s %(levelname)s %(message)s',
            # filename='logs.log'
        )

    def create_session(self):
        session = HTMLSession()
        session.headers['user-agent'] = self.USER_AGENT.google
        return session

    def get_or_create_vendor(self):
        vendor_name = 'koctas'
        vendor_nickname = 'Mobilya'
        category = 'Ev ve Bahçe / Mobilya'

        vendor = Vendor.find_by_name(vendor_name)
        if not vendor:
            vendor = Vendor(name=vendor_name, category=category, nickname=vendor_nickname)
            vendor.save()
        return vendor

    def update_session_proxy(self):
        print('=> Update Proxy..')
        if self.proxy:
            self.session = self.create_session()
            self.session.proxies = self.PROXIES

    def save_products(self, products):
        print('Saving...')
        product_list = products.copy()
        product_urls = [p['url'] for p in product_list]

        # Store data as a transaction
        with client.start_session() as session:
            with session.start_transaction():
                try:
                    # bulk save products
                    self.vendor.bulk_create_products(product_list)
                    # update product urls status to 1 as scraped flag
                    self.vendor.bulk_update_product_urls_status(urls=product_urls, status=1)
                    # commit
                    session.commit_transaction()
                    print('Saved!')
                except Exception:
                    session.abort_transaction()

    def parse_product_data(self, p, variant_group=None):
        currencies = {'TRY': 'TL'}
        data = dict()
        data['main_category'] = self.vendor.category
        data['code'] = p['code']
        data['url'] = f'https://occ2.koctas.com.tr/koctaswebservices/v2/koctas/products/{p["code"]}?cartId=&uid=anonymous'
        data['name'] = f'{p["brandName"]} {p["name"]}' if 'brandName' in p else p['name']
        data['category'] = '///'.join([i['name'] for i in p['categories']])
        data['list_price'] = p['price']['value']
        data['price'] = p['priceWithDiscount']['value']
        data['currency'] = currencies[p['price']['currencyIso']]
        data['product_features'] = [{'key': j['name'], 'value': ' '.join([v['value']
                                    for v in j['featureValues']])}
                                    for i in p['classifications']
                                    for j in i['features']] if 'classifications' in p else []
        data['variant_features'] = [{'key': f['name'], 'value': f['value']} for i in p['baseOptions'] for f in
                                    i['selected']['variantOptionQualifiers']]
        data['variant_group'] = data['variant_features'] and variant_group or ''
        data['description'] = p['description'] or p['summary']
        data['images'] = list(set([i['url'] for i in p['images'] if i['format'] == 'zoom']))
        return data

    def get_and_parse_product_details_by_code(self, code, variant_group):
        url = f'https://occ2.koctas.com.tr/koctaswebservices/v2/koctas/products/{code}?cartId=&uid=anonymous'
        try:
            r = self.session.get(url)
            data = r.json()
            return self.parse_product_data(data, variant_group)
        except (MaxRetryError, ProxyError) as e:
            print('=> Warning:', e)
            return self.get_and_parse_product_details_by_code(code, variant_group)
        except Exception:
            traceback.print_exc()
            print('ERROR:', url)

    def get_product_details(self, url):
        try:
            # self.update_session_proxy()
            r = self.session.get(url)
            if r.status_code == 200:
                data = r.json()
                # get variant and only for the first group
                product_codes = [p['code'] for i in data['baseOptions'] for p in i['options']]
                if product_codes:
                    # Create random variant group code
                    variant_group = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
                    return [self.get_and_parse_product_details_by_code(code, variant_group) for code in product_codes]
                else:
                    return [self.parse_product_data(data)]
            else:
                print(r.text)
                print('ERROR:', url)
        except (MaxRetryError, ProxyError) as e:
            print('=> Warning:', e)
            return self.get_product_details(url)
        except Exception:
            traceback.print_exc()
            print('ERROR:', url)

    def get_product_links(self, page_url):
        products_urls = []
        try:
            r = self.session.get(page_url)
            if r.status_code == 200:
                product_codes = [i['code'] for i in r.json()['results']['products']]
                product_urls = [
                    f'https://occ2.koctas.com.tr/koctaswebservices/v2/koctas/products/{code}?cartId=&uid=anonymous'
                    for code in product_codes]
            return product_urls
        except Exception:
            traceback.print_exc()
            print('ERROR URL:', page_url)
            return products_urls

    def get_category_products(self, category_url):
        r = self.session.get(category_url)
        last_page = r.json()['results']['pagination']['totalPages']


        # get category pagination
        pagination = [f'{category_url}&currentPage={i}' for i in range(0, last_page + 1)]
        logging.info(f'Pages found: {len(pagination)}')

        # get product links from pagination
        futures = []
        product_links = []
        for page in pagination:
            futures.append(self.executor.submit(self.get_product_links, page))
        for future in as_completed(futures):
            product_links.extend(future.result())
        logging.info(f'Product links found: {len(product_links)}')
        return product_links

    def get_categories(self):
        r = self.session.get('https://occ2.koctas.com.tr/koctaswebservices/v2/koctas/categoryNavigationComponent')
        categories = [f'https://occ2.koctas.com.tr/koctaswebservices/v2/koctas/search?pageSize=100&q=::category:{i["code"]}'
                      for i in r.json()['categoryListWsDTO']]
        return categories

    def flush_products_from_db(self):
        # Update product urls and delete all products
        product_links = []

        print('=> Deleting Products URLS...')
        self.vendor.delete_all_product_urls()

        print('=> Deleting Products...')
        self.vendor.delete_all_products()

        # get product urls from categories
        print('=> Getting product urls...')
        cats = self.get_categories()
        for i, cat in enumerate(cats, 1):
            print(f'=> Categories: [{i}/{len(cats)}]')
            links = self.get_category_products(cat)
            product_links.extend(links)
            # save product urls
            if links:
                self.vendor.bulk_create_product_urls([{'url': i} for i in links])

    def run(self, force_refresh=False):
        if force_refresh:
            self.flush_products_from_db()

        # get products from db
        product_links = self.vendor.get_product_urls(status=0)
        total_products = self.vendor.get_product_urls_count(status=0)
        counter = 0
        print('=> Prodcuts:', total_products)


        futures = []
        for product in product_links:
            futures.append(self.executor.submit(self.get_product_details, product['url']))

        products_data = []
        # for i, product in enumerate(page, 1):
        #     product_details = self.get_product_details(product.product_url)

        for i, future in enumerate(as_completed(futures), 1):
            counter += 1
            print(f'=> Products [{counter}/{total_products}]')
            product_details = future.result()
            if product_details and product_details:
                products_data.extend(product_details)
                # print(product_details)
                print('OK')

            # Export
            if i % 50 == 0 or i == len(futures):  # len(page)
                self.update_session_proxy()
                temp = products_data.copy()
                products_data = []
                self.save_products(temp)


if __name__ == '__main__':
    bot = KoctasScraper(max_workers=1, proxy=False)
    # bot.run(force_refresh=False)



    # bot.vendor.delete_all_products()


    # SV4-286

    products = bot.get_product_details('https://occ2.koctas.com.tr/koctaswebservices/v2/koctas/products/1000031443?cartId=&uid=anonymous')
    for p in products:
        print(p)
    # bot.save_products(products)
    #
    #


