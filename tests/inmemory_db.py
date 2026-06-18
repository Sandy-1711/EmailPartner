from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from pydantic import BaseModel

from app.infrastructure.db.document import DocumentDBManager, GenericType


class InMemoryDocumentDB(DocumentDBManager):
    """Dict-backed DocumentDBManager supporting the query/update subset the app uses."""

    def __init__(self) -> None:
        self._collections: dict[str, list[dict[str, Any]]] = {}

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    def get_collection(self, name: str) -> list[dict[str, Any]]:
        return self._collections.setdefault(name, [])

    def _docs(self, model_type: type[BaseModel]) -> list[dict[str, Any]]:
        name = getattr(model_type, "__collection__", None) or model_type.__name__.lower()
        return self.get_collection(name)

    @staticmethod
    def _matches(doc: Mapping[str, Any], query: Mapping[str, Any]) -> bool:
        for key, cond in query.items():
            if key == "$or":
                if not any(InMemoryDocumentDB._matches(doc, sub) for sub in cond):
                    return False
                continue
            value = doc.get(key)
            if isinstance(cond, Mapping) and any(str(k).startswith("$") for k in cond):
                for op, operand in cond.items():
                    if op == "$lt":
                        if value is None or not value < operand:
                            return False
                    elif op == "$gt":
                        if value is None or not value > operand:
                            return False
                    elif op == "$in":
                        if value not in operand:
                            return False
                    else:
                        raise NotImplementedError(f"operator {op}")
            elif cond is None:
                if value is not None:
                    return False
            elif value != cond:
                return False
        return True

    @staticmethod
    def _apply_update(doc: dict[str, Any], update: Mapping[str, Any]) -> None:
        for op, fields in update.items():
            if op == "$set":
                doc.update(fields)
            elif op == "$inc":
                for field, amount in fields.items():
                    doc[field] = doc.get(field, 0) + amount
            else:
                raise NotImplementedError(f"operator {op}")

    @staticmethod
    def _sort_docs(
        docs: list[dict[str, Any]], sort: Sequence[tuple[str, int]] | None
    ) -> list[dict[str, Any]]:
        result = list(docs)
        if not sort:
            return result
        for field, direction in reversed(list(sort)):
            result.sort(
                key=lambda d: (1,) if d.get(field) is None else (0, d.get(field)),
                reverse=direction < 0,
            )
        return result

    async def insert_one(self, collection: type[GenericType], document: GenericType) -> Any:
        doc = document.model_dump(by_alias=True, exclude_none=True)
        self._docs(collection).append(copy.deepcopy(doc))
        return doc["_id"]

    async def insert_many(
        self, collection: type[GenericType], documents: Iterable[GenericType]
    ) -> Sequence[Any]:
        return [await self.insert_one(collection, document) for document in documents]

    async def find_one(
        self,
        collection: type[GenericType],
        query: Mapping[str, Any],
        projection: Mapping[str, Any] | None = None,
    ) -> GenericType | None:
        for doc in self._docs(collection):
            if self._matches(doc, query):
                return collection.model_validate(copy.deepcopy(doc))
        return None

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
        matched = [doc for doc in self._docs(collection) if self._matches(doc, query)]
        matched = self._sort_docs(matched, sort)
        if skip:
            matched = matched[skip:]
        if limit is not None:
            matched = matched[:limit]
        return [collection.model_validate(copy.deepcopy(doc)) for doc in matched]

    async def update_one(
        self,
        collection: type[GenericType],
        query: Mapping[str, Any],
        update: Mapping[str, Any],
    ) -> int:
        for doc in self._docs(collection):
            if self._matches(doc, query):
                self._apply_update(doc, update)
                return 1
        return 0

    async def find_one_and_update(
        self,
        collection: type[GenericType],
        query: Mapping[str, Any],
        update: Mapping[str, Any],
        *,
        sort: Sequence[tuple[str, int]] | None = None,
        return_updated: bool = True,
    ) -> GenericType | None:
        matched = [doc for doc in self._docs(collection) if self._matches(doc, query)]
        matched = self._sort_docs(matched, sort)
        if not matched:
            return None
        doc = matched[0]
        before = copy.deepcopy(doc)
        self._apply_update(doc, update)
        chosen = doc if return_updated else before
        return collection.model_validate(copy.deepcopy(chosen))

    async def upsert_one(
        self,
        collection: type[GenericType],
        query: Mapping[str, Any],
        update: Mapping[str, Any],
    ) -> Any | None:
        for doc in self._docs(collection):
            if self._matches(doc, query):
                self._apply_update(doc, update)
                return None
        doc = {k: v for k, v in query.items() if not str(k).startswith("$")}
        self._apply_update(doc, update)
        self._docs(collection).append(doc)
        return doc.get("_id")

    async def delete_one(self, collection: type[GenericType], query: Mapping[str, Any]) -> int:
        docs = self._docs(collection)
        for i, doc in enumerate(docs):
            if self._matches(doc, query):
                del docs[i]
                return 1
        return 0

    async def delete_many(self, collection: type[GenericType], query: Mapping[str, Any]) -> int:
        docs = self._docs(collection)
        kept = [doc for doc in docs if not self._matches(doc, query)]
        removed = len(docs) - len(kept)
        docs[:] = kept
        return removed
