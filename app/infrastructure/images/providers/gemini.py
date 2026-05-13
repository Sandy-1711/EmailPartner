from __future__ import annotations

from google import genai
from google.genai import types

from app.infrastructure.images.providers.base import GeneratedImage, ImageProvider


def _aspect_ratio(size: tuple[int, int]) -> str:
    w, h = size
    if w <= 0 or h <= 0:
        return "1:1"
    ratio = w / h
    candidates = {
        "1:1": 1.0,
        "16:9": 16 / 9,
        "9:16": 9 / 16,
        "4:3": 4 / 3,
        "3:4": 3 / 4,
    }
    return min(candidates, key=lambda k: abs(candidates[k] - ratio))


class GeminiImageProvider(ImageProvider):
    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key).aio

    async def generate(
        self, prompt: str, model: str, size: tuple[int, int]
    ) -> GeneratedImage:
        if model.startswith("imagen"):
            return await self._generate_imagen(prompt, model, size)
        return await self._generate_gemini_image(prompt, model)

    async def _generate_imagen(
        self, prompt: str, model: str, size: tuple[int, int]
    ) -> GeneratedImage:
        response = await self._client.models.generate_images(
            model=model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=_aspect_ratio(size),
            ),
        )
        generated = (response.generated_images or [None])[0]
        if generated is None or generated.image is None or generated.image.image_bytes is None:
            raise ValueError(f"Imagen returned no image (model={model})")
        return GeneratedImage(
            data=generated.image.image_bytes,
            mime_type=generated.image.mime_type or "image/png",
        )

    async def _generate_gemini_image(self, prompt: str, model: str) -> GeneratedImage:
        response = await self._client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        for candidate in response.candidates or []:
            content = candidate.content
            if content is None:
                continue
            for part in content.parts or []:
                inline = getattr(part, "inline_data", None)
                if inline is not None and inline.data:
                    return GeneratedImage(
                        data=inline.data,
                        mime_type=inline.mime_type or "image/png",
                    )
        raise ValueError(f"Gemini returned no image (model={model})")
