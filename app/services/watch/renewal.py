from __future__ import annotations

import logging
from datetime import timedelta

from httpx import AsyncClient

from app.config.settings import Settings
from app.infrastructure.db.main import DBManager
from app.infrastructure.google.gmail import GmailApiClient
from app.infrastructure.google.oauth import OAuthClient, is_invalid_grant
from app.infrastructure.security.crypto import CryptoManager
from app.models.db.gmail_account import GmailAccount
from app.models.db.utils import utc_now
from app.services.storage import GmailAccountStore

logger = logging.getLogger(__name__)


class WatchRenewalService:
    def __init__(
        self,
        db_manager: DBManager,
        http_client: AsyncClient,
        crypto: CryptoManager,
        settings: Settings,
    ) -> None:
        self._http_client = http_client
        self._crypto = crypto
        self._settings = settings
        self._gmail_store = GmailAccountStore(db_manager)

    async def renew_expiring(self, threshold: timedelta = timedelta(days=1)) -> int:
        deadline = utc_now() + threshold
        accounts = await self._gmail_store.find_expiring(deadline)
        renewed = 0
        for account in accounts:
            try:
                await self._renew_one(account)
                renewed += 1
            except Exception as exc:
                if is_invalid_grant(exc):
                    await self._gmail_store.mark_disabled(account.id)
                    logger.warning(
                        "WatchRenewalService: %s revoked access (invalid_grant); disabled",
                        account.gmail_address,
                    )
                else:
                    logger.exception(
                        "WatchRenewalService: failed to renew account %s", account.id
                    )
        return renewed

    async def _renew_one(self, account: GmailAccount) -> None:
        access_token = await self._ensure_access_token(account)
        gmail_client = GmailApiClient(
            http_client=self._http_client,
            base_url=self._settings.gmail_api_base_url,
            access_token=access_token,
        )
        watch_response = await gmail_client.watch(
            topic_name=self._settings.gmail_watch_topic,
            label_ids=self._settings.gmail_watch_label_ids,
            history_types=self._settings.gmail_watch_history_types,
        )
        await self._gmail_store.update_watch(
            account_id=account.id,
            history_id=watch_response.history_id,
            watch_expiration=watch_response.expiration_datetime(),
        )
        logger.info(
            "WatchRenewalService: renewed %s through %s",
            account.gmail_address,
            watch_response.expiration_datetime(),
        )

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
