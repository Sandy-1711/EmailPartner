from __future__ import annotations

from typing import AsyncGenerator, TypeVar

from pydantic import BaseModel

from app.infrastructure.images.providers.base import GeneratedImage, ImageProvider
from app.infrastructure.llm.providers.base import LLMProvider

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
    ) -> AsyncGenerator[str, None]:
        yield ""

    async def synthesize_speech(self, text: str, model: str, voice: str) -> bytes:
        if self.tts_error is not None:
            raise self.tts_error
        self.tts_calls.append((text, model, voice))
        return b"RIFF-fake-wav"


class FakeImage(ImageProvider):
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    async def generate(
        self, prompt: str, model: str, size: tuple[int, int]
    ) -> GeneratedImage:
        if self.error is not None:
            raise self.error
        return GeneratedImage(data=b"png-bytes", mime_type="image/png")


class FakeStorage:
    def __init__(self) -> None:
        self.blobs: dict[str, tuple[bytes, str]] = {}

    async def put(self, key: str, data: bytes, mime: str) -> str:
        self.blobs[key] = (data, mime)
        return f"mem://{key}"
