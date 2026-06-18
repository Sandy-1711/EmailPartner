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
from app.services.memory import EmailMemory
from app.services.notifications.push import CardNotifier, display_name
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
    narration: str


class EmailPipeline:
    def __init__(
        self,
        db_manager: DBManager,
        settings: Settings,
        storage: BlobStorage,
        llm: LLMProvider,
        image: ImageProvider,
        *,
        notifier: CardNotifier | None = None,
        memory: EmailMemory | None = None,
    ) -> None:
        self._email_store = EmailStore(db_manager)
        self._settings = settings
        self._storage = storage
        self._llm = llm
        self._image = image
        self._notifier = notifier
        self._memory = memory

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
        card_audio_url = await self._try_generate_narration(
            email_id, str(email.user_id), result
        )

        await self._email_store.update_card_fields(
            email_id,
            processing_status=EmailProcessingStatus.READY,
            card_text=card_text,
            card_phrase=result.image_caption,
            card_tone=result.tone,
            card_background_url=card_background_url,
            card_audio_url=card_audio_url,
        )
        logger.info("EmailPipeline: ready %s", email_id)
        await self._index_for_memory(email, result)
        await self._push_ready(email, result, card_audio_url)

    async def _index_for_memory(self, email: Emails, result: SummaryResult) -> None:
        """Best-effort embed + upsert into semantic memory. A vector-store hiccup
        must never fail the already-finished card."""
        if self._memory is None:
            return
        try:
            await self._memory.index(email, tone=result.tone)
        except Exception:
            logger.exception("EmailPipeline: memory index failed for %s", email.id)

    async def _push_ready(
        self, email: Emails, result: SummaryResult, card_audio_url: str | None
    ) -> None:
        """Best-effort FCM push so the card surfaces while the app is closed.
        Never let a push failure fail the (already-finished) card."""
        if self._notifier is None:
            return
        try:
            await self._notifier.notify_card_ready(
                user_id=email.user_id,
                card_id=str(email.id),
                phrase=result.image_caption,
                sender=display_name(email.from_email),
                tone=result.tone,
                audio_url=card_audio_url,
            )
        except Exception:
            logger.exception("EmailPipeline: push notification failed for %s", email.id)

    async def _try_generate_illustration(
        self,
        email_oid: ObjectId,
        user_id: str,
        summary: SummaryResult,
    ) -> str | None:
        # The mobile app renders a procedural MeshGradient, not this illustration,
        # so generation is off by default — flip enable_image_generation to revive
        # it (the code path is kept intact).
        if not self._settings.enable_image_generation:
            return None
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

    async def _try_generate_narration(
        self,
        email_oid: ObjectId,
        user_id: str,
        summary: SummaryResult,
    ) -> str | None:
        if not self._settings.enable_audio_narration:
            return None
        script = summary.narration.strip() or f"{summary.headline}. {summary.summary}"
        try:
            audio = await self._llm.synthesize_speech(
                text=script,
                model=self._settings.tts_model,
                voice=self._settings.tts_voice,
            )
        except Exception:
            logger.exception(
                "EmailPipeline: narration generation failed for %s", email_oid
            )
            return None

        key = f"users/{user_id}/emails/{email_oid}.wav"
        try:
            return await self._storage.put(key, audio, "audio/wav")
        except Exception:
            logger.exception("EmailPipeline: narration upload failed for %s", email_oid)
            return None

