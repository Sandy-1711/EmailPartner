from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from httpx import AsyncClient

from app.config.settings import settings
from app.dependencies import get_db_manager, get_http_client
from app.infrastructure.db.main import DBManager
from app.infrastructure.security.crypto import CryptoManager
from app.models.api.webhooks import PubSubPushBody
from app.routers.v1.webhooks.gmail.service import GmailWebhookService

router = APIRouter(prefix="/webhooks/gmail", tags=["webhooks"])


def _get_webhook_service(
    db_manager: DBManager = Depends(get_db_manager),
    http_client: AsyncClient = Depends(get_http_client),
) -> GmailWebhookService:
    crypto = CryptoManager.from_secret(
        settings.encryption_master_key.get_secret_value(), settings.encryption_key_id
    )
    return GmailWebhookService(db_manager, http_client, crypto, settings)


@router.post("")
async def handle_gmail_webhook(
    request: Request,
    body: PubSubPushBody,
    service: GmailWebhookService = Depends(_get_webhook_service),
) -> dict[str, str]:
    token = request.query_params.get("token")
    if settings.pubsub_verification_token is not None:
        expected = settings.pubsub_verification_token.get_secret_value()
        if token != expected:
            raise HTTPException(status_code=401, detail="Invalid verification token")

    await service.handle_push(body)
    return {"status": "ok"}