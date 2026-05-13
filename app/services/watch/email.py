from __future__ import annotations

from bson import ObjectId

from app.config.settings import Settings
from app.infrastructure.db.main import DBManager
from app.infrastructure.images.main import build_image_provider
from app.infrastructure.llm.main import build_llm_provider
from app.infrastructure.storage.local import LocalBlobStorage
from app.services.pipeline.email_pipeline import EmailPipeline


class EmailWatchService:
    def __init__(self, db_manager: DBManager, settings: Settings) -> None:
        storage = LocalBlobStorage(
            settings.local_storage_dir,
            settings.local_storage_public_base_url,
        )
        llm = build_llm_provider(
            provider="gemini", api_key=settings.gemini_api_key.get_secret_value()
        )
        image = build_image_provider(
            provider=settings.image_provider,
            api_key=settings.gemini_api_key.get_secret_value(),
        )
        self._pipeline = EmailPipeline(db_manager, settings, storage, llm, image)

    async def watch_email(self, email_id: ObjectId) -> None:
        await self._pipeline.run(email_id)
