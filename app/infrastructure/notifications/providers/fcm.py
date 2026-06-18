from __future__ import annotations

import asyncio
import json
import logging

from httpx import AsyncClient

from app.infrastructure.notifications.providers.base import PushSender, SendResult

logger = logging.getLogger(__name__)

_FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


class FcmSender(PushSender):
    """Sends FCM HTTP v1 messages with a service-account access token.

    Uses google-auth (already a dependency) to mint/refresh the OAuth token and
    the app's shared httpx client to POST — no firebase-admin SDK needed. The
    token is refreshed lazily and reused until it expires.
    """

    def __init__(self, credentials, project_id: str, http_client: AsyncClient) -> None:
        self._credentials = credentials
        self._project_id = project_id
        self._http = http_client
        self._lock = asyncio.Lock()
        self._url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

    @classmethod
    def from_credentials_file(cls, credentials_file: str, http_client: AsyncClient) -> FcmSender:
        """Build from a service-account JSON path (the project id is read from
        the file). Raises if the file is missing or malformed."""
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=[_FCM_SCOPE]
        )
        with open(credentials_file, encoding="utf-8") as fh:
            project_id = json.load(fh)["project_id"]
        return cls(creds, project_id, http_client)

    async def _access_token(self) -> str:
        if not self._credentials.valid:
            # refresh() is blocking (uses requests); guard with a lock so
            # concurrent sends don't all refresh at once.
            from google.auth.transport.requests import Request

            async with self._lock:
                if not self._credentials.valid:
                    await asyncio.to_thread(self._credentials.refresh, Request())
        return self._credentials.token

    async def send(self, token: str, data: dict[str, str]) -> SendResult:
        """Send a DATA-only message (so the app's handler always builds the
        notification) at high priority so it wakes a backgrounded app."""
        try:
            access = await self._access_token()
        except Exception:
            logger.exception("FcmSender: failed to mint access token")
            return SendResult.ERROR

        payload = {
            "message": {
                "token": token,
                "data": data,
                "android": {"priority": "high"},
            }
        }
        try:
            resp = await self._http.post(
                self._url,
                headers={"Authorization": f"Bearer {access}"},
                json=payload,
            )
        except Exception:
            logger.exception("FcmSender: send request failed")
            return SendResult.ERROR

        if resp.status_code == 200:
            return SendResult.OK
        if resp.status_code == 404:
            # UNREGISTERED: the token no longer maps to a device.
            return SendResult.INVALID
        logger.warning("FcmSender: send failed %s %s", resp.status_code, resp.text[:300])
        return SendResult.ERROR
