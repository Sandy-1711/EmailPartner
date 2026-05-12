from typing import AsyncGenerator, AsyncIterable

from google import genai
from app.config.settings import settings
from google.genai import types
from google.genai.client import AsyncClient
from pydantic import BaseModel
from typing import TypeVar

GenericType = TypeVar("GenericType", bound=BaseModel)


class GeminiProvider:

    def __init__(self):
        self.client: AsyncClient = genai.Client(
            api_key=settings.gemini_api_key.get_secret_value()
        ).aio

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
        ] = await self.client.models.generate_content_stream(  # type: ignore
            model=model, contents=prompt, config=config
        )

        chunk: types.GenerateContentResponse
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

        response: GenericType = await self.client.models.generate_content( # type: ignore
            model=model,
            contents=prompt,
            config=config,
        )
        return response