from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from httpx import AsyncClient

from app.config.settings import settings
from app.dependencies import get_db_manager, get_http_client
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
from app.routers.v1.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_auth_service(
    db_manager=Depends(get_db_manager),
    http_client: AsyncClient = Depends(get_http_client),
) -> AuthService:
    crypto = CryptoManager.from_secret(
        settings.encryption_master_key.get_secret_value(), settings.encryption_key_id
    )
    state_manager = OAuthStateManager(
        secret=settings.oauth_state_secret.get_secret_value().encode("utf-8"),
        ttl_seconds=settings.oauth_state_ttl_seconds,
    )
    return AuthService(db_manager, http_client, crypto, state_manager, settings)


@router.post("/signup", response_model=SignupResponse)
async def signup(
    payload: SignupRequest, service: AuthService = Depends(_get_auth_service)
) -> SignupResponse:
    return await service.signup(payload)


@router.post("/connect-gmail", response_model=ConnectGmailResponse)
async def connect_gmail(
    payload: ConnectGmailRequest, service: AuthService = Depends(_get_auth_service)
) -> ConnectGmailResponse:
    return await service.connect_gmail(payload)


@router.get("/oauth/callback", response_model=OAuthCallbackResponse)
async def oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    service: AuthService = Depends(_get_auth_service),
) -> OAuthCallbackResponse:
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
    return await service.handle_oauth_callback(code=code, state=state)


@router.post("/delete-account")
async def delete_account(
    payload: DeleteAccountRequest, service: AuthService = Depends(_get_auth_service)
) -> dict[str, str]:
    await service.delete_account(payload)
    return {"status": "deleted"}
