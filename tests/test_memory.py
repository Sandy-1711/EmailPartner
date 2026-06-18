from __future__ import annotations

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.models.db.emails import EmailProcessingStatus
from app.routers.v1.cards.controller import search_cards
from app.services.memory import EmailMemory
from app.services.storage import EmailStore
from tests.fakes import FakeEmbedder, FakeVectorStore
from tests.test_email_store import make_email

pytestmark = pytest.mark.anyio


def _memory(db_manager) -> tuple[EmailMemory, FakeVectorStore]:
    store = FakeVectorStore()
    return EmailMemory(db_manager, FakeEmbedder(), store), store


async def _add(db_manager, memory, **fields):
    email = make_email(message_id=str(ObjectId()), **fields)
    await EmailStore(db_manager).upsert_email(email)
    await memory.index(email)
    return email


async def test_index_then_search_ranks_by_meaning(db_manager):
    user = ObjectId()
    memory, _ = _memory(db_manager)
    offer = await _add(
        db_manager, memory, user_id=user, subject="Your job offer from Acme", body="offer offer"
    )
    await _add(
        db_manager, memory, user_id=user, subject="Lunch menu", body="soup salad sandwich"
    )

    results = await memory.search(user, "job offer", limit=5)

    assert results[0].id == offer.id  # best match first
    assert offer.id in {e.id for e in results}


async def test_search_is_isolated_per_user(db_manager):
    memory, _ = _memory(db_manager)
    mine = ObjectId()
    await _add(db_manager, memory, user_id=ObjectId(), subject="job offer", body="offer")

    results = await memory.search(mine, "job offer", limit=5)

    assert results == []


async def test_index_skips_empty_document(db_manager):
    memory, store = _memory(db_manager)
    email = make_email(subject=None, snippet=None, body=None)
    await memory.index(email)
    assert store.records == {}


async def test_search_endpoint_returns_cards(db_manager):
    user = ObjectId()
    memory, _ = _memory(db_manager)
    email = await _add(
        db_manager, memory, user_id=user, subject="job offer", body="offer", from_email="a@acme.com"
    )
    await EmailStore(db_manager).update_card_fields(
        email.id, processing_status=EmailProcessingStatus.READY, card_phrase="You got the job"
    )

    resp = await search_cards(
        q="job offer", limit=10, memory=memory, session_user_id=str(user)
    )

    assert [c.id for c in resp.items] == [str(email.id)]


async def test_search_endpoint_401_without_session(db_manager):
    memory, _ = _memory(db_manager)
    with pytest.raises(HTTPException) as exc:
        await search_cards(q="x", limit=10, memory=memory, session_user_id=None)
    assert exc.value.status_code == 401


async def test_search_endpoint_503_when_memory_unavailable():
    with pytest.raises(HTTPException) as exc:
        await search_cards(q="x", limit=10, memory=None, session_user_id=str(ObjectId()))
    assert exc.value.status_code == 503
