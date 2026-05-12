from __future__ import annotations

from app.infrastructure.images.providers import (
    GeminiImageProvider,
    GeneratedImage,
    ImageProvider,
)


class ImageManager:
    _providers: dict[str, ImageProvider] = {}

    @classmethod
    def _get_provider(cls, provider: str) -> ImageProvider:
        name = provider.strip().lower()
        if name not in cls._providers:
            if name == "gemini":
                cls._providers[name] = GeminiImageProvider()
            else:
                raise ValueError(f"Unsupported image provider: {provider}")
        return cls._providers[name]

    @classmethod
    async def generate(
        cls,
        prompt: str,
        *,
        provider: str,
        model: str,
        size: tuple[int, int] = (1024, 1024),
    ) -> GeneratedImage:
        return await cls._get_provider(provider).generate(prompt, model, size)
