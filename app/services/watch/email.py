from __future__ import annotations

from bson import ObjectId

from app.config.settings import Settings
from app.infrastructure.db.main import DBManager
from app.services.pipeline.email_pipeline import EmailPipeline


class EmailWatchService:
    def __init__(self, db_manager: DBManager, settings: Settings) -> None:
        self._pipeline = EmailPipeline(db_manager, settings)

    async def watch_email(self, email_id: str | ObjectId) -> None:
        await self._pipeline.run(email_id)
