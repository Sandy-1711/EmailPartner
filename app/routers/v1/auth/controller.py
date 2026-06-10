from __future__ import annotations

from urllib.parse import quote

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import RedirectResponse

from app.config.settings import settings
from app.dependencies import (
    get_auth_service,
    get_db_manager,
    get_session_user_id,
)
from app.infrastructure.db.main import DBManager
from app.models.api.auth import (
    DeleteAccountRequest,
    GoogleSignInStartResponse,
    MeResponse,
)
from app.routers.v1.auth.service import AuthService
from app.services.storage import GmailAccountStore, UserStore

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google/start", response_model=GoogleSignInStartResponse)
async def google_signin_start(
    client: str = Query(default="web", pattern="^(web|mobile)$"),
    service: AuthService = Depends(get_auth_service),
) -> GoogleSignInStartResponse:
    return await service.google_signin_start(client=client)


@router.get("/google/callback")
async def google_signin_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    service: AuthService = Depends(get_auth_service),
) -> RedirectResponse:
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    _, session_token, client = await service.handle_google_signin_callback(
        code=code, state=state
    )
    if client == "mobile":
        # Hand the session token to the app via its deep link; no cookie needed.
        return RedirectResponse(
            url=f"emailpartner://auth?token={quote(session_token)}", status_code=303
        )
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )
    return response


@router.get("/me", response_model=MeResponse)
async def me(
    db_manager: DBManager = Depends(get_db_manager),
    user_id: str | None = Depends(get_session_user_id),
) -> MeResponse:
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        user_oid = ObjectId(user_id)
    except InvalidId as exc:
        raise HTTPException(status_code=401, detail="Invalid session payload") from exc

    user = await UserStore(db_manager).get_by_id(user_oid)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    gmail_account = await GmailAccountStore(db_manager).get_by_user_id(user_oid)
    return MeResponse(
        user_id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        picture_url=user.picture_url,
        gmail_connected=gmail_account is not None,
    )


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(settings.session_cookie_name)
    return {"status": "ok"}


@router.post("/delete-account")
async def delete_account(
    payload: DeleteAccountRequest, service: AuthService = Depends(get_auth_service)
) -> dict[str, str]:
    await service.delete_account(payload)
    return {"status": "deleted"}
