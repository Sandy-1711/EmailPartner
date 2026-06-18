from __future__ import annotations

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.dependencies import (
    get_db_manager,
    get_email_memory,
    get_event_bus,
    get_pipeline_worker,
    get_session_user_id,
)
from app.infrastructure.db.main import DBManager
from app.models.api.cards import CardDetail, CardListResponse, EmailCard
from app.models.db.emails import Emails
from app.services.events import CardEventBus
from app.services.memory import EmailMemory
from app.services.queue.worker import PipelineWorker
from app.services.storage import EmailStore

router = APIRouter(prefix="/cards", tags=["cards"])


def _to_card(email: Emails) -> EmailCard:
    return EmailCard(
        id=str(email.id),
        gmail_message_id=email.gmail_message_id,
        subject=email.subject,
        from_email=email.from_email,
        snippet=email.snippet,
        received_at=email.received_at,
        processing_status=email.processing_status,
        background_image_url=email.card_background_url,
        text=email.card_text,
        phrase=email.card_phrase,
        tone=email.card_tone,
        audio_url=email.card_audio_url,
    )


@router.get("/", response_model=CardListResponse)
async def list_cards(
    user_id: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db_manager: DBManager = Depends(get_db_manager),
    session_user_id: str | None = Depends(get_session_user_id),
) -> CardListResponse:
    effective_user_id = user_id or session_user_id
    if effective_user_id is None:
        raise HTTPException(status_code=401, detail="Sign in or pass user_id")
    try:
        user_oid = ObjectId(effective_user_id)
    except InvalidId as exc:
        raise HTTPException(status_code=400, detail="Invalid user_id") from exc

    store = EmailStore(db_manager)
    emails = await store.list_by_user(user_id=user_oid, limit=limit, offset=offset)
    cards = [_to_card(email) for email in emails]
    next_offset = offset + len(cards) if len(cards) == limit else None
    return CardListResponse(items=cards, limit=limit, offset=offset, next_offset=next_offset)


@router.get("/stream")
async def stream_cards(
    event_bus: CardEventBus = Depends(get_event_bus),
    session_user_id: str | None = Depends(get_session_user_id),
) -> StreamingResponse:
    """Server-Sent Events: pushes a `card_ready` event the moment a card
    finishes processing, so the app updates live instead of polling. Declared
    before /{card_id} so "stream" isn't parsed as a card id."""
    if session_user_id is None:
        raise HTTPException(status_code=401, detail="Sign in required")

    async def events():
        yield ": connected\n\n"  # open the stream immediately
        async for payload in event_bus.subscribe(session_user_id):
            if payload is None:
                yield ": ping\n\n"  # heartbeat to keep the connection alive
            else:
                yield f"event: card_ready\ndata: {payload}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/search", response_model=CardListResponse)
async def search_cards(
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    memory: EmailMemory | None = Depends(get_email_memory),
    session_user_id: str | None = Depends(get_session_user_id),
) -> CardListResponse:
    """Semantic search over the user's emails. Declared before /{card_id} so
    "search" isn't parsed as a card id."""
    if session_user_id is None:
        raise HTTPException(status_code=401, detail="Sign in required")
    if memory is None:
        raise HTTPException(status_code=503, detail="Semantic search unavailable")
    emails = await memory.search(ObjectId(session_user_id), q, limit)
    cards = [_to_card(email) for email in emails]
    return CardListResponse(items=cards, limit=limit, offset=0, next_offset=None)


@router.get("/{card_id}", response_model=CardDetail)
async def get_card(
    card_id: str,
    db_manager: DBManager = Depends(get_db_manager),
    session_user_id: str | None = Depends(get_session_user_id),
) -> CardDetail:
    if session_user_id is None:
        raise HTTPException(status_code=401, detail="Sign in required")
    try:
        card_oid = ObjectId(card_id)
    except InvalidId as exc:
        raise HTTPException(status_code=400, detail="Invalid card_id") from exc

    email = await EmailStore(db_manager).get_by_id(card_oid)
    if email is None or str(email.user_id) != session_user_id:
        raise HTTPException(status_code=404, detail="Card not found")
    return CardDetail(**_to_card(email).model_dump(), body=email.body)


@router.post("/{card_id}/retry")
async def retry_card(
    card_id: str,
    db_manager: DBManager = Depends(get_db_manager),
    worker: PipelineWorker = Depends(get_pipeline_worker),
) -> dict[str, str]:
    try:
        card_oid = ObjectId(card_id)
    except InvalidId as exc:
        raise HTTPException(status_code=400, detail="Invalid card_id") from exc

    store = EmailStore(db_manager)
    email = await store.get_by_id(card_oid)
    if email is None:
        raise HTTPException(status_code=404, detail="Card not found")

    await store.requeue(card_oid)
    worker.notify()
    return {"status": "scheduled", "card_id": card_id}
