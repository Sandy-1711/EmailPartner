from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)


_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_STATUSES
    return isinstance(exc, httpx.TransportError)


_retry_policy = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception(_is_retryable),
)


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


class GmailMessageBody(BaseModel):
    data: str | None = None
    size: int | None = None


class GmailMessagePayload(BaseModel):
    mime_type: str | None = Field(default=None, alias="mimeType")
    headers: list[GmailMessageHeader] = Field(default_factory=list[GmailMessageHeader])
    body: GmailMessageBody | None = None
    parts: list["GmailMessagePayload"] = Field(default_factory=list["GmailMessagePayload"])


class GmailMessage(BaseModel):
    id: str
    thread_id: str = Field(alias="threadId")
    snippet: str | None = None
    payload: GmailMessagePayload | None = None


GmailMessagePayload.model_rebuild()


class GmailHistoryMessageAdded(BaseModel):
    message: GmailMessage


class GmailHistoryItem(BaseModel):
    messages_added: list[GmailHistoryMessageAdded] = Field(default_factory=list[GmailHistoryMessageAdded], alias="messagesAdded")


class GmailHistoryResponse(BaseModel):
    history_id: str | None = Field(default=None, alias="historyId")
    history: list[GmailHistoryItem] = Field(default_factory=list[GmailHistoryItem])


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

    @_retry_policy
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

    @_retry_policy
    async def get_message(
        self,
        message_id: str,
        format: Literal["metadata", "full"] = "metadata",
    ) -> GmailMessage:
        params: dict[str, Any] = {"format": format}
        if format == "metadata":
            params["metadataHeaders"] = ["Subject", "From", "Date"]
        response = await self.http_client.get(
            f"{self.base_url}/users/me/messages/{message_id}",
            headers=self._headers(),
            params=params,
        )
        response.raise_for_status()
        return GmailMessage.model_validate(response.json())


def _decode_body(data: str | None) -> str:
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(
            "utf-8", errors="replace"
        )
    except (ValueError, TypeError):
        return ""


def _strip_html(html: str) -> str:
    import re
    no_scripts = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    no_tags = re.sub(r"<[^>]+>", " ", no_scripts)
    return re.sub(r"\s+", " ", no_tags).strip()


def extract_plain_text(message: GmailMessage) -> str:
    if message.payload is None:
        return ""

    plain_chunks: list[str] = []
    html_chunks: list[str] = []

    def walk(part: GmailMessagePayload) -> None:
        mime = (part.mime_type or "").lower()
        if part.parts:
            for child in part.parts:
                walk(child)
            return
        body_data = part.body.data if part.body else None
        if not body_data:
            return
        decoded = _decode_body(body_data)
        if mime == "text/plain":
            plain_chunks.append(decoded)
        elif mime == "text/html":
            html_chunks.append(decoded)

    walk(message.payload)

    if plain_chunks:
        return "\n".join(chunk.strip() for chunk in plain_chunks if chunk.strip())
    if html_chunks:
        return "\n".join(_strip_html(chunk) for chunk in html_chunks if chunk.strip())
    return ""
