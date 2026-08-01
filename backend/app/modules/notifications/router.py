import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.notifications import service
from app.modules.notifications.schemas import NotificationListResponse, NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List my notifications",
    description="Newest first, plus an unread count for the in-app badge (architecture.md §9).",
    responses={401: {"description": "Missing or invalid access token."}},
)
async def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    items, unread_count = await service.list_my_notifications(db, user_id=current_user.id, limit=limit)
    return NotificationListResponse(
        items=[NotificationOut.model_validate(n) for n in items], unread_count=unread_count
    )


@router.post(
    "/{notification_id}/read",
    response_model=NotificationOut,
    summary="Mark one notification read",
    responses={
        401: {"description": "Missing or invalid access token."},
        404: {"description": "Notification not found."},
    },
)
async def mark_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationOut:
    notification = await service.mark_read(db, notification_id=notification_id, user_id=current_user.id)
    return NotificationOut.model_validate(notification)


@router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark all notifications read",
    responses={401: {"description": "Missing or invalid access token."}},
)
async def mark_all_read(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> None:
    await service.mark_all_read(db, user_id=current_user.id)
