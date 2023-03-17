from fastapi import FastAPI, Request
from fastapi.responses import Response, StreamingResponse
from dotenv import load_dotenv
from core.tasks import scraping_task
from core.db import migrate_all_collections
from core.scraper import ScraperFactory
from core.models import Vendor
from jinja2 import Template, Environment, FileSystemLoader
import os, io


# load environment variables
load_dotenv()
config = os.environ

# Create a Jinja2 Environment object
env = Environment(loader=FileSystemLoader('templates'))

# Migrate db collections
migrate_all_collections()

app = FastAPI()


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
    products = vendor.get_products(offset, limit)
    # Render a template
    template = env.get_template(f'{vendor_name}.xml')
    rendered_xml = template.render(products=products, stock=stock)
    # convert the rendered XML to bytes
    xml_bytes = rendered_xml.encode('utf-8')
    # create a byte stream in memory
    file_like_object = io.BytesIO(xml_bytes)
    # set the response headers to indicate a file download
    response = Response(content=file_like_object.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=products.xml"
    response.headers["Content-Type"] = "application/xml; charset=utf-8"
    return response


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='localhost', port=5000)
