from __future__ import annotations

import asyncio

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.config.settings import settings
from app.dependencies import get_db_manager
from app.infrastructure.db.main import DBManager
from app.models.api.cards import CardListResponse, EmailCard
from app.services.storage import EmailStore
from app.services.watch.email import EmailWatchService

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("/", response_model=CardListResponse)
async def list_cards(
    user_id: str = Query(...),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db_manager: DBManager = Depends(get_db_manager),
) -> CardListResponse:
    try:
        user_oid = ObjectId(user_id)
    except InvalidId as exc:
        raise HTTPException(status_code=400, detail="Invalid user_id") from exc

    store = EmailStore(db_manager)
    emails = await store.list_by_user(user_id=user_oid, limit=limit, offset=offset)
    cards = [
        EmailCard(
            id=str(email.id),
            gmail_message_id=email.gmail_message_id,
            subject=email.subject,
            from_email=email.from_email,
            snippet=email.snippet,
            received_at=email.received_at,
            processing_status=email.processing_status,
            background_image_url=email.card_background_url,
            text=email.card_text,
            audio_url=email.card_audio_url,
        )
        for email in emails
    ]
    next_offset = offset + len(cards) if len(cards) == limit else None
    return CardListResponse(items=cards, limit=limit, offset=offset, next_offset=next_offset)


@router.post("/{card_id}/retry")
async def retry_card(
    card_id: str,
    db_manager: DBManager = Depends(get_db_manager),
) -> dict[str, str]:
    try:
        card_oid = ObjectId(card_id)
    except InvalidId as exc:
        raise HTTPException(status_code=400, detail="Invalid card_id") from exc

    store = EmailStore(db_manager)
    email = await store.get_by_id(card_oid)
    if email is None:
        raise HTTPException(status_code=404, detail="Card not found")

    watcher = EmailWatchService(db_manager, settings)
    asyncio.create_task(watcher.watch_email(card_oid))
    return {"status": "scheduled", "card_id": card_id}
