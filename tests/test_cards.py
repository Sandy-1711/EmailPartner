from __future__ import annotations

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.models.db.emails import EmailProcessingStatus
from app.routers.v1.cards.controller import get_card
from app.services.storage import EmailStore
from tests.test_email_store import make_email

pytestmark = pytest.mark.anyio


async def _ready_email(store: EmailStore):
    email = make_email(body="Full body text")
    await store.upsert_email(email)
    await store.update_card_fields(
        email.id,
        processing_status=EmailProcessingStatus.READY,
        card_text="Headline\n\nSummary",
        card_phrase="the phrase",
        card_tone="informative",
    )
    return email


async def test_get_card_returns_detail_for_owner(db_manager):
    email = await _ready_email(EmailStore(db_manager))

    detail = await get_card(
        card_id=str(email.id), db_manager=db_manager, session_user_id=str(email.user_id)
    )

    assert detail.id == str(email.id)
    assert detail.body == "Full body text"
    assert detail.phrase == "the phrase"
    assert detail.processing_status == EmailProcessingStatus.READY


async def test_get_card_404_for_non_owner(db_manager):
    email = await _ready_email(EmailStore(db_manager))

    with pytest.raises(HTTPException) as exc:
        await get_card(
            card_id=str(email.id), db_manager=db_manager, session_user_id=str(ObjectId())
        )
    assert exc.value.status_code == 404


async def test_get_card_401_without_session(db_manager):
    with pytest.raises(HTTPException) as exc:
        await get_card(card_id=str(ObjectId()), db_manager=db_manager, session_user_id=None)
    assert exc.value.status_code == 401


async def test_get_card_400_for_invalid_id(db_manager):
    with pytest.raises(HTTPException) as exc:
        await get_card(
            card_id="not-an-objectid", db_manager=db_manager, session_user_id=str(ObjectId())
        )
    assert exc.value.status_code == 400
