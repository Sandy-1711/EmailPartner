from typing import Annotated

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: Annotated[SecretStr, Field(validation_alias="GEMINI_API_KEY")]
    oauth_client_id: Annotated[SecretStr, Field(validation_alias="OAUTH_CLIENT_ID")]
    oauth_client_secret: Annotated[SecretStr, Field(validation_alias="OAUTH_CLIENT_SECRET")]
    oauth_redirect_uri: Annotated[str, Field(validation_alias="OAUTH_REDIRECT_URI")]

    mongo_uri: Annotated[SecretStr, Field(validation_alias="MONGO_URI")]
    mongo_db_name: Annotated[str, Field(validation_alias="MONGO_DB_NAME")]

    encryption_master_key: Annotated[SecretStr, Field(validation_alias="ENCRYPTION_MASTER_KEY")]
    encryption_key_id: Annotated[str, Field(validation_alias="ENCRYPTION_KEY_ID", default="v1")]
    oauth_state_secret: Annotated[SecretStr, Field(validation_alias="OAUTH_STATE_SECRET")]
    oauth_state_ttl_seconds: Annotated[int, Field(validation_alias="OAUTH_STATE_TTL_SECONDS", default=900)]
    session_secret: Annotated[SecretStr, Field(validation_alias="SESSION_SECRET")]
    session_ttl_seconds: Annotated[int, Field(validation_alias="SESSION_TTL_SECONDS", default=60 * 60 * 24 * 14)]
    session_cookie_name: Annotated[str, Field(validation_alias="SESSION_COOKIE_NAME", default="ep_session")]
    session_cookie_secure: Annotated[bool, Field(validation_alias="SESSION_COOKIE_SECURE", default=False)]
    admin_token: Annotated[SecretStr | None, Field(validation_alias="ADMIN_TOKEN", default=None)]

    google_oauth_authorize_url: Annotated[
        str, Field(validation_alias="GOOGLE_OAUTH_AUTHORIZE_URL", default="https://accounts.google.com/o/oauth2/v2/auth")
    ]
    google_oauth_token_url: Annotated[
        str, Field(validation_alias="GOOGLE_OAUTH_TOKEN_URL", default="https://oauth2.googleapis.com/token")
    ]
    oauth_scopes: Annotated[
        list[str],
        Field(
            validation_alias="OAUTH_SCOPES",
            default_factory=lambda: [
                "openid",
                "email",
                "profile",
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.metadata",
                "https://www.googleapis.com/auth/gmail.modify",
            ],
        ),
    ]
    google_signin_redirect_uri: Annotated[
        str | None,
        Field(validation_alias="GOOGLE_SIGNIN_REDIRECT_URI", default=None),
    ]
    gmail_api_base_url: Annotated[
        str, Field(validation_alias="GMAIL_API_BASE_URL", default="https://gmail.googleapis.com/gmail/v1")
    ]
    gmail_watch_topic: Annotated[str, Field(validation_alias="GMAIL_WATCH_TOPIC")]
    gmail_watch_label_ids: Annotated[
        list[str], Field(validation_alias="GMAIL_WATCH_LABEL_IDS", default_factory=list)
    ]
    gmail_watch_history_types: Annotated[
        list[str],
        Field(
            validation_alias="GMAIL_WATCH_HISTORY_TYPES",
            default_factory=lambda: ["messageAdded"],
        ),
    ]
    pubsub_verification_token: Annotated[
        SecretStr | None, Field(validation_alias="PUBSUB_VERIFICATION_TOKEN", default=None)
    ]
    token_refresh_skew_seconds: Annotated[
        int, Field(validation_alias="TOKEN_REFRESH_SKEW_SECONDS", default=300)
    ]
    http_timeout_seconds: Annotated[
        float, Field(validation_alias="HTTP_TIMEOUT_SECONDS", default=10.0)
    ]

    summary_model: Annotated[
        str, Field(validation_alias="SUMMARY_MODEL", default="gemini-2.5-flash")
    ]
    summary_max_body_chars: Annotated[
        int, Field(validation_alias="SUMMARY_MAX_BODY_CHARS", default=8000)
    ]

    image_provider: Annotated[
        str, Field(validation_alias="IMAGE_PROVIDER", default="gemini")
    ]
    image_model: Annotated[
        str, Field(validation_alias="IMAGE_MODEL", default="imagen-3.0-generate-001")
    ]
    local_storage_dir: Annotated[
        str, Field(validation_alias="LOCAL_STORAGE_DIR", default="./var/illustrations")
    ]
    local_storage_public_base_url: Annotated[
        str,
        Field(
            validation_alias="LOCAL_STORAGE_PUBLIC_BASE_URL",
            default="http://localhost:8000/static/illustrations",
        ),
    ]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "populate_by_name": True,
        "extra": "ignore",
    }


settings = Settings()  # pyright: ignore[reportCallIssue]
