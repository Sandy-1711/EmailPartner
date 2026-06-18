from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, TypeVar

from pydantic import BaseModel

GenericType = TypeVar('GenericType', bound=BaseModel)

class DocumentDBManager(ABC):
    @abstractmethod
    async def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_collection(self, name: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def insert_one(self, collection: type[GenericType], document: GenericType) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def insert_many(
        self, collection: type[GenericType], documents: Iterable[GenericType]
    ) -> Sequence[Any]:
        raise NotImplementedError

    @abstractmethod
    async def find_one(
        self,
        collection: type[GenericType],
        query: Mapping[str, Any],
        projection: Mapping[str, Any] | None = None,
    ) -> GenericType | None:
        raise NotImplementedError

    @abstractmethod
    async def find_many(
        self,
        collection: type[GenericType],
        query: Mapping[str, Any],
        projection: Mapping[str, Any] | None = None,
        *,
        limit: int | None = None,
        skip: int | None = None,
        sort: Sequence[tuple[str, int]] | None = None,
    ) -> list[GenericType]:
        raise NotImplementedError

    @abstractmethod
    async def update_one(
        self,
        collection: type[GenericType],
        query: Mapping[str, Any],
        update: Mapping[str, Any],
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def find_one_and_update(
        self,
        collection: type[GenericType],
        query: Mapping[str, Any],
        update: Mapping[str, Any],
        *,
        sort: Sequence[tuple[str, int]] | None = None,
        return_updated: bool = True,
    ) -> GenericType | None:
        """Atomically update the first matching document and return it."""
        raise NotImplementedError

    @abstractmethod
    async def upsert_one(
        self,
        collection: type[GenericType],
        query: Mapping[str, Any],
        update: Mapping[str, Any],
    ) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    async def delete_one(self, collection: type[GenericType], query: Mapping[str, Any]) -> int:
        raise NotImplementedError

    @abstractmethod
    async def delete_many(self, collection: type[GenericType], query: Mapping[str, Any]) -> int:
        raise NotImplementedError