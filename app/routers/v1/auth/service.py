from __future__ import annotations

import asyncio
import logging

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from httpx import AsyncClient

from app.config.settings import Settings
from app.infrastructure.db.main import DBManager
from app.infrastructure.google.gmail import GmailApiClient
from app.infrastructure.google.oauth import OAuthClient, OAuthTokenResponse
from app.infrastructure.security.crypto import CryptoManager
from app.infrastructure.security.session import SessionManager
from app.infrastructure.security.state import OAuthStateManager
from app.models.api.auth import (
    DeleteAccountRequest,
    GoogleSignInCallbackResponse,
    GoogleSignInStartResponse,
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
        session_manager: SessionManager,
        settings: Settings,
    ) -> None:
        self._db_manager = db_manager
        self._http_client = http_client
        self._crypto = crypto
        self._state_manager = state_manager
        self._session_manager = session_manager
        self._settings = settings
        self._user_store = UserStore(db_manager)
        self._gmail_store = GmailAccountStore(db_manager)

    async def google_signin_start(self) -> GoogleSignInStartResponse:
        state = self._state_manager.create_state({"mode": "signin"})
        oauth_client = OAuthClient(self._settings)
        return GoogleSignInStartResponse(auth_url=oauth_client.build_authorization_url(state))

    async def handle_google_signin_callback(
        self, *, code: str, state: str
    ) -> tuple[GoogleSignInCallbackResponse, str]:
        payload = self._state_manager.verify_state_payload(state)
        if payload is None or payload.get("mode") != "signin":
            raise HTTPException(status_code=400, detail="Invalid or expired state")

        oauth_client = OAuthClient(self._settings)
        token_response = await oauth_client.exchange_code(self._http_client, code)
        if token_response.id_token is None:
            raise HTTPException(status_code=400, detail="Missing id_token from Google")
        if token_response.refresh_token is None:
            raise HTTPException(
                status_code=400,
                detail="Missing refresh_token; revoke prior consent and retry",
            )

        identity = await self._verify_id_token(token_response.id_token)
        google_sub = str(identity["sub"])
        email = str(identity["email"])
        raw_name = identity.get("name")
        raw_picture = identity.get("picture")
        display_name: str | None = str(raw_name) if isinstance(raw_name, str) else None
        picture_url: str | None = str(raw_picture) if isinstance(raw_picture, str) else None

        user = await self._user_store.get_by_google_sub(google_sub)
        if user is None:
            user = await self._user_store.get_by_email(email)

        if user is None:
            user = Users(
                email=email,
                display_name=display_name,
                google_sub=google_sub,
                picture_url=picture_url,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            await self._user_store.create(user)
        else:
            await self._user_store.update_google_identity(
                user.id,
                google_sub=google_sub,
                display_name=display_name,
                picture_url=picture_url,
            )

        _, gmail_address = await self._persist_gmail_account(user, token_response)
        session_token = self._session_manager.create_session(str(user.id))
        return (
            GoogleSignInCallbackResponse(
                user_id=str(user.id),
                email=user.email,
                display_name=display_name or user.display_name,
                gmail_address=gmail_address,
            ),
            session_token,
        )

    async def _verify_id_token(self, token: str):
        client_id = self._settings.oauth_client_id.get_secret_value()

        def _verify():
            return google_id_token.verify_oauth2_token( #type: ignore
                token, google_requests.Request(), client_id
            )

        try:
            return await asyncio.to_thread(_verify)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid id_token") from exc

    async def _persist_gmail_account(
        self, user: Users, token_response: OAuthTokenResponse
    ) -> tuple[str, str]:
        assert token_response.refresh_token is not None
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

        existing_by_user = await self._gmail_store.get_by_user_id(user.id)
        if existing_by_user is not None and existing_by_user.gmail_address != profile.email_address:
            raise HTTPException(
                status_code=409,
                detail="User already connected to a different Gmail account",
            )

        existing_account = await self._gmail_store.get_by_email(profile.email_address)
        if existing_account is not None and str(existing_account.user_id) != str(user.id):
            raise HTTPException(
                status_code=409,
                detail="Gmail address already linked to another user",
            )
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
            return str(existing_account.id), profile.email_address

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
        return str(account_id), profile.email_address

    async def delete_account(self, payload: DeleteAccountRequest) -> None:
        try:
            user_oid = ObjectId(payload.user_id)
        except InvalidId as exc:
            raise HTTPException(status_code=400, detail="Invalid user_id") from exc

        deleted = await self._user_store.mark_deleted(user_oid)
        if not deleted:
            raise HTTPException(status_code=404, detail="User not found")
        logger.info("User %s marked as deleted", payload.user_id)
