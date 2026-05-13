from __future__ import annotations

from app.infrastructure.images.providers import GeminiImageProvider, ImageProvider


def build_image_provider(*, provider: str, api_key: str) -> ImageProvider:
    name = provider.strip().lower()
    if name == "gemini":
        return GeminiImageProvider(api_key=api_key)
    raise ValueError(f"Unsupported image provider: {provider}")
