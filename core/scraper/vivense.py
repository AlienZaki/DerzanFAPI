import logging
import traceback
from requests_html import HTMLSession
from concurrent.futures import ThreadPoolExecutor, as_completed
from fake_useragent import UserAgent
from core.models import Vendor
from core.db import client
from requests.exceptions import ProxyError
from urllib3.exceptions import MaxRetryError

ua = UserAgent()


class VivenseScraper:
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
        session.headers['user-agent'] = VivenseScraper.USER_AGENT.google
        return session

    def get_or_create_vendor(self):
        vendor_name = 'vivense'
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

    def search_nested_dict(self, nested_dict, search_key):
        """Search for all occurrences of a key in a nested dictionary recursively."""
        matches = []
        for key, value in nested_dict.items():
            if key == search_key:
                matches.append(value)
            elif isinstance(value, dict):
                matches.extend(self.search_nested_dict(value, search_key))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        matches.extend(self.search_nested_dict(item, search_key))
        return matches


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
                except:
                    session.abort_transaction()


    def get_attribute_value(self, type, values):
        if type == 'color':
            value = values[0][type] and values[0][type]['title'] and values[0][type]['title']['tr']
        elif type == 'text':
            value = values[0][type] and values[0][type]['tr']
        elif type == 'boolean':
            value = values[0][type]
            value = 'Evet' if value else 'Hayır'
        elif type == 'numberDouble':
            value = values[0][type]
            value = int(value) if value.is_integer() else value
        else:
            value = None
        return value

    def parse_product_data(self, p):
        currencies = {'TRY': 'TL'}
        data = dict()
        data['vendor_id'] = self.vendor.id
        data['main_category'] = self.vendor.category
        data['category'] = '///'.join([i['title']['tr'] for i in p['breadcrumbs'][1:]])
        data['code'] = p['vsin']
        data['name'] = p['title']['tr']
        data['url'] = f'https://app.vivense.com/products/vsin/{p["vsin"]}'
        data['variant_group'] = p['variantId'] or ''
        data['variant_features'] = []
        data['price'] = p['siteData']['prices'][0]['unitPrice']
        data['list_price'] = p['siteData']['prices'][0]['generalMarketPrice'] or data['price']
        data['currency'] = currencies[p['siteData']['prices'][0]['currencyCode']]
        data['images'] = ['https://img.vivense.com/' + i['newFileName'] for i in p['media']]

        # Check and get variant features
        if variant_group := p.get('variantGroup'):
            for group in variant_group['groups']:
                attribute = group['attribute']
                attr_key, attr_type = attribute['title']['tr'], attribute['attributeType']
                for product in [i for i in group['products'] if i['product']['vsin'] == p['vsin']]:
                    attr_values = product['attributeValues']
                    attr_value = self.get_attribute_value(type=attr_type, values=attr_values)
                    data['variant_features'].append({'key': attr_key, 'value': attr_value})

        # data['variant_key'] = p['variantGroup'] and p['variantGroup']['groups'][0]['attribute']['title']['tr']
        # attribute_type = p['variantGroup'] and p['variantGroup']['groups'][0]['attribute']['attributeType']
        # data['variant_value'] = p['variantGroup'] and [self.get_attribute_value(type=attribute_type, values=i['attributeValues']) for i in p['variantGroup']['groups'][0]['products'] if i['product']['vsin'] == p['vsin']]
        # data['variant_value'] = data['variant_value'] and data['variant_value'][0]




        # print(p)
        attributes = []
        for a in p['attributes']:
            key = a['title']['tr']

            value = a['values'] and a['values'][0] and self.get_attribute_value(type=a['type'], values=a['values'])
            if value:
                attributes.append((key, value))
            # print(key, a['type'], value)

        attributes_html = '\n'.join([f'<tr><th>{key}</th><td>{value}</td></tr>' for key, value in attributes])
        data['description'] = f"""<div class="panel-body" style="display: block;">
                                        <table class="table">
                                            <tbody id="producttables" class="desctab">
                                                {attributes_html}
                                            </tbody>
                                        </table>
                                    </div><br>"""
        elements = ''
        for item in p["dimensions"]:
            title = item["title"] and item["title"]["tr"] or ''
            width = item['widthCm'] and f"{item['widthCm']} cm"
            height = item['heightCm'] and f"{item['heightCm']} cm"
            length = item['lengthCm'] and f"{item['lengthCm']} cm"
            weight = item['weightKg'] and f"{item['weightKg']} kg"
            radius = item['radiusCm'] and f"{item['radiusCm']} cm"
            diameter = item['diameterCm'] and f"{item['diameterCm']} cm"
            elements += f"""<tr><th>{title}</th>"""
            if width: elements += f'<td>{width}</td>'
            if height: elements += f'<td>{height}</td>'
            if length: elements += f'<td>{length}</td>'
            if weight: elements += f'<td>{weight}</td>'
            if radius: elements += f'<td>{radius}</td>'
            if diameter: elements += f'<td>{diameter}</td>'
            elements += '</tr>'

        data['description'] += f"""
                <div class="panel panel-default custom-panel" id="part87">
                    <div class="panel-heading pd-productsize open">Ürün Boyutları</div>
                    <div class="panel-body nopadding" style="display: block;">
                        <table class="table product-feature">
                            <thead><tr><th class="main-header">&nbsp;</th><th>Genişlik</th><th>Derinlik</th><th>Yükseklik</th></tr></thead>
                            <tbody>
                                {elements}
                            </tbody>
                        </table>
                    </div>
                </div>
                """

        return data

    def get_and_parse_product_details_by_vsin(self, vsin):
        url = f'https://app.vivense.com/products/vsin/{vsin}'
        try:
            # self.update_session_proxy()
            r = self.session.get(url)
            data = r.json()['items'][0]
            return self.parse_product_data(data)
        except (MaxRetryError, ProxyError) as e:
            print('=> Warning:', e)
            return self.get_and_parse_product_details_by_vsin(vsin)
        except Exception:
            traceback.print_exc()
            print('ERROR:', url)

    def get_product_details(self, url):
        try:
            # self.update_session_proxy()
            r = self.session.get(url)
            if r.status_code == 200:
                data = r.json()['items'][0]
                # get variant and only for the first group
                vsins = data['variantGroup'] and [p['vsin'] for p in data['variantGroup']['products']]
                if vsins:
                    return [self.get_and_parse_product_details_by_vsin(vsin) for vsin in vsins]
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
                products_urls = [f'https://app.vivense.com/products/vsin/{i["vsin"]}' for i in r.json()['items']]
            return products_urls
        except Exception:
            traceback.print_exc()
            print('ERROR URL:', page_url)
            return products_urls

    def get_category_products(self, category_url):
        r = self.session.get(category_url)
        size = r.json()['size']
        last_page = size // 32

        # get category pagination
        pagination = [f'{category_url}?page={i}' for i in range(1, last_page + 1)]
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
        r = self.session.get('https://app.vivense.com/menu')
        links = self.search_nested_dict(r.json(), 'link')
        categories = [f'https://app.vivense.com/Products/listing/search/{i["alias"]}-c-{i["params"]["vsin"]}'
                      for i in links if 'vsin' in i["params"]]
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
    bot = VivenseScraper(max_workers=10, proxy=True)
    bot.run(force_refresh=False)

    # bot.vendor.products_urls.filter(status=1).update(status=0)
    # bot.vendor.products.all().delete()

    # bot.vendor.delete_all_products()


    # SV4-286

    # products = bot.get_product_details('https://app.vivense.com/products/vsin/TO3-729')
    # # print(products)
    # for p in products:
    #     print(p)
    # bot.save_products(products)