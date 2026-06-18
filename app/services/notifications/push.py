from __future__ import annotations

import logging
import re
from typing import Protocol

from bson import ObjectId
from pydantic import BaseModel

from app.infrastructure.db.main import DBManager
from app.infrastructure.notifications.fcm import MessageSender, SendResult
from app.services.storage import DeviceTokenStore

logger = logging.getLogger(__name__)

_DISPLAY_NAME = re.compile(r'^\s*"?([^"<]+?)"?\s*<')


def display_name(from_email: str | None) -> str:
    """`"Acme Team" <no-reply@acme.com>` -> `Acme Team`; falls back to the raw."""
    if not from_email:
        return "Echo Mail"
    match = _DISPLAY_NAME.match(from_email)
    return (match.group(1) if match else from_email).strip() or "Echo Mail"


class CardPush(BaseModel):
    """The FCM data payload for a ready card — the single source of truth for
    the contract the mobile EchoPushService reads. FCM data values must all be
    strings, so optional fields default to "" rather than None."""

    id: str
    phrase: str
    sender: str
    tone: str = ""
    audio_url: str = ""


class CardNotifier(Protocol):
    async def notify_card_ready(
        self,
        *,
        user_id: ObjectId,
        card_id: str,
        phrase: str,
        sender: str,
        tone: str | None,
        audio_url: str | None,
    ) -> None: ...


class PushNotifier:
    """Pushes a freshly-ready card to all of a user's registered devices.

    The message is DATA-only (the app's EchoPushService builds the actual
    notification + widget refresh), so payload values must all be strings.
    Tokens FCM reports as unregistered are pruned.
    """

    def __init__(self, db_manager: DBManager, sender: MessageSender) -> None:
        self._tokens = DeviceTokenStore(db_manager)
        self._sender = sender

    async def notify_card_ready(
        self,
        *,
        user_id: ObjectId,
        card_id: str,
        phrase: str,
        sender: str,
        tone: str | None,
        audio_url: str | None,
    ) -> None:
        tokens = await self._tokens.list_tokens(user_id)
        if not tokens:
            return
        data = CardPush(
            id=card_id,
            phrase=phrase,
            sender=sender,
            tone=tone or "",
            audio_url=audio_url or "",
        ).model_dump()
        for token in tokens:
            result = await self._sender.send(token, data)
            if result is SendResult.INVALID:
                await self._tokens.delete(token)
        logger.info("PushNotifier: pushed card %s to %d device(s)", card_id, len(tokens))
