from __future__ import annotations

import pytest
from bson import ObjectId

from app.infrastructure.notifications.providers import PushSender, SendResult
from app.services.notifications.push import PushNotifier, display_name
from app.services.storage import DeviceTokenStore

pytestmark = pytest.mark.anyio


class FakeSender(PushSender):
    def __init__(self, results: dict[str, SendResult] | None = None) -> None:
        self.results = results or {}
        self.sent: list[tuple[str, dict[str, str]]] = []

    async def send(self, token: str, data: dict[str, str]) -> SendResult:
        self.sent.append((token, data))
        return self.results.get(token, SendResult.OK)


def test_display_name_parses_and_falls_back():
    assert display_name('"Acme Team" <no-reply@acme.com>') == "Acme Team"
    assert display_name("plain@acme.com") == "plain@acme.com"
    assert display_name(None) == "Echo Mail"
    assert display_name("") == "Echo Mail"


async def test_notify_sends_data_only_to_all_tokens(db_manager):
    user = ObjectId()
    tokens = DeviceTokenStore(db_manager)
    await tokens.register(user, "tok-a", "android")
    await tokens.register(user, "tok-b", "android")
    sender = FakeSender()

    await PushNotifier(db_manager, sender).notify_card_ready(
        user_id=user,
        card_id="card-1",
        phrase="Acme said yes",
        sender="Acme",
        tone="informative",
        audio_url="https://x/a.wav",
    )

    assert {t for t, _ in sender.sent} == {"tok-a", "tok-b"}
    _, data = sender.sent[0]
    assert data == {
        "id": "card-1",
        "phrase": "Acme said yes",
        "sender": "Acme",
        "tone": "informative",
        "audio_url": "https://x/a.wav",
    }


async def test_notify_coerces_none_tone_and_audio_to_strings(db_manager):
    user = ObjectId()
    await DeviceTokenStore(db_manager).register(user, "tok", "android")
    sender = FakeSender()

    await PushNotifier(db_manager, sender).notify_card_ready(
        user_id=user, card_id="c", phrase="p", sender="s", tone=None, audio_url=None
    )

    _, data = sender.sent[0]
    assert data["tone"] == "" and data["audio_url"] == ""


async def test_notify_prunes_invalid_tokens(db_manager):
    user = ObjectId()
    tokens = DeviceTokenStore(db_manager)
    await tokens.register(user, "good", "android")
    await tokens.register(user, "stale", "android")
    sender = FakeSender({"stale": SendResult.INVALID})

    await PushNotifier(db_manager, sender).notify_card_ready(
        user_id=user, card_id="c", phrase="p", sender="s", tone=None, audio_url=None
    )

    assert await tokens.list_tokens(user) == ["good"]


async def test_notify_no_tokens_is_noop(db_manager):
    sender = FakeSender()
    await PushNotifier(db_manager, sender).notify_card_ready(
        user_id=ObjectId(), card_id="c", phrase="p", sender="s", tone=None, audio_url=None
    )
    assert sender.sent == []
