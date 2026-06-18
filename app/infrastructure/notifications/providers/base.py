from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum


class SendResult(str, Enum):
    OK = "ok"
    INVALID = "invalid"  # token unregistered — caller should prune it
    ERROR = "error"


class PushSender(ABC):
    """Pushes a data payload to one device token. One implementation per
    transport (FCM today; APNs / web push could follow)."""

    @abstractmethod
    async def send(self, token: str, data: dict[str, str]) -> SendResult: ...
