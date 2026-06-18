from __future__ import annotations

from app.infrastructure.embeddings.providers import EmbeddingProvider, GeminiEmbeddingProvider


def build_embedding_provider(*, provider: str, api_key: str, model: str) -> EmbeddingProvider:
    name = provider.strip().lower()
    if name == "gemini":
        return GeminiEmbeddingProvider(api_key=api_key, model=model)
    raise ValueError(f"Unsupported embedding provider: {provider}")
