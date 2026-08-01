"""ConnectionManager tests (architecture.md §3) — a real Redis round-trip (the
docker-compose `redis` service), not a mock, since the whole point of this
class is that publish-on-one-instance/deliver-on-another actually works.
"""

import asyncio

import pytest_asyncio

from app.core.config import settings
from app.ws.manager import ConnectionManager


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.received: list[dict] = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, data: dict):
        self.received.append(data)


async def _wait_until(predicate, timeout: float = 2.0) -> None:
    """Pub/sub delivery is async — poll briefly instead of a fixed sleep."""
    elapsed = 0.0
    step = 0.02
    while not predicate() and elapsed < timeout:
        await asyncio.sleep(step)
        elapsed += step
    assert predicate(), "condition not met within timeout"


@pytest_asyncio.fixture()
async def manager():
    m = ConnectionManager(settings.REDIS_URL)
    yield m
    await m.close()


async def test_broadcast_to_channel_only_reaches_subscribed_users(manager):
    alice_ws, bob_ws = FakeWebSocket(), FakeWebSocket()
    await manager.connect(user_id="alice", websocket=alice_ws, channel_ids=["c1"])
    await manager.connect(user_id="bob", websocket=bob_ws, channel_ids=["c2"])

    await manager.broadcast_to_channel("c1", {"event": "message.new", "data": {"x": 1}})

    await _wait_until(lambda: len(alice_ws.received) == 1)
    assert alice_ws.received[0]["event"] == "message.new"
    assert bob_ws.received == []


async def test_send_to_user_reaches_only_that_user(manager):
    alice_ws, bob_ws = FakeWebSocket(), FakeWebSocket()
    await manager.connect(user_id="alice", websocket=alice_ws, channel_ids=[])
    await manager.connect(user_id="bob", websocket=bob_ws, channel_ids=[])

    await manager.send_to_user("bob", {"event": "notification.new", "data": {}})

    await _wait_until(lambda: len(bob_ws.received) == 1)
    assert alice_ws.received == []


async def test_multiple_sockets_for_the_same_user_both_receive(manager):
    ws1, ws2 = FakeWebSocket(), FakeWebSocket()
    await manager.connect(user_id="alice", websocket=ws1, channel_ids=["c1"])
    await manager.connect(user_id="alice", websocket=ws2, channel_ids=["c1"])

    await manager.broadcast_to_channel("c1", {"event": "message.new", "data": {}})

    await _wait_until(lambda: len(ws1.received) == 1 and len(ws2.received) == 1)


async def test_disconnect_stops_further_delivery(manager):
    ws = FakeWebSocket()
    await manager.connect(user_id="alice", websocket=ws, channel_ids=["c1"])
    manager.disconnect(user_id="alice", websocket=ws)
    assert not manager.is_connected("alice")

    await manager.broadcast_to_channel("c1", {"event": "message.new", "data": {}})
    await asyncio.sleep(0.3)  # give it a chance to (wrongly) arrive
    assert ws.received == []


async def test_is_connected_reflects_socket_count(manager):
    ws = FakeWebSocket()
    assert not manager.is_connected("alice")
    await manager.connect(user_id="alice", websocket=ws, channel_ids=[])
    assert manager.is_connected("alice")
    manager.disconnect(user_id="alice", websocket=ws)
    assert not manager.is_connected("alice")
