from __future__ import annotations

import asyncio
import json

import pytest
from bson import ObjectId

from app.services.events import CardEventBus

pytestmark = pytest.mark.anyio


async def _subscribe_one(bus: CardEventBus, user_id: str) -> tuple[asyncio.Task[None], dict]:
    """Start a subscriber that captures the first real (non-heartbeat) event."""
    got: dict = {}

    async def consume() -> None:
        async for payload in bus.subscribe(user_id, heartbeat=0.02):
            if payload is not None:
                got.update(json.loads(payload))
                return

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.01)  # let the subscriber register
    return task, got


async def test_notify_reaches_subscriber_for_that_user():
    bus = CardEventBus()
    uid = ObjectId()
    task, got = await _subscribe_one(bus, str(uid))

    await bus.notify_card_ready(
        user_id=uid,
        card_id="card-1",
        phrase="Acme said yes",
        sender="Acme",
        tone="informative",
        audio_url="https://x/a.wav",
    )
    await asyncio.wait_for(task, timeout=1)

    assert got == {
        "type": "card_ready",
        "id": "card-1",
        "phrase": "Acme said yes",
        "sender": "Acme",
        "tone": "informative",
        "audio_url": "https://x/a.wav",
    }


async def test_publish_is_isolated_per_user():
    bus = CardEventBus()
    task, got = await _subscribe_one(bus, str(ObjectId()))

    # publish for a different user — the subscriber must not receive it
    await bus.notify_card_ready(
        user_id=ObjectId(), card_id="c", phrase="p", sender="s", tone=None, audio_url=None
    )
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(asyncio.shield(task), timeout=0.1)
    task.cancel()
    assert got == {}


async def test_publish_with_no_subscribers_is_noop():
    bus = CardEventBus()
    await bus.notify_card_ready(
        user_id=ObjectId(), card_id="c", phrase="p", sender="s", tone=None, audio_url=None
    )  # must not raise


async def test_subscriber_cleanup_after_cancel():
    bus = CardEventBus()
    uid = str(ObjectId())
    task, _ = await _subscribe_one(bus, uid)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await asyncio.sleep(0.01)
    assert uid not in bus._subscribers
