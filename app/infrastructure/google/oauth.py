from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, Field

from app.config.settings import Settings


class OAuthTokenResponse(BaseModel):
    access_token: str = Field(alias="access_token")
    expires_in: int = Field(alias="expires_in")
    refresh_token: str | None = Field(default=None, alias="refresh_token")
    scope: str | None = Field(default=None, alias="scope")
    token_type: str = Field(alias="token_type")

    def expires_at(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(seconds=self.expires_in)


@dataclass(frozen=True)
class OAuthClient:
    settings: Settings

    def build_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.settings.oauth_client_id.get_secret_value(),
            "redirect_uri": self.settings.oauth_redirect_uri,
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        params["scope"] = " ".join(self.settings.oauth_scopes)
        return f"{self.settings.google_oauth_authorize_url}?{urlencode(params)}"

    async def exchange_code(self, client: httpx.AsyncClient, code: str) -> OAuthTokenResponse:
        data = {
            "code": code,
            "client_id": self.settings.oauth_client_id.get_secret_value(),
            "client_secret": self.settings.oauth_client_secret.get_secret_value(),
            "redirect_uri": self.settings.oauth_redirect_uri,
            "grant_type": "authorization_code",
        }
        response = await client.post(self.settings.google_oauth_token_url, data=data)
        response.raise_for_status()
        return OAuthTokenResponse.model_validate(response.json())

    async def refresh_access_token(
        self, client: httpx.AsyncClient, refresh_token: str
    ) -> OAuthTokenResponse:
        data = {
            "client_id": self.settings.oauth_client_id.get_secret_value(),
            "client_secret": self.settings.oauth_client_secret.get_secret_value(),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        response = await client.post(self.settings.google_oauth_token_url, data=data)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        if "refresh_token" not in payload:
            payload["refresh_token"] = refresh_token
        return OAuthTokenResponse.model_validate(payload)
