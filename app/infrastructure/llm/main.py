from __future__ import annotations

from app.infrastructure.llm.providers import GeminiProvider, LLMProvider


def build_llm_provider(*, provider: str, api_key: str) -> LLMProvider:
    name = provider.strip().lower()
    if name == "gemini":
        return GeminiProvider(api_key=api_key)
    raise ValueError(f"Unsupported LLM provider: {provider}")
