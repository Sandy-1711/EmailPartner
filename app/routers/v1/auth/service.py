from __future__ import annotations

import logging

from fastapi import HTTPException
from httpx import AsyncClient

from app.config.settings import Settings
from app.infrastructure.db.main import DBManager
from app.infrastructure.google.gmail import GmailApiClient
from app.infrastructure.google.oauth import OAuthClient
from app.infrastructure.security.crypto import CryptoManager
from app.infrastructure.security.state import OAuthStateManager
from app.models.api.auth import (
    ConnectGmailRequest,
    ConnectGmailResponse,
    DeleteAccountRequest,
    OAuthCallbackResponse,
    SignupRequest,
    SignupResponse,
)
from app.models.db.gmail_account import GmailAccount
from app.models.db.user import Users
from app.models.db.utils import utc_now
from app.services.storage import GmailAccountStore, UserStore

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
        self,
        db_manager: DBManager,
        http_client: AsyncClient,
        crypto: CryptoManager,
        state_manager: OAuthStateManager,
        settings: Settings,
    ) -> None:
        self._db_manager = db_manager
        self._http_client = http_client
        self._crypto = crypto
        self._state_manager = state_manager
        self._settings = settings
        self._user_store = UserStore(db_manager)
        self._gmail_store = GmailAccountStore(db_manager)

    async def signup(self, payload: SignupRequest) -> SignupResponse:
        existing = await self._user_store.get_by_email(payload.email)
        if existing is not None:
            return SignupResponse(user_id=str(existing.id))

        user = Users(
            email=payload.email,
            display_name=payload.display_name,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        user_id = await self._user_store.create(user)
        return SignupResponse(user_id=str(user_id))

    async def connect_gmail(self, payload: ConnectGmailRequest) -> ConnectGmailResponse:
        user = await self._user_store.get_by_id(payload.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        state = self._state_manager.create_state(str(user.id))
        oauth_client = OAuthClient(self._settings)
        auth_url = oauth_client.build_authorization_url(state)
        return ConnectGmailResponse(auth_url=auth_url)

    async def handle_oauth_callback(
        self, *, code: str, state: str
    ) -> OAuthCallbackResponse:
        user_id = self._state_manager.verify_state(state)
        if user_id is None:
            raise HTTPException(status_code=400, detail="Invalid or expired state")

        user = await self._user_store.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        oauth_client = OAuthClient(self._settings)
        token_response = await oauth_client.exchange_code(self._http_client, code)
        if token_response.refresh_token is None:
            raise HTTPException(status_code=400, detail="Missing refresh token")

        encrypted_refresh = self._crypto.encrypt_str(token_response.refresh_token)
        encrypted_access = self._crypto.encrypt_str(token_response.access_token)
        access_expires_at = token_response.expires_at()

        gmail_client = GmailApiClient(
            http_client=self._http_client,
            base_url=self._settings.gmail_api_base_url,
            access_token=token_response.access_token,
        )
        profile = await gmail_client.get_profile()
        watch_response = await gmail_client.watch(
            topic_name=self._settings.gmail_watch_topic,
            label_ids=self._settings.gmail_watch_label_ids,
            history_types=self._settings.gmail_watch_history_types,
        )

        existing_account = await self._gmail_store.get_by_email(profile.email_address)
        if existing_account is not None:
            await self._gmail_store.update_tokens(
                account_id=existing_account.id,
                access_token=encrypted_access,
                access_expires_at=access_expires_at,
                refresh_token=encrypted_refresh,
            )
            await self._gmail_store.update_watch(
                account_id=existing_account.id,
                history_id=watch_response.history_id,
                watch_expiration=watch_response.expiration_datetime(),
            )
            return OAuthCallbackResponse(
                gmail_account_id=str(existing_account.id),
                gmail_address=profile.email_address,
            )

        account = GmailAccount(
            user_id=user.id,
            gmail_address=profile.email_address,
            refresh_token=encrypted_refresh,
            access_token=encrypted_access,
            access_token_expires_at=access_expires_at,
            history_id=watch_response.history_id,
            watch_expiration=watch_response.expiration_datetime(),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        account_id = await self._gmail_store.create(account)
        return OAuthCallbackResponse(
            gmail_account_id=str(account_id),
            gmail_address=profile.email_address,
        )

    async def delete_account(self, payload: DeleteAccountRequest) -> None:
        deleted = await self._user_store.mark_deleted(payload.user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="User not found")
        logger.info("User %s marked as deleted", payload.user_id)