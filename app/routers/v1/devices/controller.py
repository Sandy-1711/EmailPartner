from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_db_manager, get_session_user_id
from app.infrastructure.db.main import DBManager
from app.models.api.devices import RegisterDeviceRequest
from app.services.storage import DeviceTokenStore

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("")
async def register_device(
    body: RegisterDeviceRequest,
    db_manager: DBManager = Depends(get_db_manager),
    session_user_id: str | None = Depends(get_session_user_id),
) -> dict[str, str]:
    """Register the caller's FCM token so the worker can push ready cards to it."""
    if session_user_id is None:
        raise HTTPException(status_code=401, detail="Sign in required")
    await DeviceTokenStore(db_manager).register(
        ObjectId(session_user_id), body.token, body.platform
    )
    return {"status": "registered"}
