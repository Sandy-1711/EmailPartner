from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VectorRecord:
    """A point to store: a domain id (e.g. an email id), its vector, and payload
    used for filtering/return (must include ``user_id``)."""

    id: str
    vector: list[float]
    payload: dict[str, Any]


@dataclass(frozen=True)
class VectorHit:
    id: str
    score: float
    payload: dict[str, Any]


class VectorStore(ABC):
    @abstractmethod
    async def ensure_collection(self, dim: int) -> None:
        """Create the collection (idempotent) for vectors of size ``dim``."""
        ...

    @abstractmethod
    async def upsert(self, records: list[VectorRecord]) -> None: ...

    @abstractmethod
    async def search(self, vector: list[float], *, user_id: str, limit: int) -> list[VectorHit]:
        """Nearest neighbours for ``vector`` restricted to one user."""
        ...

    @abstractmethod
    async def delete(self, ids: list[str]) -> None: ...
