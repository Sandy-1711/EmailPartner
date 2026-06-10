from __future__ import annotations

from datetime import timedelta

import pytest
from bson import ObjectId

from app.models.db.emails import EmailProcessingStatus, Emails
from app.models.db.utils import utc_now
from app.services.storage import EmailStore

pytestmark = pytest.mark.anyio


def make_email(message_id: str = "msg-1", **overrides) -> Emails:
    defaults = dict(
        user_id=ObjectId(),
        gmail_account_id=ObjectId(),
        gmail_message_id=message_id,
        subject="Hello",
        snippet="snippet",
        received_at=utc_now(),
    )
    defaults.update(overrides)
    return Emails(**defaults)


async def test_upsert_inserts_then_preserves_card_fields(db_manager):
    store = EmailStore(db_manager)
    email = make_email()

    email_id, is_new = await store.upsert_email(email)
    assert is_new

    await store.update_card_fields(
        email_id,
        processing_status=EmailProcessingStatus.READY,
        card_text="headline\n\nsummary",
    )

    duplicate = make_email(snippet="fresher snippet")
    dup_id, is_new = await store.upsert_email(duplicate)
    assert dup_id == email_id
    assert not is_new

    stored = await store.get_by_id(email_id)
    assert stored is not None
    assert stored.processing_status == EmailProcessingStatus.READY
    assert stored.card_text == "headline\n\nsummary"
    assert stored.snippet == "fresher snippet"


async def test_claim_next_pending_oldest_first_and_increments_attempts(db_manager):
    store = EmailStore(db_manager)
    old = make_email("old", created_at=utc_now() - timedelta(minutes=5))
    new = make_email("new", created_at=utc_now())
    await store.upsert_email(new)
    await store.upsert_email(old)

    first = await store.claim_next_pending()
    assert first is not None
    assert first.gmail_message_id == "old"
    assert first.processing_status == EmailProcessingStatus.PROCESSING
    assert first.attempts == 1
    assert first.claimed_at is not None

    second = await store.claim_next_pending()
    assert second is not None
    assert second.gmail_message_id == "new"

    assert await store.claim_next_pending() is None


async def test_requeue_resets_to_pending(db_manager):
    store = EmailStore(db_manager)
    email_id, _ = await store.upsert_email(make_email())
    claimed = await store.claim_next_pending()
    assert claimed is not None

    await store.requeue(email_id)
    stored = await store.get_by_id(email_id)
    assert stored is not None
    assert stored.processing_status == EmailProcessingStatus.PENDING
    assert stored.claimed_at is None


async def test_reset_stale_processing_requeues_expired_leases(db_manager):
    store = EmailStore(db_manager)
    stale_id, _ = await store.upsert_email(make_email("stale"))
    orphan_id, _ = await store.upsert_email(make_email("orphan"))
    fresh_id, _ = await store.upsert_email(make_email("fresh"))

    long_ago = utc_now() - timedelta(hours=2)
    await db_manager.document_db.update_one(
        Emails,
        {"_id": stale_id},
        {"$set": {"processing_status": "processing", "claimed_at": long_ago}},
    )
    await db_manager.document_db.update_one(
        Emails,
        {"_id": orphan_id},
        {"$set": {"processing_status": "processing", "claimed_at": None}},
    )
    await db_manager.document_db.update_one(
        Emails,
        {"_id": fresh_id},
        {"$set": {"processing_status": "processing", "claimed_at": utc_now()}},
    )

    reset = await store.reset_stale_processing(utc_now() - timedelta(minutes=10))
    assert reset == 2

    for email_id, expected in (
        (stale_id, EmailProcessingStatus.PENDING),
        (orphan_id, EmailProcessingStatus.PENDING),
        (fresh_id, EmailProcessingStatus.PROCESSING),
    ):
        stored = await store.get_by_id(email_id)
        assert stored is not None
        assert stored.processing_status == expected


async def test_list_by_user_newest_first(db_manager):
    store = EmailStore(db_manager)
    user_id = ObjectId()
    base = utc_now()
    for i in range(3):
        await store.upsert_email(
            make_email(f"msg-{i}", user_id=user_id, received_at=base + timedelta(minutes=i))
        )
    await store.upsert_email(make_email("other-user"))

    emails = await store.list_by_user(user_id=user_id, limit=10, offset=0)
    assert [e.gmail_message_id for e in emails] == ["msg-2", "msg-1", "msg-0"]
