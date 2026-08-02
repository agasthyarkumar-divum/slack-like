import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ChannelMember, Message, MessageRead, Reaction

MESSAGE_LOAD_OPTIONS = (selectinload(Message.attachments), selectinload(Message.reactions))


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
    #
    # populate_existing=True matters whenever this is a *re-fetch* of a
    # message whose relationships were already touched earlier in the same
    # request (e.g. react_to_message loads it once via _require_message
    # before toggling, then again after) — without it, selectinload silently
    # no-ops on a relationship that's already populated (even an empty list
    # counts as "populated"), so a collection loaded before a write stays
    # stale instead of picking up the change.
    result = await db.execute(
        select(Message)
        .where(Message.id == message_id)
        .options(*MESSAGE_LOAD_OPTIONS)
        .execution_options(populate_existing=True)
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
    # reply_to_id IS NULL excludes thread replies — those only ever surface via
    # list_replies_for_message, never inline in the main timeline.
    query = (
        select(Message)
        .where(
            Message.channel_id == channel_id,
            Message.is_deleted.is_(False),
            Message.reply_to_id.is_(None),
        )
        .options(*MESSAGE_LOAD_OPTIONS)
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


async def list_replies_for_message(
    db: AsyncSession,
    *,
    parent_id: uuid.UUID,
    limit: int,
    cursor: tuple[datetime, uuid.UUID] | None,
) -> list[Message]:
    """Oldest-first (thread reading order), keyset-paginated forward via
    `created_at > cursor` — the mirror image of the main list's DESC paging.
    """
    query = (
        select(Message)
        .where(Message.reply_to_id == parent_id, Message.is_deleted.is_(False))
        .options(*MESSAGE_LOAD_OPTIONS)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .limit(limit)
    )
    if cursor is not None:
        cursor_created_at, cursor_id = cursor
        query = query.where(
            or_(
                Message.created_at > cursor_created_at,
                and_(Message.created_at == cursor_created_at, Message.id > cursor_id),
            )
        )
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_replies_for_messages(
    db: AsyncSession, *, message_ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[int, datetime | None]]:
    """message_id -> (reply_count, last_reply_at) for a batch of (potential)
    parent messages — one query instead of N, used to annotate MessageOut.
    """
    if not message_ids:
        return {}
    result = await db.execute(
        select(Message.reply_to_id, func.count(Message.id), func.max(Message.created_at))
        .where(Message.reply_to_id.in_(message_ids), Message.is_deleted.is_(False))
        .group_by(Message.reply_to_id)
    )
    return {row[0]: (row[1], row[2]) for row in result.all()}


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


async def count_unread_by_channel(db: AsyncSession, user_id: uuid.UUID) -> dict[uuid.UUID, int]:
    """channel_id -> count of that user's unread messages in it (their own
    messages don't count, and neither do ones they've already read). Powers
    the Home screen's per-channel unread badges.
    """
    result = await db.execute(
        select(Message.channel_id, func.count(Message.id))
        .join(
            ChannelMember,
            and_(ChannelMember.channel_id == Message.channel_id, ChannelMember.user_id == user_id),
        )
        .outerjoin(
            MessageRead,
            and_(MessageRead.message_id == Message.id, MessageRead.user_id == user_id),
        )
        .where(
            Message.is_deleted.is_(False),
            Message.sender_id != user_id,
            MessageRead.message_id.is_(None),
        )
        .group_by(Message.channel_id)
    )
    return {row[0]: row[1] for row in result.all()}


async def mark_read(db: AsyncSession, *, message_id: uuid.UUID, user_id: uuid.UUID) -> datetime:
    existing = await db.get(MessageRead, {"message_id": message_id, "user_id": user_id})
    read_at = datetime.now(timezone.utc)
    if existing is not None:
        existing.read_at = read_at
    else:
        db.add(MessageRead(message_id=message_id, user_id=user_id, read_at=read_at))
    await db.flush()
    return read_at
