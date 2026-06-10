from __future__ import annotations

from fastapi import Cookie, Depends, Header, Request
from httpx import AsyncClient

from app.config.settings import Settings, settings
from app.infrastructure.db.main import DBManager
from app.infrastructure.images.providers.base import ImageProvider
from app.infrastructure.llm.providers.base import LLMProvider
from app.infrastructure.security.crypto import CryptoManager
from app.infrastructure.security.session import SessionManager
from app.infrastructure.security.state import OAuthStateManager
from app.infrastructure.storage.base import BlobStorage
from app.services.queue.worker import PipelineWorker


def _from_state(request: Request, attr: str, friendly: str):
    value = getattr(request.app.state, attr, None)
    if value is None:
        raise RuntimeError(f"{friendly} not initialized; check lifespan setup")
    return value


def get_settings(request: Request) -> Settings:
    return _from_state(request, "settings", "Settings")


def get_db_manager(request: Request) -> DBManager:
    return _from_state(request, "db_manager", "Database manager")


def get_http_client(request: Request) -> AsyncClient:
    return _from_state(request, "http_client", "HTTP client")


def get_crypto(request: Request) -> CryptoManager:
    return _from_state(request, "crypto", "CryptoManager")


def get_state_manager(request: Request) -> OAuthStateManager:
    return _from_state(request, "state_manager", "OAuthStateManager")


def get_session_manager(request: Request) -> SessionManager:
    return _from_state(request, "session_manager", "SessionManager")


def get_llm_provider(request: Request) -> LLMProvider:
    return _from_state(request, "llm_provider", "LLMProvider")


def get_image_provider(request: Request) -> ImageProvider:
    return _from_state(request, "image_provider", "ImageProvider")


def get_storage(request: Request) -> BlobStorage:
    return _from_state(request, "storage", "BlobStorage")


def get_pipeline_worker(request: Request) -> PipelineWorker:
    return _from_state(request, "pipeline_worker", "PipelineWorker")


def get_session_user_id(
    session_manager: SessionManager = Depends(get_session_manager),
    session_cookie: str | None = Cookie(
        default=None, alias=settings.session_cookie_name
    ),
    authorization: str | None = Header(default=None),
) -> str | None:
    """Resolve the signed-in user from the session cookie or a Bearer token.

    The web frontend uses the cookie; the mobile app sends the same session
    token as `Authorization: Bearer <token>`.
    """
    token = session_cookie
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        return None
    return session_manager.verify_session(token)


def get_auth_service(
    db_manager: DBManager = Depends(get_db_manager),
    http_client: AsyncClient = Depends(get_http_client),
    crypto: CryptoManager = Depends(get_crypto),
    state_manager: OAuthStateManager = Depends(get_state_manager),
    session_manager: SessionManager = Depends(get_session_manager),
    settings: Settings = Depends(get_settings),
):
    from app.routers.v1.auth.service import AuthService

    return AuthService(
        db_manager, http_client, crypto, state_manager, session_manager, settings
    )


def get_webhook_service(
    db_manager: DBManager = Depends(get_db_manager),
    http_client: AsyncClient = Depends(get_http_client),
    crypto: CryptoManager = Depends(get_crypto),
    settings: Settings = Depends(get_settings),
    worker: PipelineWorker = Depends(get_pipeline_worker),
):
    from app.routers.v1.webhooks.gmail.service import GmailWebhookService

    return GmailWebhookService(db_manager, http_client, crypto, settings, worker)
