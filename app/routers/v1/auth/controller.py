from __future__ import annotations

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response
from httpx import AsyncClient

from app.config.settings import settings
from app.dependencies import get_db_manager, get_http_client
from app.infrastructure.db.main import DBManager
from app.infrastructure.security.crypto import CryptoManager
from app.infrastructure.security.session import SessionManager
from app.infrastructure.security.state import OAuthStateManager
from app.models.api.auth import (
    DeleteAccountRequest,
    GoogleSignInCallbackResponse,
    GoogleSignInStartResponse,
    MeResponse,
)
from app.routers.v1.auth.service import AuthService
from app.services.storage import GmailAccountStore, UserStore

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_session_manager() -> SessionManager:
    return SessionManager(
        secret=settings.session_secret.get_secret_value().encode("utf-8"),
        ttl_seconds=settings.session_ttl_seconds,
    )


def _get_auth_service(
    db_manager: DBManager = Depends(get_db_manager),
    http_client: AsyncClient = Depends(get_http_client),
) -> AuthService:
    crypto = CryptoManager.from_secret(
        settings.encryption_master_key.get_secret_value(), settings.encryption_key_id
    )
    state_manager = OAuthStateManager(
        secret=settings.oauth_state_secret.get_secret_value().encode("utf-8"),
        ttl_seconds=settings.oauth_state_ttl_seconds,
    )
    session_manager = _build_session_manager()
    return AuthService(
        db_manager, http_client, crypto, state_manager, session_manager, settings
    )


@router.get("/google/start", response_model=GoogleSignInStartResponse)
async def google_signin_start(
    service: AuthService = Depends(_get_auth_service),
) -> GoogleSignInStartResponse:
    return await service.google_signin_start()


@router.get("/google/callback", response_model=GoogleSignInCallbackResponse)
async def google_signin_callback(
    response: Response,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    service: AuthService = Depends(_get_auth_service),
) -> GoogleSignInCallbackResponse:
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    payload, session_token = await service.handle_google_signin_callback(
        code=code, state=state
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )
    return payload


@router.get("/me", response_model=MeResponse)
async def me(
    db_manager: DBManager = Depends(get_db_manager),
    session_cookie: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> MeResponse:
    if session_cookie is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_manager = _build_session_manager()
    user_id = session_manager.verify_session(session_cookie)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    try:
        user_oid = ObjectId(user_id)
    except InvalidId as exc:
        raise HTTPException(status_code=401, detail="Invalid session payload") from exc

    user = await UserStore(db_manager).get_by_id(user_oid)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    gmail_account = await GmailAccountStore(db_manager).get_by_user_id(user_oid)
    return MeResponse(
        user_id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        picture_url=user.picture_url,
        gmail_connected=gmail_account is not None,
    )


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(settings.session_cookie_name)
    return {"status": "ok"}


@router.post("/delete-account")
async def delete_account(
    payload: DeleteAccountRequest, service: AuthService = Depends(_get_auth_service)
) -> dict[str, str]:
    await service.delete_account(payload)
    return {"status": "deleted"}
