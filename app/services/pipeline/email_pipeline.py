from __future__ import annotations

import logging
from typing import Literal

from bson import ObjectId
from pydantic import BaseModel

from app.config.settings import Settings
from app.infrastructure.db.main import DBManager
from app.infrastructure.images.providers.base import ImageProvider
from app.infrastructure.llm.providers.base import LLMProvider
from app.infrastructure.storage.base import BlobStorage
from app.models.db.emails import EmailProcessingStatus, Emails
from app.services.pipeline.prompts import (
    EMAIL_SUMMARY_SYSTEM,
    build_illustration_prompt,
    build_summary_prompt,
)
from app.services.storage import EmailStore

logger = logging.getLogger(__name__)


class SummaryResult(BaseModel):
    headline: str
    summary: str
    tone: Literal[
        "informative", "urgent", "social", "promotional", "transactional"
    ]
    image_caption: str
    visual_concept: str


class EmailPipeline:
    def __init__(
        self,
        db_manager: DBManager,
        settings: Settings,
        storage: BlobStorage,
        llm: LLMProvider,
        image: ImageProvider,
    ) -> None:
        self._email_store = EmailStore(db_manager)
        self._settings = settings
        self._storage = storage
        self._llm = llm
        self._image = image

    async def process(self, email: Emails) -> None:
        """Turn one claimed email into a finished card (status PROCESSING -> READY/FAILED)."""
        email_id = email.id
        try:
            result = await self._llm.generate_structured_output(
                prompt=build_summary_prompt(email, self._settings.summary_max_body_chars),
                system_instructions=EMAIL_SUMMARY_SYSTEM,
                model=self._settings.summary_model,
                response_model=SummaryResult,
            )
        except Exception as exc:
            logger.exception("EmailPipeline: summary generation failed for %s", email_id)
            await self._email_store.update_card_fields(
                email_id,
                processing_status=EmailProcessingStatus.FAILED,
                last_error=f"summary: {exc}",
            )
            return

        card_text = f"{result.headline}\n\n{result.summary}"
        card_background_url = await self._try_generate_illustration(
            email_id, str(email.user_id), result
        )

        await self._email_store.update_card_fields(
            email_id,
            processing_status=EmailProcessingStatus.READY,
            card_text=card_text,
            card_background_url=card_background_url,
        )
        logger.info("EmailPipeline: ready %s", email_id)

    async def _try_generate_illustration(
        self,
        email_oid: ObjectId,
        user_id: str,
        summary: SummaryResult,
    ) -> str | None:
        try:
            image = await self._image.generate(
                prompt=build_illustration_prompt(
                    image_caption=summary.image_caption,
                    visual_concept=summary.visual_concept,
                    tone=summary.tone,
                ),
                model=self._settings.image_model,
                size=(1920, 1080),
            )
        except Exception:
            logger.exception(
                "EmailPipeline: illustration generation failed for %s", email_oid
            )
            return None

        extension = "jpg" if "jpeg" in image.mime_type or "jpg" in image.mime_type else "png"
        key = f"users/{user_id}/emails/{email_oid}.{extension}"

        try:
            return await self._storage.put(key, image.data, image.mime_type)
        except Exception:
            logger.exception(
                "EmailPipeline: illustration upload failed for %s", email_oid
            )
            return None

