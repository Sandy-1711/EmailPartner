from __future__ import annotations

import logging
from typing import Literal

from bson import ObjectId
from pydantic import BaseModel

from app.config.settings import Settings
from app.infrastructure.db.main import DBManager
from app.infrastructure.llm.main import LLMManager
from app.models.db.emails import EmailProcessingStatus
from app.services.pipeline.prompts import EMAIL_SUMMARY_SYSTEM, build_summary_prompt
from app.services.storage import EmailStore

logger = logging.getLogger(__name__)


class SummaryResult(BaseModel):
    headline: str
    summary: str
    tone: Literal[
        "informative", "urgent", "social", "promotional", "transactional"
    ]


class EmailPipeline:
    def __init__(self, db_manager: DBManager, settings: Settings) -> None:
        self._email_store = EmailStore(db_manager)
        self._settings = settings

    async def run(self, email_id: str | ObjectId) -> None:
        oid = email_id if isinstance(email_id, ObjectId) else ObjectId(email_id)

        email = await self._email_store.get_by_id(oid)
        if email is None:
            logger.warning("EmailPipeline: email %s not found", oid)
            return

        await self._email_store.update_card_fields(
            oid, processing_status=EmailProcessingStatus.PROCESSING
        )

        try:
            result = await LLMManager.generate_structured_output(
                prompt=build_summary_prompt(email, self._settings.summary_max_body_chars),
                system_instructions=EMAIL_SUMMARY_SYSTEM,
                model=self._settings.summary_model,
                response_model=SummaryResult,
                provider="gemini",
            )
        except Exception:
            logger.exception("EmailPipeline: summary generation failed for %s", oid)
            await self._email_store.update_card_fields(
                oid, processing_status=EmailProcessingStatus.FAILED
            )
            return

        card_text = f"{result.headline}\n\n{result.summary}"
        await self._email_store.update_card_fields(
            oid,
            processing_status=EmailProcessingStatus.READY,
            card_text=card_text,
        )
        logger.info("EmailPipeline: ready %s", oid)
