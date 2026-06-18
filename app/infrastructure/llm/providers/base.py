from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import TypeVar

from pydantic import BaseModel

GenericType = TypeVar("GenericType", bound=BaseModel)


class LLMProvider(ABC):
    @abstractmethod
    async def generate_structured_output(
        self,
        prompt: str,
        model: str,
        system_instructions: str,
        response_model: type[GenericType],
    ) -> GenericType:
        ...

    @abstractmethod
    def generate_text_as_stream(
        self,
        prompt: str,
        model: str,
        system_instructions: str,
    ) -> AsyncGenerator[str]:
        ...

    @abstractmethod
    async def synthesize_speech(
        self,
        text: str,
        model: str,
        voice: str,
    ) -> bytes:
        """Render ``text`` as spoken audio and return playable WAV bytes."""
        ...
