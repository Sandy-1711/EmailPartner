from __future__ import annotations

import asyncio
import base64
import json
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime

from httpx import AsyncClient, HTTPStatusError

from app.config.settings import Settings
from app.infrastructure.db.main import DBManager
from app.infrastructure.google.gmail import GmailApiClient, GmailHistoryResponse, GmailMessage
from app.infrastructure.google.oauth import OAuthClient
from app.infrastructure.security.crypto import CryptoManager
from app.models.api.webhooks import GmailNotification, PubSubPushBody
from app.models.db.emails import Emails
from app.models.db.gmail_account import GmailAccount
from app.models.db.utils import utc_now
from app.services.storage import EmailStore, GmailAccountStore
from app.services.watch.email import EmailWatchService

logger = logging.getLogger(__name__)


class GmailWebhookService:
    def __init__(
        self,
        db_manager: DBManager,
        http_client: AsyncClient,
        crypto: CryptoManager,
        settings: Settings,
    ) -> None:
        self._db_manager = db_manager
        self._http_client = http_client
        self._crypto = crypto
        self._settings = settings
        self._gmail_store = GmailAccountStore(db_manager)
        self._email_store = EmailStore(db_manager)

    async def handle_push(self, body: PubSubPushBody) -> None:
        notification = self._parse_notification(body)
        account = await self._gmail_store.get_by_email(notification.email_address)
        if account is None:
            logger.warning("No Gmail account for %s", notification.email_address)
            return

        access_token = await self._ensure_access_token(account)
        gmail_client = GmailApiClient(
            http_client=self._http_client,
            base_url=self._settings.gmail_api_base_url,
            access_token=access_token,
        )

        start_history_id = account.history_id or notification.history_id
        try:
            history_response = await gmail_client.list_history(
                start_history_id,
                history_types=self._settings.gmail_watch_history_types,
            )
        except HTTPStatusError as exc:
            logger.warning("Failed to read history: %s", exc)
            return

        await self._process_history(account, gmail_client, history_response)

        if history_response.history_id:
            await self._gmail_store.update_watch(
                account_id=account.id,
                history_id=history_response.history_id,
                watch_expiration=account.watch_expiration,
            )

    def _parse_notification(self, body: PubSubPushBody) -> GmailNotification:
        decoded = base64.b64decode(body.message.data).decode("utf-8")
        payload = json.loads(decoded)
        return GmailNotification.model_validate(payload)

    async def _ensure_access_token(self, account: GmailAccount) -> str:
        if account.access_token and account.access_token_expires_at:
            skew = self._settings.token_refresh_skew_seconds
            if (account.access_token_expires_at - utc_now()).total_seconds() > skew:
                return self._crypto.decrypt_str(account.access_token)

        refresh_token = self._crypto.decrypt_str(account.refresh_token)
        oauth_client = OAuthClient(self._settings)
        token_response = await oauth_client.refresh_access_token(
            self._http_client, refresh_token
        )
        encrypted_access = self._crypto.encrypt_str(token_response.access_token)
        await self._gmail_store.update_tokens(
            account_id=account.id,
            access_token=encrypted_access,
            access_expires_at=token_response.expires_at(),
        )
        return token_response.access_token

    async def _process_history(
        self,
        account: GmailAccount,
        gmail_client: GmailApiClient,
        history_response: GmailHistoryResponse,
    ) -> None:
        message_ids: list[str] = []
        for item in history_response.history:
            for added in item.messages_added:
                message_ids.append(added.message.id)

        for message_id in message_ids:
            message = await gmail_client.get_message(message_id)
            subject = _get_header(message, "Subject")
            from_header = _get_header(message, "From")
            date_header = _get_header(message, "Date")
            received_at = _parse_date(date_header)

            email_record = Emails(
                user_id=account.user_id,
                gmail_account_id=account.id,
                gmail_message_id=message.id,
                thread_id=message.thread_id,
                subject=subject,
                from_email=from_header,
                snippet=message.snippet,
                received_at=received_at,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            email_id = await self._email_store.upsert_email(email_record)
            asyncio.create_task(EmailWatchService.watch_email(email_id)).add_done_callback(
                _log_task_exception
            )


def _log_task_exception(task: asyncio.Task[None]) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.exception("Background email task failed", exc_info=exc)


def _get_header(message: GmailMessage, name: str) -> str | None:
    if message.payload is None:
        return None
    for header in message.payload.headers:
        if header.name.lower() == name.lower():
            return header.value
    return None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except Exception:
        return None
