from __future__ import annotations

from datetime import datetime
from enum import Enum

from bson import ObjectId
from pydantic import EmailStr, Field
from pydantic_mongo import PydanticObjectId

from app.config import ConfigModels
from app.models.db.crypto import EncryptedBlob
from app.models.db.utils import utc_now


class GmailAccountStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class GmailAccount(ConfigModels.EmailPartnerDBConfig):
    __collection__ = "gmail_accounts"

    id: PydanticObjectId = Field(default_factory=ObjectId, alias="_id")
    user_id: PydanticObjectId
    gmail_address: EmailStr
    refresh_token: EncryptedBlob
    access_token: EncryptedBlob | None = None
    access_token_expires_at: datetime | None = None
    history_id: str | None = None
    watch_expiration: datetime | None = None
    status: GmailAccountStatus = GmailAccountStatus.ACTIVE
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
