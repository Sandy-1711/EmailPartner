from __future__ import annotations

import uuid

from qdrant_client import AsyncQdrantClient, models

from app.infrastructure.vectorstore.providers.base import VectorHit, VectorRecord, VectorStore

# Qdrant point ids must be UUIDs or unsigned ints; our domain ids are Mongo
# ObjectId hex strings, so map them deterministically and keep the original in
# the payload under "_id".
_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")


def _point_id(domain_id: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, domain_id))


class QdrantVectorStore(VectorStore):
    def __init__(self, url: str, api_key: str | None, collection: str) -> None:
        self._client = AsyncQdrantClient(url=url, api_key=api_key)
        self._collection = collection

    async def ensure_collection(self, dim: int) -> None:
        if await self._client.collection_exists(self._collection):
            return
        await self._client.create_collection(
            self._collection,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )
        # index user_id so per-user filtering is efficient
        await self._client.create_payload_index(
            self._collection, "user_id", models.PayloadSchemaType.KEYWORD
        )

    async def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        points = [
            models.PointStruct(
                id=_point_id(r.id), vector=r.vector, payload={**r.payload, "_id": r.id}
            )
            for r in records
        ]
        await self._client.upsert(self._collection, points=points)

    async def search(self, vector: list[float], *, user_id: str, limit: int) -> list[VectorHit]:
        flt = models.Filter(
            must=[models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))]
        )
        response = await self._client.query_points(
            self._collection, query=vector, query_filter=flt, limit=limit, with_payload=True
        )
        return [
            VectorHit(
                id=str((p.payload or {}).get("_id", p.id)),
                score=p.score,
                payload=p.payload or {},
            )
            for p in response.points
        ]

    async def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        await self._client.delete(
            self._collection,
            points_selector=models.PointIdsList(points=[_point_id(i) for i in ids]),
        )
