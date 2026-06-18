from __future__ import annotations

from datetime import datetime
from enum import Enum

from bson import ObjectId
from pydantic import EmailStr, Field
from pydantic_mongo import PydanticObjectId

from app.config import ConfigModels
from app.models.db.utils import utc_now


class UserStatus(str, Enum):
    ACTIVE = "active"
    DELETED = "deleted"


class Users(ConfigModels.EmailPartnerDBConfig):
    __collection__ = "users"

    id: PydanticObjectId = Field(default_factory=ObjectId, alias="_id")
    email: EmailStr
    display_name: str | None = None
    google_sub: str | None = None
    picture_url: str | None = None
    status: UserStatus = UserStatus.ACTIVE
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    