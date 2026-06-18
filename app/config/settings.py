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
    watch_renew_interval_seconds: Annotated[
        int, Field(validation_alias="WATCH_RENEW_INTERVAL_SECONDS", default=60 * 60)
    ]
    watch_renew_threshold_hours: Annotated[
        int, Field(validation_alias="WATCH_RENEW_THRESHOLD_HOURS", default=24)
    ]
    enable_background_jobs: Annotated[
        bool, Field(validation_alias="ENABLE_BACKGROUND_JOBS", default=True)
    ]

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
                "https://www.googleapis.com/auth/gmail.modify",
            ],
        ),
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
    # Backfill flood guard: only process emails received within this many
    # seconds of now. When the backend comes back online after a gap, Gmail's
    # history.list (from a stale historyId) returns the whole backlog of
    # messagesAdded — without this, every one would run the LLM + TTS pipeline
    # and burn credits. 0 disables the guard (process everything). Default 1h.
    gmail_max_email_age_seconds: Annotated[
        int, Field(validation_alias="GMAIL_MAX_EMAIL_AGE_SECONDS", default=3600)
    ]
    # Push notifications (FCM HTTP v1). Path to the Firebase service-account
    # JSON (the admin SDK key). When unset, push is disabled and the worker
    # simply skips it. The project id is read from the file itself.
    firebase_credentials_file: Annotated[
        str | None, Field(validation_alias="FIREBASE_CREDENTIALS_FILE", default=None)
    ]
    enable_push_notifications: Annotated[
        bool, Field(validation_alias="ENABLE_PUSH_NOTIFICATIONS", default=True)
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
        str, Field(validation_alias="SUMMARY_MODEL", default="gemini-3.1-flash-lite")
    ]
    summary_max_body_chars: Annotated[
        int, Field(validation_alias="SUMMARY_MAX_BODY_CHARS", default=8000)
    ]

    tts_model: Annotated[
        str, Field(validation_alias="TTS_MODEL", default="gemini-2.5-flash-preview-tts")
    ]
    tts_voice: Annotated[str, Field(validation_alias="TTS_VOICE", default="Kore")]
    enable_audio_narration: Annotated[
        bool, Field(validation_alias="ENABLE_AUDIO_NARRATION", default=True)
    ]

    pipeline_concurrency: Annotated[
        int, Field(validation_alias="PIPELINE_CONCURRENCY", default=2)
    ]
    pipeline_poll_interval_seconds: Annotated[
        float, Field(validation_alias="PIPELINE_POLL_INTERVAL_SECONDS", default=15.0)
    ]
    pipeline_lease_seconds: Annotated[
        int, Field(validation_alias="PIPELINE_LEASE_SECONDS", default=600)
    ]
    pipeline_max_attempts: Annotated[
        int, Field(validation_alias="PIPELINE_MAX_ATTEMPTS", default=5)
    ]

    # The mobile app uses a procedural MeshGradient, not the generated
    # illustration, so image generation is off by default (it burns image-model
    # credits for an asset nothing displays). The pipeline code path is retained.
    enable_image_generation: Annotated[
        bool, Field(validation_alias="ENABLE_IMAGE_GENERATION", default=False)
    ]
    image_provider: Annotated[
        str, Field(validation_alias="IMAGE_PROVIDER", default="gemini")
    ]
    image_model: Annotated[
        str, Field(validation_alias="IMAGE_MODEL", default="gemini-2.5-flash-image")
    ]
    # Semantic memory (RAG). Off by default — needs a running Qdrant. When on,
    # the pipeline embeds each ready card and upserts it to the vector store, and
    # search uses it. See docs/agentic-architecture.md.
    enable_semantic_memory: Annotated[
        bool, Field(validation_alias="ENABLE_SEMANTIC_MEMORY", default=False)
    ]
    embedding_provider: Annotated[
        str, Field(validation_alias="EMBEDDING_PROVIDER", default="gemini")
    ]
    embedding_model: Annotated[
        str, Field(validation_alias="EMBEDDING_MODEL", default="text-embedding-004")
    ]
    embedding_dim: Annotated[int, Field(validation_alias="EMBEDDING_DIM", default=768)]
    qdrant_url: Annotated[str, Field(validation_alias="QDRANT_URL", default="http://localhost:6333")]
    qdrant_api_key: Annotated[
        SecretStr | None, Field(validation_alias="QDRANT_API_KEY", default=None)
    ]
    qdrant_collection: Annotated[
        str, Field(validation_alias="QDRANT_COLLECTION", default="emails")
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
