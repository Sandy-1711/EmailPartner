from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient

from app.config.settings import settings
from app.infrastructure.db.indexes import ensure_indexes
from app.infrastructure.db.main import DBManager
from app.infrastructure.db.mongo import MongoDBManager
from app.routers.v1 import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo = MongoDBManager(settings.mongo_uri.get_secret_value(), settings.mongo_db_name)
    await mongo.connect()
    app.state.db_manager = DBManager(mongo)
    app.state.http_client = AsyncClient(timeout=settings.http_timeout_seconds)
    await ensure_indexes(mongo)
    try:
        yield
    finally:
        db_manager: DBManager | None = getattr(app.state, "db_manager", None)
        if db_manager is not None:
            await db_manager.document_db.disconnect()
        http_client: AsyncClient | None = getattr(app.state, "http_client", None)
        if http_client is not None:
            await http_client.aclose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health():
    return {"status": "healthy"}