from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from httpx import AsyncClient

from app.config.settings import settings
from app.dependencies import get_db_manager, get_http_client
from app.infrastructure.db.main import DBManager
from app.infrastructure.security.crypto import CryptoManager
from app.services.watch.renewal import WatchRenewalService

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if settings.admin_token is None:
        raise HTTPException(status_code=403, detail="Admin endpoints disabled")
    if x_admin_token != settings.admin_token.get_secret_value():
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.post("/watch/renew", dependencies=[Depends(_require_admin)])
async def renew_watches(
    db_manager: DBManager = Depends(get_db_manager),
    http_client: AsyncClient = Depends(get_http_client),
) -> dict[str, int]:
    crypto = CryptoManager.from_secret(
        settings.encryption_master_key.get_secret_value(), settings.encryption_key_id
    )
    service = WatchRenewalService(db_manager, http_client, crypto, settings)
    renewed = await service.renew_expiring(
        threshold=timedelta(hours=settings.watch_renew_threshold_hours)
    )
    return {"renewed": renewed}
