import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from httpx import AsyncClient

from app.config.settings import settings
from app.infrastructure.db.indexes import ensure_indexes
from app.infrastructure.db.main import DBManager
from app.infrastructure.db.mongo import MongoDBManager
from app.infrastructure.images.main import build_image_provider
from app.infrastructure.llm.main import build_llm_provider
from app.infrastructure.security.crypto import CryptoManager
from app.infrastructure.security.session import SessionManager
from app.infrastructure.security.state import OAuthStateManager
from app.infrastructure.storage.local import LocalBlobStorage
from app.routers.v1 import router as v1_router
from app.services.pipeline.email_pipeline import EmailPipeline
from app.services.queue.worker import PipelineWorker
from app.services.watch.renewal import WatchRenewalService

logger = logging.getLogger(__name__)


async def _watch_renewal_loop(
    db_manager: DBManager,
    http_client: AsyncClient,
    crypto: CryptoManager,
) -> None:
    service = WatchRenewalService(db_manager, http_client, crypto, settings)
    threshold = timedelta(hours=settings.watch_renew_threshold_hours)
    while True:
        try:
            renewed = await service.renew_expiring(threshold=threshold)
            if renewed:
                logger.info("watch renewal loop: renewed %d watches", renewed)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("watch renewal loop iteration failed")
        try:
            await asyncio.sleep(settings.watch_renew_interval_seconds)
        except asyncio.CancelledError:
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    mongo = MongoDBManager(settings.mongo_uri.get_secret_value(), settings.mongo_db_name)
    await mongo.connect()
    await ensure_indexes(mongo)

    api_key = settings.gemini_api_key.get_secret_value()
    app.state.settings = settings
    app.state.db_manager = DBManager(mongo)
    app.state.http_client = AsyncClient(timeout=settings.http_timeout_seconds)
    app.state.crypto = CryptoManager.from_secret(
        settings.encryption_master_key.get_secret_value(), settings.encryption_key_id
    )
    app.state.state_manager = OAuthStateManager(
        secret=settings.oauth_state_secret.get_secret_value().encode("utf-8"),
        ttl_seconds=settings.oauth_state_ttl_seconds,
    )
    app.state.session_manager = SessionManager(
        secret=settings.session_secret.get_secret_value().encode("utf-8"),
        ttl_seconds=settings.session_ttl_seconds,
    )
    app.state.llm_provider = build_llm_provider(provider="gemini", api_key=api_key)
    app.state.image_provider = build_image_provider(
        provider=settings.image_provider, api_key=api_key
    )
    app.state.storage = LocalBlobStorage(
        settings.local_storage_dir, settings.local_storage_public_base_url
    )

    pipeline = EmailPipeline(
        app.state.db_manager,
        settings,
        app.state.storage,
        app.state.llm_provider,
        app.state.image_provider,
    )
    app.state.pipeline_worker = PipelineWorker(
        app.state.db_manager,
        pipeline,
        concurrency=settings.pipeline_concurrency,
        poll_interval_seconds=settings.pipeline_poll_interval_seconds,
        lease_seconds=settings.pipeline_lease_seconds,
        max_attempts=settings.pipeline_max_attempts,
    )

    renewal_task: asyncio.Task[None] | None = None
    worker_started = False
    if settings.enable_background_jobs:
        await app.state.pipeline_worker.start()
        worker_started = True
        renewal_task = asyncio.create_task(
            _watch_renewal_loop(
                app.state.db_manager, app.state.http_client, app.state.crypto
            )
        )

    try:
        yield
    finally:
        if worker_started:
            await app.state.pipeline_worker.stop()
        if renewal_task is not None:
            renewal_task.cancel()
            try:
                await renewal_task
            except (asyncio.CancelledError, Exception):
                pass
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

_illustrations_dir = Path(settings.local_storage_dir)
_illustrations_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    "/static/illustrations",
    StaticFiles(directory=_illustrations_dir),
    name="illustrations",
)

app.include_router(v1_router)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
