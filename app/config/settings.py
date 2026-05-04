from pydantic_settings import BaseSettings
from typing import Annotated
from pydantic import Field, SecretStr

class Settings(BaseSettings):

    gemini_api_key: Annotated[SecretStr, Field(validation_alias="GEMINI_API_KEY")]
    oauth_client_id: Annotated[SecretStr, Field(validation_alias="OAUTH_CLIENT_ID")]
    oauth_client_secret: Annotated[SecretStr, Field(validation_alias="OAUTH_CLIENT_SECRET")]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "populate_by_name": True,
    }


settings = Settings()  # pyright: ignore[reportCallIssue]
