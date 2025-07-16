from fastapi import APIRouter

router = APIRouter()

@router.get("/profile")
async def get_profile():
    return {"message": "Get user profile"}

@router.put("/profile")
async def update_profile():
    return {"message": "Update user profile"}