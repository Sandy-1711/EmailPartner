from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

from bson import ObjectId

logger = logging.getLogger(__name__)


class CardEventBus:
    """In-process pub/sub for card-ready events, fanned out to SSE subscribers.

    Doubles as a CardNotifier sink: the pipeline calls notify_card_ready, which
    publishes to every live SSE connection for that user, so the app updates
    without polling. In-process only (one uvicorn worker) — a multi-worker
    deploy would swap this for Redis/NATS behind the same interface.
    """

    def __init__(self, max_queue: int = 100) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[str]]] = {}
        self._max_queue = max_queue

    # --- CardNotifier sink ---------------------------------------------------

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
        self.publish(
            str(user_id),
            {
                "type": "card_ready",
                "id": card_id,
                "phrase": phrase,
                "sender": sender,
                "tone": tone or "",
                "audio_url": audio_url or "",
            },
        )

    def publish(self, user_id: str, event: dict[str, str]) -> None:
        queues = self._subscribers.get(user_id)
        if not queues:
            return
        payload = json.dumps(event)
        for q in list(queues):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning("CardEventBus: dropping event for slow subscriber %s", user_id)

    # --- SSE source ----------------------------------------------------------

    async def subscribe(
        self, user_id: str, heartbeat: float = 15.0
    ) -> AsyncIterator[str | None]:
        """Yield JSON event payloads for a user; yields None as a heartbeat tick
        (so the endpoint can keep the connection alive through proxies)."""
        queue = self._register(user_id)
        try:
            while True:
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=heartbeat)
                except TimeoutError:
                    yield None
        finally:
            self._unregister(user_id, queue)

    def _register(self, user_id: str) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=self._max_queue)
        self._subscribers.setdefault(user_id, set()).add(queue)
        return queue

    def _unregister(self, user_id: str, queue: asyncio.Queue[str]) -> None:
        subs = self._subscribers.get(user_id)
        if subs is None:
            return
        subs.discard(queue)
        if not subs:
            self._subscribers.pop(user_id, None)
