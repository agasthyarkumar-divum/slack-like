"""ConnectionManager (architecture.md §3): Redis pub/sub fan-out so broadcasts
work correctly even with a single replica today, and need zero code changes
when a second replica joins later.

`local_*` state only ever describes sockets/subscriptions held by *this*
process — the Redis pub/sub round-trip is what makes broadcast_to_channel()
reach every replica's local sockets, including this one's.
"""

import asyncio
import json
import logging
from collections.abc import Iterable

import redis.asyncio as redis
from fastapi import WebSocket

from app.core.config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._redis: redis.Redis | None = None
        self._pubsub: redis.client.PubSub | None = None
        self._listener_task: asyncio.Task | None = None

        self._user_sockets: dict[str, set[WebSocket]] = {}
        # channel_id -> user_ids (connected to THIS instance) currently interested in it.
        self._channel_subscribers: dict[str, set[str]] = {}

    async def connect(
        self, *, user_id: str, websocket: WebSocket, channel_ids: Iterable[str]
    ) -> None:
        await websocket.accept()
        self._user_sockets.setdefault(user_id, set()).add(websocket)
        for channel_id in channel_ids:
            self._channel_subscribers.setdefault(channel_id, set()).add(user_id)
        await self._ensure_listener()

    def disconnect(self, *, user_id: str, websocket: WebSocket) -> None:
        sockets = self._user_sockets.get(user_id)
        if sockets is not None:
            sockets.discard(websocket)
            if not sockets:
                del self._user_sockets[user_id]
        for subscribers in self._channel_subscribers.values():
            subscribers.discard(user_id)

    def is_connected(self, user_id: str) -> bool:
        return bool(self._user_sockets.get(user_id))

    async def broadcast_to_channel(self, channel_id: str, event: dict) -> None:
        await self._publish(f"channel:{channel_id}", event)

    async def send_to_user(self, user_id: str, event: dict) -> None:
        await self._publish(f"user:{user_id}", event)

    async def _publish(self, key: str, event: dict) -> None:
        redis_client = await self._get_redis()
        await redis_client.publish(key, json.dumps(event))

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def _ensure_listener(self) -> None:
        if self._listener_task is not None:
            return
        redis_client = await self._get_redis()
        self._pubsub = redis_client.pubsub()
        await self._pubsub.psubscribe("channel:*", "user:*")
        self._listener_task = asyncio.create_task(self._listen())

    async def close(self) -> None:
        """Cancels the listener task and closes the Redis connection — call on
        app shutdown (and from tests, so pytest doesn't warn about leaked tasks).
        """
        if self._listener_task is not None:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except (asyncio.CancelledError, Exception):
                pass
            self._listener_task = None
        if self._pubsub is not None:
            await self._pubsub.aclose()
            self._pubsub = None
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def _listen(self) -> None:
        assert self._pubsub is not None
        async for message in self._pubsub.listen():
            if message["type"] != "pmessage":
                continue
            try:
                event = json.loads(message["data"])
            except (TypeError, ValueError):
                logger.warning("dropped malformed pub/sub payload on %s", message["channel"])
                continue
            await self._deliver(message["channel"], event)

    async def _deliver(self, channel_key: str, event: dict) -> None:
        kind, _, target_id = channel_key.partition(":")
        if kind == "user":
            user_ids: Iterable[str] = (target_id,)
        elif kind == "channel":
            user_ids = list(self._channel_subscribers.get(target_id, ()))
        else:
            return

        for user_id in user_ids:
            for websocket in list(self._user_sockets.get(user_id, ())):
                try:
                    await websocket.send_json(event)
                except Exception:
                    logger.debug("dropped delivery to a dead socket for user %s", user_id)


# Module-level singleton — the WS router and any service that needs to
# broadcast (messages, files, notifications) share this one instance.
manager = ConnectionManager(settings.REDIS_URL)
