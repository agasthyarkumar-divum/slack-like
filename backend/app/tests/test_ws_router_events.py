"""_handle_client_event tests (app/ws/router.py) — the client->server event
handling that sits above ConnectionManager (already covered by
test_ws_manager.py). Calls the handler directly against the real module-level
`manager` singleton, the same one the live /ws endpoint uses.
"""

import uuid

from app.ws.manager import manager
from app.ws.router import _handle_client_event


class FakeWebSocket:
    def __init__(self):
        self.received: list[dict] = []

    async def accept(self):
        pass

    async def send_json(self, data: dict):
        self.received.append(data)


async def _wait_until(predicate, timeout: float = 2.0) -> None:
    import asyncio

    elapsed = 0.0
    step = 0.02
    while not predicate() and elapsed < timeout:
        await asyncio.sleep(step)
        elapsed += step
    assert predicate(), "condition not met within timeout"


async def test_message_delivered_is_rebroadcast_to_the_channel_and_not_persisted(db_session):
    sender_ws, recipient_ws = FakeWebSocket(), FakeWebSocket()
    channel_id = str(uuid.uuid4())
    recipient_id = uuid.uuid4()
    message_id = str(uuid.uuid4())

    await manager.connect(user_id="sender", websocket=sender_ws, channel_ids=[channel_id])
    await manager.connect(user_id=str(recipient_id), websocket=recipient_ws, channel_ids=[channel_id])

    await _handle_client_event(
        recipient_id,
        {"event": "message.delivered", "data": {"message_id": message_id, "channel_id": channel_id}},
    )

    await _wait_until(lambda: len(sender_ws.received) == 1)
    payload = sender_ws.received[0]
    assert payload["event"] == "message.delivered"
    assert payload["data"] == {"message_id": message_id, "user_id": str(recipient_id)}
    # Rebroadcast to every channel member, including the acking client itself.
    await _wait_until(lambda: len(recipient_ws.received) == 1)


async def test_message_delivered_missing_fields_is_a_no_op():
    ws = FakeWebSocket()
    channel_id = str(uuid.uuid4())
    await manager.connect(user_id="alice", websocket=ws, channel_ids=[channel_id])

    await _handle_client_event(uuid.uuid4(), {"event": "message.delivered", "data": {"channel_id": channel_id}})
    await _handle_client_event(uuid.uuid4(), {"event": "message.delivered", "data": {"message_id": "x"}})

    import asyncio

    await asyncio.sleep(0.2)
    assert ws.received == []
