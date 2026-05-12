from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedImage:
    data: bytes
    mime_type: str


class ImageProvider(ABC):
    @abstractmethod
    async def generate(
        self, prompt: str, model: str, size: tuple[int, int]
    ) -> GeneratedImage:
        ...
