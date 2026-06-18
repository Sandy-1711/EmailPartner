from __future__ import annotations

from datetime import datetime

from pydantic import Field
from bson import ObjectId

from app.config import ConfigModels
from pydantic_mongo import PydanticObjectId
from app.models.db.utils import utc_now


class DeviceTokens(ConfigModels.EmailPartnerDBConfig):
    """An FCM registration token for one of a user's devices.

    The worker sends a push to every token a user has when a card turns ready.
    Tokens rotate, so the same physical device may register a new token over
    time; invalid ones are pruned when FCM reports them unregistered.
    """

    __collection__ = "device_tokens"

    id: PydanticObjectId = Field(default_factory=ObjectId, alias="_id")
    user_id: PydanticObjectId
    token: str
    platform: str = "android"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
