from __future__ import annotations

import io
import wave
from typing import AsyncGenerator, AsyncIterable, TypeVar

from google import genai
from google.genai import types
from google.genai.client import AsyncClient
from pydantic import BaseModel

from app.infrastructure.llm.providers.base import LLMProvider

GenericType = TypeVar("GenericType", bound=BaseModel)


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str) -> None:
        self._client: AsyncClient = genai.Client(api_key=api_key).aio

    async def generate_text_as_stream(
        self,
        prompt: str,
        model: str,
        system_instructions: str,
    ) -> AsyncGenerator[str, None]:
        config = genai.types.GenerateContentConfig(
            system_instruction=system_instructions,
        )

        response_stream: AsyncIterable[
            types.GenerateContentResponse
        ] = await self._client.models.generate_content_stream(  # type: ignore[arg-type]
            model=model, contents=prompt, config=config
        )

        async for chunk in response_stream:
            if chunk.text is not None:
                yield chunk.text

    async def generate_structured_output(
        self,
        prompt: str,
        model: str,
        system_instructions: str,
        response_model: type[GenericType],
    ) -> GenericType:
        config = genai.types.GenerateContentConfig(
            system_instruction=system_instructions,
            response_mime_type="application/json",
            response_schema=response_model,
        )

        response = await self._client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )

        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, response_model):
            return parsed
        if response.text:
            return response_model.model_validate_json(response.text)
        raise ValueError("Gemini returned no parseable structured output")

    async def synthesize_speech(
        self,
        text: str,
        model: str,
        voice: str,
    ) -> bytes:
        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
        )
        response = await self._client.models.generate_content(
            model=model,
            contents=text,
            config=config,
        )
        pcm = _extract_audio_bytes(response)
        if pcm is None:
            raise ValueError("Gemini TTS returned no audio data")
        return _pcm_to_wav(pcm)


def _extract_audio_bytes(response: types.GenerateContentResponse) -> bytes | None:
    for candidate in response.candidates or []:
        if candidate.content is None:
            continue
        for part in candidate.content.parts or []:
            inline = part.inline_data
            if inline is not None and inline.data:
                return inline.data
    return None


def _pcm_to_wav(
    pcm: bytes, *, channels: int = 1, sample_width: int = 2, rate: int = 24000
) -> bytes:
    """Gemini TTS returns raw 16-bit 24kHz mono PCM; wrap it in a WAV container."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(rate)
        wav.writeframes(pcm)
    return buffer.getvalue()
