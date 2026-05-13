from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.config.settings import settings
from app.dependencies import get_webhook_service
from app.models.api.webhooks import PubSubPushBody
from app.routers.v1.webhooks.gmail.service import GmailWebhookService

router = APIRouter(prefix="/webhooks/gmail", tags=["webhooks"])


@router.post("")
async def handle_gmail_webhook(
    request: Request,
    body: PubSubPushBody,
    service: GmailWebhookService = Depends(get_webhook_service),
) -> dict[str, str]:
    token = request.query_params.get("token")
    if settings.pubsub_verification_token is not None:
        expected = settings.pubsub_verification_token.get_secret_value()
        if token != expected:
            raise HTTPException(status_code=401, detail="Invalid verification token")

    await service.handle_push(body)
    return {"status": "ok"}
