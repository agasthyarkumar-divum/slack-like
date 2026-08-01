"""Notification creation + delivery (architecture.md §9):
insert a row -> push over WS if the user is connected to this instance ->
otherwise queue an FCM push (Celery task, stubbed — see workers/tasks_notifications.py).
"""

import re
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Notification, User
from app.modules.notifications import repository
from app.ws.manager import manager

PREVIEW_MAX_LENGTH = 140

# No `username` column in the schema (architecture.md §5) — @mentions match
# against the local-part of a channel member's email (alice@example.com -> @alice),
# the closest available proxy. Single-token only, same reasoning Slack-style
# usernames exist for: display names can contain spaces, tokens can't.
_MENTION_PATTERN = re.compile(r"@([\w.+-]+)")


def make_preview(content: str | None) -> str:
    if not content:
        return ""
    return content if len(content) <= PREVIEW_MAX_LENGTH else content[: PREVIEW_MAX_LENGTH - 1] + "…"


def find_mentioned_user_ids(content: str | None, members: list[User]) -> set[uuid.UUID]:
    if not content:
        return set()
    tokens = {m.lower() for m in _MENTION_PATTERN.findall(content)}
    if not tokens:
        return set()
    return {
        member.id
        for member in members
        if member.email.split("@", 1)[0].lower() in tokens
    }


async def notify_user(db: AsyncSession, *, user_id: uuid.UUID, type: str, payload: dict) -> Notification:
    notification = await repository.create_notification(db, user_id=user_id, type=type, payload=payload)
    await db.commit()

    event = {
        "event": "notification.new",
        "data": {
            "id": str(notification.id),
            "type": notification.type,
            "payload": notification.payload,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
        },
    }
    await manager.send_to_user(str(user_id), event)

    if not manager.is_connected(str(user_id)):
        from app.workers.tasks_notifications import send_fcm_push  # local import, mirrors tasks_files

        send_fcm_push.delay(user_id=str(user_id), notification_type=type, preview=payload.get("preview", ""))

    return notification


async def list_my_notifications(
    db: AsyncSession, *, user_id: uuid.UUID, limit: int
) -> tuple[list[Notification], int]:
    items = await repository.list_for_user(db, user_id=user_id, limit=limit)
    unread_count = await repository.count_unread(db, user_id=user_id)
    return items, unread_count


async def mark_read(db: AsyncSession, *, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
    notification = await repository.get_notification_by_id(db, notification_id)
    if notification is None or notification.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found.")
    await repository.mark_read(db, notification)
    await db.commit()
    return notification


async def mark_all_read(db: AsyncSession, *, user_id: uuid.UUID) -> None:
    await repository.mark_all_read(db, user_id=user_id)
    await db.commit()
