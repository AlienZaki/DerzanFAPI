from fastapi import FastAPI
from dotenv import load_dotenv
from core.tasks import add
from core.db import db
import os


load_dotenv()
config = os.environ

app = FastAPI()



@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get('/add/{x}/{y}')
async def add_numbers(x: int, y: int):
    result = add.delay(x, y)
    return {'task_id': result.id}


@app.get('/data/{id}')
async def get_data(id: str):
    result = db['products'].find()
    return result



if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='localhost', port=8000)
