from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from pydantic import BaseModel

from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from app.infrastructure.db.document import DocumentDBManager, GenericType


class MongoDBManager(DocumentDBManager):
    def __init__(self, uri: str, database: str) -> None:
        self._uri = uri
        self._database = database
        self._client: AsyncMongoClient[Any] | None = None
        self._db: AsyncDatabase[Any] | None = None
        self._collections_cache: dict[str, AsyncCollection[Any]] = {}

    async def connect(self) -> None:
        if self._client is not None:
            return
        self._client = AsyncMongoClient(self._uri)
        self._db = self._client[self._database]
        await self._client.admin.command("ping")

    async def disconnect(self) -> None:
        if self._client is None:
            return
        await self._client.close()
        self._client = None
        self._db = None
        self._collections_cache.clear()

    def get_collection(self, name: str) -> AsyncCollection[Any]:
        if self._db is None:
            raise RuntimeError("Database not connected")
        cached = self._collections_cache.get(name)
        if cached is not None:
            return cached
        collection = self._db.get_collection(name)
        self._collections_cache[name] = collection
        return collection

    def _resolve_collection_name(self, model_type: type[BaseModel]) -> str:
        explicit = getattr(model_type, "collection_name", None) or getattr(
            model_type, "__collection__", None
        )
        if isinstance(explicit, str) and explicit.strip():
            return explicit
        return model_type.__name__.lower()

    def _get_collection_by_type(self, model_type: type[BaseModel]) -> AsyncCollection[Any]:
        return self.get_collection(self._resolve_collection_name(model_type))

    async def insert_one(self, collection: type[GenericType], document: GenericType) -> Any:
        result = await self._get_collection_by_type(collection).insert_one(
            document.model_dump()
        )
        return result.inserted_id

    async def insert_many(
        self, collection: type[GenericType], documents: Iterable[GenericType]
    ) -> Sequence[Any]:
        docs = [document.model_dump() for document in documents]
        if not docs:
            return []
        result = await self._get_collection_by_type(collection).insert_many(docs)
        return result.inserted_ids

    async def find_one(
        self,
        collection: type[GenericType],
        query: Mapping[str, Any],
        projection: Mapping[str, Any] | None = None,
    ) -> GenericType | None:
        document = await self._get_collection_by_type(collection).find_one(
            query, projection
        )
        if document is None:
            return None
        return collection.model_validate(document)

    async def find_many(
        self,
        collection: type[GenericType],
        query: Mapping[str, Any],
        projection: Mapping[str, Any] | None = None,
        *,
        limit: int | None = None,
        skip: int | None = None,
    ) -> list[GenericType]:
        cursor = self._get_collection_by_type(collection).find(query, projection)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        return [collection.model_validate(document) async for document in cursor]

    async def update_one(
        self,
        collection: type[GenericType],
        query: Mapping[str, Any],
        update: Mapping[str, Any],
    ) -> int:
        result = await self._get_collection_by_type(collection).update_one(query, update)
        return result.modified_count

    async def upsert_one(
        self,
        collection: type[GenericType],
        query: Mapping[str, Any],
        update: Mapping[str, Any],
    ) -> Any | None:
        result = await self._get_collection_by_type(collection).update_one(
            query, update, upsert=True
        )
        return result.upserted_id

    async def delete_one(
        self, collection: type[GenericType], query: Mapping[str, Any]
    ) -> int:
        result = await self._get_collection_by_type(collection).delete_one(query)
        return result.deleted_count

    async def delete_many(
        self, collection: type[GenericType], query: Mapping[str, Any]
    ) -> int:
        result = await self._get_collection_by_type(collection).delete_many(query)
        return result.deleted_count
    