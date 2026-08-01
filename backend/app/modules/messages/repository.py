import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Message, MessageRead, Reaction


async def create_message(
    db: AsyncSession,
    *,
    channel_id: uuid.UUID,
    sender_id: uuid.UUID,
    content: str | None,
    reply_to_id: uuid.UUID | None = None,
    forwarded_from_id: uuid.UUID | None = None,
) -> Message:
    message = Message(
        channel_id=channel_id,
        sender_id=sender_id,
        content=content,
        reply_to_id=reply_to_id,
        forwarded_from_id=forwarded_from_id,
    )
    db.add(message)
    await db.flush()
    # Restricted to column attributes: an unrestricted refresh() also tries to
    # reload the `attachments` relationship, which hits a MissingGreenlet error
    # in this async context (refreshing relationships takes a different, and
    # here broken, internal path than the plain lazy-load fallback).
    await db.refresh(message, attribute_names=["id", "created_at", "is_pinned", "is_edited", "is_deleted"])
    return message


async def get_message_by_id(db: AsyncSession, message_id: uuid.UUID) -> Message | None:
    # Not db.get(): when the object is already in the session's identity map
    # (e.g. just created in this same request), get() returns the cached
    # instance as-is and *skips* applying eager-load options entirely, leaving
    # `attachments` unloaded. An explicit select() always re-applies them.
    result = await db.execute(
        select(Message).where(Message.id == message_id).options(selectinload(Message.attachments))
    )
    return result.scalar_one_or_none()


async def list_messages_for_channel(
    db: AsyncSession,
    *,
    channel_id: uuid.UUID,
    limit: int,
    cursor: tuple[datetime, uuid.UUID] | None,
) -> list[Message]:
    # Composite (created_at, id) DESC keyset pagination — correct even when two
    # messages share a created_at timestamp, unlike a plain `created_at < cursor`
    # cutoff. Uses the idx_messages_channel_created index (architecture.md §5).
    query = (
        select(Message)
        .where(Message.channel_id == channel_id, Message.is_deleted.is_(False))
        .options(selectinload(Message.attachments))
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit)
    )
    if cursor is not None:
        cursor_created_at, cursor_id = cursor
        query = query.where(
            or_(
                Message.created_at < cursor_created_at,
                and_(Message.created_at == cursor_created_at, Message.id < cursor_id),
            )
        )
    result = await db.execute(query)
    return list(result.scalars().all())


async def toggle_reaction(
    db: AsyncSession, *, message_id: uuid.UUID, user_id: uuid.UUID, emoji: str
) -> bool:
    """Returns True if a reaction was added, False if an existing one was removed."""
    existing = await db.get(Reaction, {"message_id": message_id, "user_id": user_id, "emoji": emoji})
    if existing is not None:
        await db.delete(existing)
        await db.flush()
        return False
    db.add(Reaction(message_id=message_id, user_id=user_id, emoji=emoji))
    await db.flush()
    return True


async def mark_read(db: AsyncSession, *, message_id: uuid.UUID, user_id: uuid.UUID) -> datetime:
    existing = await db.get(MessageRead, {"message_id": message_id, "user_id": user_id})
    read_at = datetime.now(timezone.utc)
    if existing is not None:
        existing.read_at = read_at
    else:
        db.add(MessageRead(message_id=message_id, user_id=user_id, read_at=read_at))
    await db.flush()
    return read_at
