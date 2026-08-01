import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Notification


async def create_notification(
    db: AsyncSession, *, user_id: uuid.UUID, type: str, payload: dict
) -> Notification:
    notification = Notification(user_id=user_id, type=type, payload=payload)
    db.add(notification)
    await db.flush()
    await db.refresh(notification)
    return notification


async def get_notification_by_id(db: AsyncSession, notification_id: uuid.UUID) -> Notification | None:
    return await db.get(Notification, notification_id)


async def list_for_user(db: AsyncSession, *, user_id: uuid.UUID, limit: int) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_unread(db: AsyncSession, *, user_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
    )
    return result.scalar_one()


async def mark_read(db: AsyncSession, notification: Notification) -> None:
    notification.is_read = True
    await db.flush()


async def mark_all_read(db: AsyncSession, *, user_id: uuid.UUID) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
