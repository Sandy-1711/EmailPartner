from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class BlobStorage(Protocol):
    async def put(self, key: str, data: bytes, mime: str) -> str:
        """Store bytes under ``key`` and return a URL that resolves to them."""
        ...
