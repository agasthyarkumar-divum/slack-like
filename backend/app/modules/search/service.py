"""Postgres FTS search (architecture.md §6) — reuses the search_vector columns,
GIN indexes, and BEFORE INSERT/UPDATE triggers built in Phase 2 (the migration,
not the ORM — see db/models comments). Each search type is scoped to what the
current user is allowed to see; nothing here bypasses channel membership.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Attachment, Channel, ChannelMember, Message, User

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def _clamp(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))


async def search_messages(
    db: AsyncSession, *, user_id: uuid.UUID, query: str, limit: int
) -> list[Message]:
    tsquery = func.plainto_tsquery("english", query)
    rank = func.ts_rank(Message.search_vector, tsquery)
    result = await db.execute(
        select(Message)
        .join(ChannelMember, ChannelMember.channel_id == Message.channel_id)
        .where(
            ChannelMember.user_id == user_id,
            Message.is_deleted.is_(False),
            Message.search_vector.op("@@")(tsquery),
        )
        .options(selectinload(Message.attachments))
        .order_by(rank.desc())
        .limit(_clamp(limit))
    )
    return list(result.scalars().all())


async def search_users(db: AsyncSession, *, query: str, limit: int) -> list[User]:
    # Company directory — not membership-scoped; any authenticated user can
    # look up any other employee, same as GET /users?search=.
    tsquery = func.plainto_tsquery("english", query)
    rank = func.ts_rank(User.search_vector, tsquery)
    result = await db.execute(
        select(User)
        .where(User.search_vector.op("@@")(tsquery), User.is_active.is_(True))
        .order_by(rank.desc())
        .limit(_clamp(limit))
    )
    return list(result.scalars().all())


async def search_channels(
    db: AsyncSession, *, user_id: uuid.UUID, query: str, limit: int
) -> list[Channel]:
    tsquery = func.plainto_tsquery("english", query)
    rank = func.ts_rank(Channel.search_vector, tsquery)
    result = await db.execute(
        select(Channel)
        .join(ChannelMember, ChannelMember.channel_id == Channel.id)
        .where(ChannelMember.user_id == user_id, Channel.search_vector.op("@@")(tsquery))
        .order_by(rank.desc())
        .limit(_clamp(limit))
    )
    return list(result.scalars().all())


async def search_files(
    db: AsyncSession, *, user_id: uuid.UUID, query: str, limit: int
) -> list[Attachment]:
    # attachments has no search_vector/FTS column (architecture.md §5) — a
    # filename substring match is the pragmatic stand-in rather than adding a
    # new column not in the spec.
    result = await db.execute(
        select(Attachment)
        .join(Message, Message.id == Attachment.message_id)
        .join(ChannelMember, ChannelMember.channel_id == Message.channel_id)
        .where(ChannelMember.user_id == user_id, Attachment.file_name.ilike(f"%{query}%"))
        .order_by(Attachment.created_at.desc())
        .limit(_clamp(limit))
    )
    return list(result.scalars().all())
