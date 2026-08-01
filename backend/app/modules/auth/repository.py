"""Direct DB access for the `users` and `sessions` tables — the only layer
that touches an AsyncSession directly (architecture.md §4's router -> service
-> repository pattern).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Role, Session, User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    result = await db.execute(select(Role).where(Role.name == name))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    hashed_password: str,
    display_name: str,
    role_id: uuid.UUID | None,
) -> User:
    user = User(
        email=email, hashed_password=hashed_password, display_name=display_name, role_id=role_id
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def create_session(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    refresh_token_hash: str,
    expires_at: datetime,
    device_info: dict | None = None,
) -> Session:
    session_row = Session(
        user_id=user_id,
        refresh_token_hash=refresh_token_hash,
        expires_at=expires_at,
        device_info=device_info,
    )
    db.add(session_row)
    await db.flush()
    await db.refresh(session_row)
    return session_row


async def get_session_by_token_hash(db: AsyncSession, token_hash: str) -> Session | None:
    result = await db.execute(select(Session).where(Session.refresh_token_hash == token_hash))
    return result.scalar_one_or_none()


async def revoke_session(db: AsyncSession, session_row: Session) -> None:
    session_row.revoked_at = datetime.now(timezone.utc)
    await db.flush()


async def revoke_all_sessions_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(Session)
        .where(Session.user_id == user_id, Session.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
