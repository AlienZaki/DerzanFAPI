from core.db import db


class TM:

    def __init__(self):
        self.collection = db['translation_memory']

    def get_translation(self, source_text, source_lang, target_lang):
        document = self.collection.find_one({'source_text': source_text, 'source_lang': source_lang, 'target_lang': target_lang})
        return document['target_text'] if document else None

    def save_translation(self, source_text, source_lang, target_text, target_lang):
        if source_text and target_text:
            document = {
                'source_text': source_text,
                'source_lang': source_lang,
                'target_text': target_text,
                'target_lang': target_lang
            }
            result = self.collection.insert_one(document)



if __name__ == '__main__':
    tm = TM()
    # print(tm.save_translation('zaki', 'en', 'زكى', 'ar'))
    # print(tm.get_translation('zaki', 'en', 'ar'))
    db['translation_memory'].update_many({}, {"$set": {"target_lang": "ar"}})

