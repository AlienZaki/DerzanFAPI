from fastapi import FastAPI, Request
from fastapi.responses import Response, StreamingResponse
from dotenv import load_dotenv
from core.tasks import vivense_scraper_task
from core.db import db, products_collection
from core.scraper.vivense import VivenseScraper
from jinja2 import Template
import os, io


# load environment variables
load_dotenv()
config = os.environ

app = FastAPI()


@app.get("/")
async def root(request: Request):
    return {"message": "Hello World", 'data': request.headers["host"]}


@app.get('/scrape')
async def scrape(request: Request, workers: int = 1, flush: bool = 0, proxy=0):
    host = request.headers["host"]
    result = vivense_scraper_task.delay(host=host, workers=workers, flush=flush, proxy=proxy)
    return {'task_id': result.id}


@app.get('/export')
async def export(offset: int = 0, limit: int = 100, stock=1):
    # fetch the products using pagination
    products = VivenseScraper().vendor.get_products(offset, limit)
    template = Template(open('products.xml').read())
    rendered_xml = template.render(products=products, stock=stock)
    # convert the rendered XML to bytes
    xml_bytes = rendered_xml.encode('utf-8')
    # create a byte stream in memory
    file_like_object = io.BytesIO(xml_bytes)
    # set the response headers to indicate a file download
    response = Response(content=file_like_object.getvalue())
    # response.headers["Content-Disposition"] = "attachment; filename=products.xml"
    # response.headers["Content-Type"] = "application/octet-stream"
    return response

@app.get('/export2')
async def export2(offset: int = 0, limit: int = 100, stock=1):
    # fetch the products using pagination
    products = VivenseScraper().vendor.get_products(offset, limit)
    # create a response object with a streaming content
    response = StreamingResponse(generate_xml(products, stock), media_type='application/octet-stream')
    response.headers["Content-Disposition"] = "attachment; filename=products.xml"
    return response

async def generate_xml(products, stock):
    # create a template object
    template = Template(open('products.xml').read())
    # send the XML header
    yield b'<?xml version="1.0" encoding="UTF-8"?>\n'
    # loop through the products and render the XML
    async for product in products:
        rendered_xml = template.render(product=product, stock=stock)
        # convert the rendered XML to bytes
        xml_bytes = rendered_xml.encode('utf-8')
        # send the bytes to the response stream
        yield xml_bytes






if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='localhost', port=5000)
