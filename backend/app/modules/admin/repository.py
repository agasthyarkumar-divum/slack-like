import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog, Channel, Message, Role, User


async def list_users_with_scope(db: AsyncSession) -> list[tuple[User, str]]:
    result = await db.execute(
        select(User, Role.name).outerjoin(Role, Role.id == User.role_id).order_by(User.created_at.desc())
    )
    return [(user, role_name or "users") for user, role_name in result.all()]


async def get_user_with_scope(db: AsyncSession, user_id: uuid.UUID) -> tuple[User, str] | None:
    result = await db.execute(
        select(User, Role.name).outerjoin(Role, Role.id == User.role_id).where(User.id == user_id)
    )
    row = result.first()
    if row is None:
        return None
    user, role_name = row
    return user, role_name or "users"


async def create_audit_log(
    db: AsyncSession,
    *,
    actor_id: uuid.UUID,
    action: str,
    target_type: str | None,
    target_id: uuid.UUID | None,
    metadata: dict,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id, action=action, target_type=target_type, target_id=target_id, extra_data=metadata
    )
    db.add(entry)
    await db.flush()
    return entry


async def list_audit_logs(db: AsyncSession, *, limit: int) -> list[AuditLog]:
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    return list(result.scalars().all())


async def get_stats(db: AsyncSession) -> dict:
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    active_users = (
        await db.execute(select(func.count()).select_from(User).where(User.is_active.is_(True)))
    ).scalar_one()
    total_channels = (await db.execute(select(func.count()).select_from(Channel))).scalar_one()
    total_messages = (
        await db.execute(select(func.count()).select_from(Message).where(Message.is_deleted.is_(False)))
    ).scalar_one()
    today = datetime.now(timezone.utc).date()
    users_active_today = (
        await db.execute(
            select(func.count()).select_from(User).where(func.date(User.last_seen) == today)
        )
    ).scalar_one()
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_channels": total_channels,
        "total_messages": total_messages,
        "users_active_today": users_active_today,
    }
