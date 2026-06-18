from __future__ import annotations

import hashlib
import math
from collections.abc import AsyncGenerator
from typing import TypeVar

from pydantic import BaseModel

from app.infrastructure.embeddings.providers.base import EmbeddingProvider
from app.infrastructure.images.providers.base import GeneratedImage, ImageProvider
from app.infrastructure.llm.providers.base import LLMProvider
from app.infrastructure.vectorstore.providers.base import VectorHit, VectorRecord, VectorStore

GenericType = TypeVar("GenericType", bound=BaseModel)


class FakeLLM(LLMProvider):
    def __init__(
        self,
        result: BaseModel | None = None,
        summary_error: Exception | None = None,
        tts_error: Exception | None = None,
    ) -> None:
        self.result = result
        self.summary_error = summary_error
        self.tts_error = tts_error
        self.tts_calls: list[tuple[str, str, str]] = []

    async def generate_structured_output(
        self,
        prompt: str,
        model: str,
        system_instructions: str,
        response_model: type[GenericType],
    ) -> GenericType:
        if self.summary_error is not None:
            raise self.summary_error
        assert isinstance(self.result, response_model)
        return self.result

    async def generate_text_as_stream(
        self,
        prompt: str,
        model: str,
        system_instructions: str,
    ) -> AsyncGenerator[str]:
        yield ""

    async def synthesize_speech(self, text: str, model: str, voice: str) -> bytes:
        if self.tts_error is not None:
            raise self.tts_error
        self.tts_calls.append((text, model, voice))
        return b"RIFF-fake-wav"


class FakeImage(ImageProvider):
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, str, tuple[int, int]]] = []

    async def generate(
        self, prompt: str, model: str, size: tuple[int, int]
    ) -> GeneratedImage:
        self.calls.append((prompt, model, size))
        if self.error is not None:
            raise self.error
        return GeneratedImage(data=b"png-bytes", mime_type="image/png")


class FakeEmbedder(EmbeddingProvider):
    """Deterministic bag-of-words hashing embedder so similarity reflects word
    overlap (a query sharing words with a doc ranks high). No network."""

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [self._vector(t) for t in texts]

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for word in text.lower().split():
            idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim
            vec[idx] += 1.0
        return vec


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class FakeVectorStore(VectorStore):
    """In-memory cosine store with per-user filtering — matches the Qdrant
    impl's contract without a server."""

    def __init__(self) -> None:
        self.records: dict[str, VectorRecord] = {}

    async def ensure_collection(self, dim: int) -> None:
        return None

    async def upsert(self, records: list[VectorRecord]) -> None:
        for record in records:
            self.records[record.id] = record

    async def search(self, vector: list[float], *, user_id: str, limit: int) -> list[VectorHit]:
        hits = [
            VectorHit(id=r.id, score=_cosine(vector, r.vector), payload=r.payload)
            for r in self.records.values()
            if r.payload.get("user_id") == user_id
        ]
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:limit]

    async def delete(self, ids: list[str]) -> None:
        for id_ in ids:
            self.records.pop(id_, None)


class FakeStorage:
    def __init__(self) -> None:
        self.blobs: dict[str, tuple[bytes, str]] = {}

    async def put(self, key: str, data: bytes, mime: str) -> str:
        self.blobs[key] = (data, mime)
        return f"mem://{key}"
