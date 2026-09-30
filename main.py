from fastapi import FastAPI
from contextlib import asynccontextmanager
from .src.database import create_db_and_tables
from .src.redis import redis_client
from .src.worker.celery import celery_app
from .src.routers import tasks
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield  
    await redis_client.close()

app = FastAPI(title="Task Management API", lifespan=lifespan)

app.include_router(tasks.router)


@app.get("/redis-heath")
async def root():
    print("Root endpoint hit")
    redis_status = await redis_client.ping()
    return {"status": "ok", "redis": redis_status}

@app.get("/celery-heath")
def check_celery_status():
    inspect = celery_app.control.inspect()
    workers = inspect.ping()
    
    if workers:
        return {"message":"Celery Workers Active:"}
    else :
        return {"message":"No active Celery workers found!"}
