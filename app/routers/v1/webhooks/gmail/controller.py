from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/")
async def handle_gmail_webhook(request: Request):
    return {"message": "Gmail webhook received"}