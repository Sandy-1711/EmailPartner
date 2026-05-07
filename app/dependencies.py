from __future__ import annotations

from fastapi import Request
from httpx import AsyncClient

from app.infrastructure.db.main import DBManager


def get_db_manager(request: Request) -> DBManager:
    db_manager = getattr(request.app.state, "db_manager", None)
    if db_manager is None:
        raise RuntimeError("Database manager not initialized")
    return db_manager


def get_http_client(request: Request) -> AsyncClient:
    client = getattr(request.app.state, "http_client", None)
    if client is None:
        raise RuntimeError("HTTP client not initialized")
    return client
