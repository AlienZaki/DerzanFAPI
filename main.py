from bson import ObjectId, json_util
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, StreamingResponse
from dotenv import load_dotenv
from pymongo import ReturnDocument

from core.tasks import scraping_task
from core.db import migrate_all_collections, db
from core.scraper import ScraperFactory
from core.models import Vendor
from jinja2 import Template, Environment, FileSystemLoader
import os, io, json
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


# load environment variables
load_dotenv()
config = os.environ

# Create a Jinja2 Environment object
env = Environment(loader=FileSystemLoader('templates'))

# Migrate db collections
migrate_all_collections()

app = FastAPI()

app.mount("/web/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# CORS Configuration
origins = [
    "*",  # Change this to the domain of your frontend application
    # "https://example-frontend.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root(request: Request):
    return {"message": "Hello World", 'data': request.headers["host"]}


@app.get('/{vendor_name}/scrape')
async def scrape(request: Request, vendor_name: str, workers: int = 1, flush: bool = 0, proxy=0):
    host = request.headers["host"]
    try:
        ScraperFactory.get_vendor_scraper_by_name(vendor_name)
        result = scraping_task.delay(vendor_name, host=host, workers=workers, flush=flush, proxy=proxy)
        return {'vendor': vendor_name, 'task_id': result.id}
    except ValueError as e:
        return {'error': str(e)}


@app.get('/{vendor_name}/export')
async def export(vendor_name: str, offset: int = 0, limit: int = 100, stock=1):
    # fetch the products
    vendor = Vendor.find_by_name(vendor_name.lower())
    if not vendor:
        return {'error': f"Unsupported vendor: '{vendor_name}'"}
    # Get products
    products = vendor.get_products(offset, limit)
    # Render a template
    template = env.get_template(f'{vendor_name}.xml')
    rendered_xml = template.render(products=products, stock=stock)
    # convert the rendered XML to_lang bytes
    xml_bytes = rendered_xml.encode('utf-8')
    # create a byte stream in memory
    file_like_object = io.BytesIO(xml_bytes)
    # set the response headers to_lang indicate a file download
    response = Response(content=file_like_object.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=products.xml"
    response.headers["Content-Type"] = "application/xml; charset=utf-8"
    return response

@app.get('/{vendor_name}/translated/export')
async def export_translated(vendor_name: str, lang: str, offset: int = 0, limit: int = 100):
    # fetch the products
    vendor = Vendor.find_by_name(vendor_name.lower())
    if not vendor:
        return {'error': f"Unsupported vendor: '{vendor_name}'"}
    # Get translated products
    translated_products = vendor.get_translated_products(lang, offset, limit)
    # Render a template
    template = env.get_template(f'{vendor_name}_translated.xml')
    rendered_xml = template.render(products=translated_products, lang=lang)
    # convert the rendered XML to_lang bytes
    xml_bytes = rendered_xml.encode('utf-8')
    # create a byte stream in memory
    file_like_object = io.BytesIO(xml_bytes)
    # set the response headers to_lang indicate a file download
    response = Response(content=file_like_object.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=products_{vendor_name}_{lang}_{offset}_{offset+limit}.xml"
    response.headers["Content-Type"] = "application/xml; charset=utf-8"
    return response


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError('Invalid objectId')
        return str(v)
class Translation(BaseModel):
    id: Optional[PyObjectId] = Field(alias='_id')
    source_text: str
    source_lang: str
    target_text: str
    target_lang: str
    last_update: Optional[datetime]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str
        }



collection = db["translation_memory"]


class TranslationItem(BaseModel):
    id: Optional[str]
    source_text: str = Field(...)
    source_lang: str = Field(...)
    target_text: str = Field(...)
    target_lang: str = Field(...)
    last_update: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str
        }

class TranslationUpdateItem(BaseModel):
    source_text: Optional[str] = Field(None)
    target_text: Optional[str] = Field(None)


@app.put('/translations/{translation_id}', response_model=TranslationItem)
async def update_translation(translation_id: str, translation_item: TranslationUpdateItem):
    translation_dict = translation_item.dict()
    translation_dict["last_update"] = datetime.utcnow()
    translation_res = collection.update_one(
        {"_id": ObjectId(translation_id)},
        {"$set": translation_dict}
    )
    if translation_res.modified_count == 0:
        raise HTTPException(status_code=404, detail="Translation not found")

    updated_translation = collection.find_one({"_id": ObjectId(translation_id)})
    updated_translation["id"] = str(updated_translation["_id"])
    return updated_translation


class Pagination(BaseModel):
    total: int
    items: List[TranslationItem]
    page: int
    per_page: int


@app.get('/translations/', response_model=Pagination)
async def get_translations(page: int = 0, per_page: int = 10,
                           source_text: Optional[str] = None,
                           source_lang: Optional[str] = None,
                           target_text: Optional[str] = None,
                           target_lang: Optional[str] = None):
    skip = page * per_page
    translation_query = {}
    if source_text:
        translation_query['source_text'] = {'$regex': source_text}
    if source_lang:
        translation_query['source_lang'] = source_lang
    if target_text:
        translation_query['target_text'] = {'$regex': target_text}
    if target_lang:
        translation_query['target_lang'] = target_lang

    translations = list(collection.find(translation_query).skip(skip).limit(per_page))
    for translation in translations:
        translation['id'] = str(translation['_id'])

    total = collection.count_documents(translation_query)
    response = Pagination(total=total, items=translations, page=page, per_page=per_page)
    return response

@app.get("/tm", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='localhost', port=5000)
