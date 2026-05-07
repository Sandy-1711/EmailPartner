from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field
from bson import ObjectId

from app.config import ConfigModels
from pydantic_mongo import PydanticObjectId
from app.models.db.utils import utc_now


class EmailProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Emails(ConfigModels.EmailPartnerDBConfig):
    __collection__ = "emails"

    id: PydanticObjectId = Field(default_factory=ObjectId, alias="_id")
    user_id: PydanticObjectId
    gmail_account_id: PydanticObjectId
    gmail_message_id: str
    thread_id: str | None = None
    subject: str | None = None
    from_email: str | None = None
    snippet: str | None = None
    body: str | None = None
    received_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    processing_status: EmailProcessingStatus = EmailProcessingStatus.PENDING
    card_background_url: str | None = None
    card_text: str | None = None
    card_audio_url: str | None = None
