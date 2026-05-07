from fastapi import APIRouter

from app.routers.v1.auth.controller import router as auth_router
from app.routers.v1.cards.controller import router as cards_router
from app.routers.v1.webhooks.gmail.controller import router as gmail_webhook_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router)
router.include_router(gmail_webhook_router)
router.include_router(cards_router)

__all__ = ["router"]
