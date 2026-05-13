from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncGenerator, TypeVar

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
    ) -> AsyncGenerator[str, None]:
        ...
