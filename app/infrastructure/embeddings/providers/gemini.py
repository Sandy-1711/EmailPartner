from __future__ import annotations

from google import genai
from google.genai.client import AsyncClient

from app.infrastructure.embeddings.providers.base import EmbeddingProvider


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client: AsyncClient = genai.Client(api_key=api_key).aio
        self._model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._client.models.embed_content(model=self._model, contents=texts)  # type: ignore[arg-type]
        return [list(embedding.values or []) for embedding in (response.embeddings or [])]
