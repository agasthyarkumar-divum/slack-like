from fastapi import APIRouter, Depends

from app.db.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.users.schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get the current user's profile",
    description="Returns the profile of the user identified by the access token "
    "in the Authorization header.",
    responses={401: {"description": "Missing, invalid, or expired access token."}},
)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
