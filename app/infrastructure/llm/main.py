from typing import AsyncGenerator
from app.infrastructure.llm.providers import GeminiProvider
from typing import TypeVar
from pydantic import BaseModel

GenericType = TypeVar("GenericType", bound=BaseModel)

class LLMManager:
    _gemini: GeminiProvider
    
    @classmethod
    async def initiate(cls):
        cls._gemini = GeminiProvider()

    @classmethod
    async def generate_text_as_stream(
        cls, prompt: str, system_instructions: str, provider: str, model: str
    ) -> AsyncGenerator[str, None]:
        async for chunk in cls._gemini.generate_text_as_stream(
            prompt=prompt, system_instructions=system_instructions, model=model
        ):
            yield chunk

    @classmethod
    async def generate_structured_output(
        cls,
        prompt: str,
        system_instructions: str,
        model: str,
        response_model: type[GenericType],
    ) -> GenericType:
        response = await cls._gemini.generate_structured_output(
            prompt=prompt,
            system_instructions=system_instructions,
            model=model,
            response_model=response_model,
        )
        return response
    