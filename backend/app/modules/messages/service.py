import base64
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Message
from app.modules.channels import repository as channels_repository
from app.modules.channels.service import require_membership
from app.modules.files import repository as files_repository
from app.modules.messages import repository
from app.modules.notifications import service as notifications_service
from app.ws.manager import manager

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


async def _broadcast_new(message: Message) -> None:
    await manager.broadcast_to_channel(
        str(message.channel_id),
        {
            "event": "message.new",
            "data": {
                "id": str(message.id),
                "channel_id": str(message.channel_id),
                "sender_id": str(message.sender_id) if message.sender_id else None,
                "content": message.content,
                "reply_to_id": str(message.reply_to_id) if message.reply_to_id else None,
                "forwarded_from_id": str(message.forwarded_from_id)
                if message.forwarded_from_id
                else None,
                "is_pinned": message.is_pinned,
                "is_edited": message.is_edited,
                "created_at": _iso(message.created_at),
                "attachment_ids": [str(a.id) for a in message.attachments],
            },
        },
    )


async def _broadcast_edited(message: Message) -> None:
    await manager.broadcast_to_channel(
        str(message.channel_id),
        {
            "event": "message.edited",
            "data": {
                "id": str(message.id),
                "channel_id": str(message.channel_id),
                "content": message.content,
                "edited_at": _iso(message.edited_at),
            },
        },
    )


async def _broadcast_deleted(message: Message) -> None:
    await manager.broadcast_to_channel(
        str(message.channel_id),
        {"event": "message.deleted", "data": {"id": str(message.id), "channel_id": str(message.channel_id)}},
    )


async def _notify_for_new_message(db: AsyncSession, message: Message) -> None:
    """architecture.md §9: DMs notify every other member unconditionally;
    other channel types only notify users explicitly @mentioned in the text.
    """
    channel = await channels_repository.get_channel_by_id(db, message.channel_id)
    if channel is None or message.sender_id is None:
        return
    members = await channels_repository.list_member_users(db, message.channel_id)

    if channel.type == "dm":
        recipient_ids = {m.id for m in members if m.id != message.sender_id}
        notif_type = "dm"
    else:
        recipient_ids = notifications_service.find_mentioned_user_ids(message.content, members)
        recipient_ids.discard(message.sender_id)
        notif_type = "mention"

    if not recipient_ids:
        return
    payload = {
        "channel_id": str(message.channel_id),
        "message_id": str(message.id),
        "preview": notifications_service.make_preview(message.content),
    }
    for recipient_id in recipient_ids:
        await notifications_service.notify_user(db, user_id=recipient_id, type=notif_type, payload=payload)


def _encode_cursor(message: Message) -> str:
    raw = f"{message.created_at.isoformat()}|{message.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        created_at_str, id_str = raw.split("|")
        return datetime.fromisoformat(created_at_str), uuid.UUID(id_str)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid cursor.") from exc


async def _require_message(db: AsyncSession, message_id: uuid.UUID) -> Message:
    message = await repository.get_message_by_id(db, message_id)
    if message is None or message.is_deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found.")
    return message


async def list_messages(
    db: AsyncSession, *, channel_id: uuid.UUID, user_id: uuid.UUID, cursor: str | None, limit: int
) -> tuple[list[Message], str | None]:
    await require_membership(db, channel_id=channel_id, user_id=user_id)
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    decoded_cursor = _decode_cursor(cursor) if cursor else None

    # Fetch one extra row to know whether there's a next page without a second query.
    rows = await repository.list_messages_for_channel(
        db, channel_id=channel_id, limit=limit + 1, cursor=decoded_cursor
    )
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = _encode_cursor(page[-1]) if has_more and page else None
    return page, next_cursor


async def send_message(
    db: AsyncSession,
    *,
    channel_id: uuid.UUID,
    sender_id: uuid.UUID,
    content: str | None,
    reply_to_id: uuid.UUID | None,
    attachment_ids: list[uuid.UUID] | None = None,
) -> Message:
    attachment_ids = attachment_ids or []
    if not content and not attachment_ids:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "A message needs content, an attachment, or both."
        )
    await require_membership(db, channel_id=channel_id, user_id=sender_id)
    if reply_to_id is not None:
        reply_target = await _require_message(db, reply_to_id)
        if reply_target.channel_id != channel_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "reply_to_id is in a different channel.")

    attachments = []
    for attachment_id in attachment_ids:
        attachment = await files_repository.get_attachment_by_id(db, attachment_id)
        if attachment is None or attachment.uploaded_by != sender_id or attachment.message_id is not None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Attachment {attachment_id} isn't a ready, unattached upload of yours.",
            )
        attachments.append(attachment)

    message = await repository.create_message(
        db, channel_id=channel_id, sender_id=sender_id, content=content, reply_to_id=reply_to_id
    )
    for attachment in attachments:
        await files_repository.attach_to_message(db, attachment, message.id)
    await db.commit()
    # Re-fetch rather than assign to message.attachments directly — assigning
    # to an unloaded relationship attribute needs to read its current value
    # first for change-tracking, and that implicit lazy-load doesn't survive
    # this async context (MissingGreenlet). A fresh eager-loaded query is both
    # simpler and avoids that entirely.
    message = await repository.get_message_by_id(db, message.id)
    await _broadcast_new(message)
    await _notify_for_new_message(db, message)
    return message


async def edit_message(
    db: AsyncSession, *, message_id: uuid.UUID, user_id: uuid.UUID, content: str
) -> Message:
    message = await _require_message(db, message_id)
    if message.sender_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only edit your own messages.")
    message.content = content
    message.is_edited = True
    message.edited_at = datetime.now(timezone.utc)
    await db.commit()
    await _broadcast_edited(message)
    return message


async def delete_message(db: AsyncSession, *, message_id: uuid.UUID, user_id: uuid.UUID) -> Message:
    message = await _require_message(db, message_id)
    if message.sender_id != user_id:
        membership = await require_membership(db, channel_id=message.channel_id, user_id=user_id)
        if membership.role not in {"owner", "admin"}:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "You can only delete your own messages (or be a channel owner/admin).",
            )
    message.is_deleted = True
    await db.commit()
    await _broadcast_deleted(message)
    return message


async def react_to_message(
    db: AsyncSession, *, message_id: uuid.UUID, user_id: uuid.UUID, emoji: str
) -> Message:
    message = await _require_message(db, message_id)
    await require_membership(db, channel_id=message.channel_id, user_id=user_id)
    added = await repository.toggle_reaction(db, message_id=message_id, user_id=user_id, emoji=emoji)
    await db.commit()
    if added and message.sender_id and message.sender_id != user_id:
        await notifications_service.notify_user(
            db,
            user_id=message.sender_id,
            type="reaction",
            payload={
                "channel_id": str(message.channel_id),
                "message_id": str(message.id),
                "emoji": emoji,
                "reactor_id": str(user_id),
            },
        )
    return message


async def pin_message(
    db: AsyncSession, *, message_id: uuid.UUID, user_id: uuid.UUID, pinned: bool
) -> Message:
    message = await _require_message(db, message_id)
    membership = await require_membership(db, channel_id=message.channel_id, user_id=user_id)
    if membership.role not in {"owner", "admin"}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only channel owners/admins can pin messages.")
    message.is_pinned = pinned
    await db.commit()
    return message


async def forward_message(
    db: AsyncSession, *, message_id: uuid.UUID, user_id: uuid.UUID, target_channel_id: uuid.UUID
) -> Message:
    original = await _require_message(db, message_id)
    await require_membership(db, channel_id=original.channel_id, user_id=user_id)
    await require_membership(db, channel_id=target_channel_id, user_id=user_id)
    forwarded = await repository.create_message(
        db,
        channel_id=target_channel_id,
        sender_id=user_id,
        content=original.content,
        forwarded_from_id=original.id,
    )
    await db.commit()
    forwarded = await repository.get_message_by_id(db, forwarded.id)  # see send_message's comment
    await _broadcast_new(forwarded)
    await _notify_for_new_message(db, forwarded)
    return forwarded
