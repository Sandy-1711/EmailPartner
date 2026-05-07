from typing import AsyncGenerator, TypeVar

from pydantic import BaseModel

from app.infrastructure.llm.providers import GeminiProvider

GenericType = TypeVar("GenericType", bound=BaseModel)

class LLMManager:
    _providers: dict[str, GeminiProvider] = {}

    @classmethod
    async def initiate(cls) -> None:
        cls._get_provider("gemini")

    @classmethod
    def _get_provider(cls, provider: str) -> GeminiProvider:
        name = provider.strip().lower()
        if name != "gemini":
            raise ValueError(f"Unsupported LLM provider: {provider}")
        if name not in cls._providers:
            cls._providers[name] = GeminiProvider()
        return cls._providers[name]

    @classmethod
    async def generate_text_as_stream(
        cls, prompt: str, system_instructions: str, provider: str, model: str
    ) -> AsyncGenerator[str, None]:
        llm = cls._get_provider(provider)
        async for chunk in llm.generate_text_as_stream(
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
        provider: str = "gemini",
    ) -> GenericType:
        llm = cls._get_provider(provider)
        response = await llm.generate_structured_output(
            prompt=prompt,
            system_instructions=system_instructions,
            model=model,
            response_model=response_model,
        )
        return response
    