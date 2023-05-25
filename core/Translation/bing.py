import requests
import uuid
import json
import traceback
from bs4 import BeautifulSoup, NavigableString, Tag
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.Translation.TM import TM



class BingTranslator:
    def __init__(self, key, location, max_workers=10):
        self.key = key
        self.endpoint = "https://api.cognitive.microsofttranslator.com"
        self.location = location
        self.path = '/translate'
        self.constructed_url = self.endpoint + self.path
        self.headers = {
            'Ocp-Apim-Subscription-Key': self.key,
            'Ocp-Apim-Subscription-Region': self.location,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.TM = TM()

    def translate(self, text, from_lang, to_lang):
        text = str(text)

        # Translation memory
        result = self.TM.get_translation(text, from_lang, to_lang)
        if result:
            return result

        # Machine Translation
        body = [{'text': text}]
        params = {
            'api-version': '3.0',
            'from': from_lang,
            'to': to_lang   # ['en', 'ar']
        }
        response = requests.post(self.constructed_url, params=params, headers=self.headers, json=body)
        if response.status_code != 200:
            raise ValueError(response.text)

        target_text = response.json()[0]['translations'][0]['text']

        # Save translation to TM
        try:
            self.TM.save_translation(source_text=text, source_lang=from_lang, target_text=target_text, target_lang=to_lang)
        except:
            pass

        return target_text

    def translate_list(self, text_list, from_lang, to_lang):
        if not text_list:
            return text_list

        text_list = {i: text.strip() for i, text in enumerate(text_list)}
        memory_translations = {i: translation for i, text in text_list.items() if text and
                               (translation := self.TM.get_translation(text, from_lang, to_lang)) is not None}
        untranslated_indices = [i for i, text in text_list.items() if text and i not in memory_translations]

        text_list.update(memory_translations)
        if untranslated_indices:
            untranslated_texts = [text_list[i] for i in untranslated_indices]
            print('untranslated_texts:', untranslated_texts)
            body = [{'text': text} for text in untranslated_texts]
            params = {'api-version': '3.0', 'from': from_lang, 'to': to_lang}
            response = requests.post(self.constructed_url, params=params, headers=self.headers, json=body)

            if response.status_code != 200:
                if 'too many elements' in response.text:
                    return {}
                raise ValueError(response.text)

            api_translations = {}
            for i, text in enumerate(untranslated_texts):
                target_text = response.json()[i]['translations'][0]['text']
                api_translations[untranslated_indices[i]] = target_text
                try:
                    self.TM.save_translation(source_text=text, source_lang=from_lang, target_text=target_text,
                                             target_lang=to_lang)
                except Exception as e:
                    print("=> Failed to save translation: %s", e)

            text_list.update(api_translations)

        return list(text_list.values())

    def translate_product(self, product, to_lang: str, from_lang='tr'):
        # print(product)

        # translate name
        translated_name = self.translate(text=product['name'], from_lang=from_lang, to_lang=to_lang)

        # translate description
        soup = BeautifulSoup(product['description'], 'html.parser')

        # Find all the HTML tags with text content
        tags = [tag for tag in soup.descendants if isinstance(tag, NavigableString) and tag.strip() and tag.parent.name not in ['script', 'style']]

        # Translate the text content
        translated_list = self.translate_list([tag.string for tag in tags], from_lang=from_lang, to_lang=to_lang)

        # Replace the original text with the translated text
        for tag, translated_text in zip(tags, translated_list):
            tag.replace_with(translated_text)

        translated_description = str(soup).replace('\n', '')

        # print('=>', translated_description)

        product['translation'] = {
            'name': translated_name,
            'description': translated_description
        }

        return product


if __name__ == '__main__':
    # Example usage:
    key = "d74339cf185c4d42896344bcbfbc61d6"
    location = "germanywestcentral"
    translator = BingTranslator(key, location)

    product = {
        'name': 'Kadın Siyah Kısa Kollu T-Shirt',
        'description': """<div class="panel-body" style="display: block;">
                                        <table class="table">
                                            <tbody id="producttables" class="desctab">
                                                <tr><th>Kumaş Rengi:</th><td>KİREMİT</td></tr>
<tr><th>Takım İçeriği</th><td>Sağ köşe orta modül sol köşe ve puf modülünden oluşmaktadır.</td></tr>
<tr><th>Kumaş İçeriği</th><td>Keten kumaş kullanılmıştır.</td></tr>
<tr><th>Kumaş Özelliği</th><td>Silinebilir kumaştır.</td></tr>
<tr><th>Fonksiyon</th><td>Modüler</td></tr>
<tr><th>İskelet Malzemesi</th><td>Kavak kontrplak ve keresteden üretilmiştir.</td></tr>
<tr><th>Oturum Yumuşaklığı</th><td>Yumuşak</td></tr>
<tr><th>Oturum Minderi Malzemesi</th><td>32 DNS reflex ve kuş tüyü malzeme kullanılmıştır.</td></tr>
<tr><th>Sırt Minderi Malzemesi</th><td>Minderi yoktur.</td></tr>
<tr><th>Ayak Malzemesi</th><td>Plastik</td></tr>
<tr><th>Kumaş Bakım/Temizlik Önerisi</th><td>Nemli bezle silinebilir.</td></tr>
<tr><th>Demonte Parçalar</th><td>Tüm parçalar demonte gönderilir.</td></tr>
<tr><th>Kumaş değiştirilebilir</th><td>Kumaş Değişimsiz</td></tr>
<tr><th>Köşe Yönü</th><td>Modül</td></tr>
<tr><th>Ayak Rengi</th><td>KİREMİT</td></tr>
<tr><th>Renk</th><td>Kiremit</td></tr>
<tr><th>Kumaş Materyali</th><td>Keten</td></tr>
<tr><th>Form</th><td>Modüler Köşe</td></tr>
<tr><th>Ek Bilgiler</th><td>6 adet kırlent hediyemizdir. Renkli kırlentler fiyata dahil değildir. Ürünün renginde 4 adet 2 adette farklı renkte kırlent gönderimi sağlanmaktadır. Kırlentlerde renk seçimi yoktur.Ürün altında bulunan kilit mekanizması ile modülleri birbirine kolaylıkla sabitleyebilirsiniz ve modüllerin yerlerini değiştirerek istediğiniz şekilde kombinleyebilirsiniz. İsterseniz 3+1 olarak kullanabilirsiniz İsterseniz köşe olarak kullanabilirsiniz İsterseniz 2 adet Dinlenme olarak kullanabilirsiniz Evinizdeki mekana göre oturumunuzu kendiniz ayarlabilme özelliğine sahipsiniz. Ölçüler Dıştan dışa Genişlik: 296cm Derinlik: 107cm Sırt yüksekliği: 68cm Oturum yüksekliği: 43cm İç Oturum Genişliği: 246cm İç Oturum Derinliği: 82cm</td></tr>
                                            </tbody>
                                        </table>
                                    </div><br>
                <div class="panel panel-default custom-panel" id="part87">
                    <div class="panel-heading pd-productsize open">Ürün Boyutları</div>
                    <div class="panel-body nopadding" style="display: block;">
                        <table class="table product-feature">
                            <thead><tr><th class="main-header">&nbsp;</th><th>Genişlik</th><th>Derinlik</th><th>Yükseklik</th></tr></thead>
                            <tbody>
                                <tr><th>Köşe Koltuk</th><td>300.0 cm</td><td>68.0 cm</td><td>107.0 cm</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                

"""
    }
    # translated_product = translator.translate_product(product, from_lang='tr', to_lang='ar')
    # print(translated_product['translation'])


    source_list = ['Kaymaz suni tabanlıdır.']
    response = translator.translate_list(source_list, from_lang='tr', to_lang='ar')
    print('=>', source_list)
    print('=>', response)
    for source, trans in zip(source_list, response):
        print(source, ':', trans)

