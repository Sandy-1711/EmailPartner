from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.db.emails import EmailProcessingStatus


class EmailCard(BaseModel):
    id: str
    gmail_message_id: str
    subject: str | None
    from_email: str | None
    snippet: str | None
    received_at: datetime | None
    processing_status: EmailProcessingStatus
    background_image_url: str | None
    text: str | None
    audio_url: str | None


class CardListResponse(BaseModel):
    items: list[EmailCard]
    limit: int
    offset: int
    next_offset: int | None
