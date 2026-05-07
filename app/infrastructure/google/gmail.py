from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import BaseModel, Field


class GmailProfile(BaseModel):
    email_address: str = Field(alias="emailAddress")
    history_id: str = Field(alias="historyId")


class GmailWatchResponse(BaseModel):
    history_id: str = Field(alias="historyId")
    expiration: str | None = None

    def expiration_datetime(self) -> datetime | None:
        if not self.expiration:
            return None
        return datetime.fromtimestamp(int(self.expiration) / 1000, tz=timezone.utc)


class GmailMessageHeader(BaseModel):
    name: str
    value: str


class GmailMessagePayload(BaseModel):
    headers: list[GmailMessageHeader] = Field(default_factory=list)


class GmailMessage(BaseModel):
    id: str
    thread_id: str = Field(alias="threadId")
    snippet: str | None = None
    payload: GmailMessagePayload | None = None


class GmailHistoryMessageAdded(BaseModel):
    message: GmailMessage


class GmailHistoryItem(BaseModel):
    messages_added: list[GmailHistoryMessageAdded] = Field(default_factory=list, alias="messagesAdded")


class GmailHistoryResponse(BaseModel):
    history_id: str | None = Field(default=None, alias="historyId")
    history: list[GmailHistoryItem] = Field(default_factory=list)


@dataclass(frozen=True)
class GmailApiClient:
    http_client: httpx.AsyncClient
    base_url: str
    access_token: str

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def get_profile(self) -> GmailProfile:
        response = await self.http_client.get(
            f"{self.base_url}/users/me/profile", headers=self._headers()
        )
        response.raise_for_status()
        return GmailProfile.model_validate(response.json())

    async def watch(
        self, topic_name: str, label_ids: list[str], history_types: list[str]
    ) -> GmailWatchResponse:
        payload: dict[str, Any] = {"topicName": topic_name}
        if label_ids:
            payload["labelIds"] = label_ids
        if history_types:
            payload["historyTypes"] = history_types
        response = await self.http_client.post(
            f"{self.base_url}/users/me/watch",
            headers=self._headers(),
            json=payload,
        )
        response.raise_for_status()
        return GmailWatchResponse.model_validate(response.json())

    async def list_history(
        self, start_history_id: str, history_types: list[str] | None = None
    ) -> GmailHistoryResponse:
        params: dict[str, Any] = {"startHistoryId": start_history_id}
        if history_types:
            params["historyTypes"] = history_types
        response = await self.http_client.get(
            f"{self.base_url}/users/me/history", headers=self._headers(), params=params
        )
        response.raise_for_status()
        return GmailHistoryResponse.model_validate(response.json())

    async def get_message(self, message_id: str) -> GmailMessage:
        params = {
            "format": "metadata",
            "metadataHeaders": ["Subject", "From", "Date"],
        }
        response = await self.http_client.get(
            f"{self.base_url}/users/me/messages/{message_id}",
            headers=self._headers(),
            params=params,
        )
        response.raise_for_status()
        return GmailMessage.model_validate(response.json())
