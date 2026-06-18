from __future__ import annotations

import base64
import os

# Must be set before any app import: app.config.settings instantiates Settings
# at import time.
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("OAUTH_CLIENT_ID", "test-client")
os.environ.setdefault("OAUTH_CLIENT_SECRET", "test-secret")
os.environ.setdefault("OAUTH_REDIRECT_URI", "http://localhost:8000/v1/auth/google/callback")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB_NAME", "emailpartner_test")
os.environ.setdefault(
    "ENCRYPTION_MASTER_KEY", base64.urlsafe_b64encode(b"0" * 32).decode("ascii")
)
os.environ.setdefault("OAUTH_STATE_SECRET", "state-secret")
os.environ.setdefault("SESSION_SECRET", "session-secret")
os.environ.setdefault("GMAIL_WATCH_TOPIC", "projects/test/topics/gmail")
os.environ.setdefault("ENABLE_BACKGROUND_JOBS", "false")

import pytest

from app.config.settings import Settings
from app.infrastructure.db.main import DBManager
from tests.inmemory_db import InMemoryDocumentDB


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def db_manager() -> DBManager:
    return DBManager(InMemoryDocumentDB())


@pytest.fixture
def app_settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]
