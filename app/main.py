from contextlib import asynccontextmanager

from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI

from app.api import router
from app.config import get_settings
from app.db import engine
from app.elastic import ensure_index


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    elastic = AsyncElasticsearch(settings.elasticsearch_url)
    try:
        await ensure_index(elastic, settings.elasticsearch_index)
        app.state.elastic = elastic
        app.state.elasticsearch_index = settings.elasticsearch_index
        yield
    finally:
        await elastic.close()
        await engine.dispose()


app = FastAPI(title="Document Search", version="1.0.0", lifespan=lifespan)
app.include_router(router)
