"""WS gateway (architecture.md §3). Auth is a query-param access token since
browsers/RN can't set custom headers on the WebSocket handshake — see
docs/websocket-events.md for the full wire protocol this implements.
"""

import logging
import uuid
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.security import TokenType, decode_token
from app.db.base import AsyncSessionLocal
from app.modules.auth import repository as auth_repository
from app.modules.channels import repository as channels_repository
from app.modules.messages import repository as messages_repository
from app.ws.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)) -> None:
    user_id = await _authenticate(token)
    if user_id is None:
        await websocket.close(code=4401)
        return

    async with AsyncSessionLocal() as db:
        channels = await channels_repository.list_channels_for_user(db, user_id)
        channel_ids = [str(c.id) for c in channels]

    user_key = str(user_id)
    await manager.connect(user_id=user_key, websocket=websocket, channel_ids=channel_ids)
    await _set_presence(user_id, channel_ids, status="online")

    try:
        while True:
            raw = await websocket.receive_json()
            await _handle_client_event(user_id, raw)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WS connection for user %s crashed", user_key)
    finally:
        manager.disconnect(user_id=user_key, websocket=websocket)
        if not manager.is_connected(user_key):
            await _set_presence(user_id, channel_ids, status="offline")


async def _authenticate(token: str) -> uuid.UUID | None:
    try:
        payload = decode_token(token, TokenType.ACCESS)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        return None

    async with AsyncSessionLocal() as db:
        user = await auth_repository.get_user_by_id(db, user_id)
        if user is None or not user.is_active:
            return None
    return user_id


async def _set_presence(user_id: uuid.UUID, channel_ids: list[str], *, status: str) -> None:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        user = await auth_repository.get_user_by_id(db, user_id)
        if user is None:
            return
        user.status = status
        user.last_seen = now
        await db.commit()

    event = {
        "event": "presence.update",
        "data": {"user_id": str(user_id), "status": status, "last_seen": now.isoformat()},
    }
    for channel_id in channel_ids:
        await manager.broadcast_to_channel(channel_id, event)


async def _handle_client_event(user_id: uuid.UUID, raw: dict) -> None:
    event = raw.get("event")
    data = raw.get("data") or {}

    if event in ("typing.start", "typing.stop"):
        channel_id = data.get("channel_id")
        if not channel_id:
            return
        await manager.broadcast_to_channel(
            channel_id,
            {"event": event, "data": {"channel_id": channel_id, "user_id": str(user_id)}},
        )
        return

    if event == "read_receipt.update":
        raw_message_id = data.get("message_id")
        if not raw_message_id:
            return
        try:
            message_id = uuid.UUID(raw_message_id)
        except ValueError:
            return

        async with AsyncSessionLocal() as db:
            message = await messages_repository.get_message_by_id(db, message_id)
            if message is None:
                return
            read_at = await messages_repository.mark_read(db, message_id=message_id, user_id=user_id)
            await db.commit()
            channel_id = message.channel_id

        await manager.broadcast_to_channel(
            str(channel_id),
            {
                "event": "read_receipt.update",
                "data": {
                    "message_id": str(message_id),
                    "user_id": str(user_id),
                    "read_at": read_at.isoformat(),
                },
            },
        )
        return

    logger.debug("ignored unknown WS client event: %r", event)
