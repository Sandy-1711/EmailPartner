from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PubSubMessage(BaseModel):
    data: str
    message_id: str = Field(alias="messageId")
    publish_time: datetime | None = Field(default=None, alias="publishTime")
    attributes: dict[str, str] | None = None


class PubSubPushBody(BaseModel):
    message: PubSubMessage
    subscription: str


class GmailNotification(BaseModel):
    email_address: str = Field(alias="emailAddress")
    history_id: str = Field(alias="historyId")
