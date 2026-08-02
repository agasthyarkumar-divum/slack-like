import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.modules.auth import repository as auth_repository
from app.modules.auth.dependencies import get_current_user
from app.modules.users.schemas import UserOut, UserSettingsUpdate

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


@router.patch(
    "/me",
    response_model=UserOut,
    summary="Update the current user's settings",
    description="Currently just the notification preference (Settings screen's "
    "radio group) — profile fields aren't editable via this endpoint.",
    responses={401: {"description": "Missing, invalid, or expired access token."}},
)
async def update_me(
    payload: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    current_user.notification_preference = payload.notification_preference
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get(
    "/{user_id}",
    response_model=UserOut,
    summary="Get a user's profile",
    description="Public profile lookup by id — used to resolve display names "
    "for message senders, typing indicators, and DM titles.",
    responses={
        401: {"description": "Missing, invalid, or expired access token."},
        404: {"description": "User not found."},
    },
)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    user = await auth_repository.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    return user
