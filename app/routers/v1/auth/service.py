from fastapi import APIRouter
router = APIRouter()

# 1. Signup
# 2. Connect Gmail
# 3. Delete Account
@router.post("/signup")
async def signup():
    pass

@router.post("/connect-gmail")
async def connect_gmail():
    pass

@router.post("/delete-account")
async def delete_account():
    pass