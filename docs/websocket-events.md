# WebSocket Events

Source of truth for the WS wire protocol (`ws/router.py` + `ws/manager.py`, architecture §3).
Not covered by OpenAPI, so it's documented by hand here — keep this file in sync with
`ws/manager.py` in the same commit whenever an event's shape changes.

## Connecting

```
WSS /ws?token=<access_jwt>
```

The access JWT is passed as a query param (browsers/RN can't set custom headers on the
WebSocket handshake). The server verifies it the same way as the REST `Authorization` header
and rejects the upgrade with a close code if it's missing, expired, or invalid.

All events on the wire share this envelope:

```json
{
  "event": "message.new",
  "data": { }
}
```

## Event Reference

| Event | Direction | Description |
|---|---|---|
| `message.new` | server → client | A new message was posted to a channel the client is a member of |
| `message.edited` | server → client | An existing message's content changed |
| `message.deleted` | server → client | A message was soft-deleted |
| `typing.start` | client → server → broadcast | Client started typing in a channel |
| `typing.stop` | client → server → broadcast | Client stopped typing (or composer cleared/blurred) |
| `presence.update` | server → client | A user's online/away/offline status or `last_seen` changed |
| `read_receipt.update` | client → server → broadcast | Client marked a message read |
| `notification.new` | server → client | A new notification was created for this user (mention, DM, reaction) |
| `file.ready` | server → client | An uploaded attachment finished async processing (encrypt/compress/thumbnail) and is downloadable |

## Payload Shapes

### `message.new` (server → client)

```json
{
  "event": "message.new",
  "data": {
    "id": "b3f1c2b0-...-uuid",
    "channel_id": "a1e4...-uuid",
    "sender_id": "9c2d...-uuid",
    "content": "hey, standup moved to 10am",
    "reply_to_id": null,
    "forwarded_from_id": null,
    "is_pinned": false,
    "is_edited": false,
    "created_at": "2026-07-31T09:12:03.512Z"
  }
}
```

### `message.edited` (server → client)

```json
{
  "event": "message.edited",
  "data": {
    "id": "b3f1c2b0-...-uuid",
    "channel_id": "a1e4...-uuid",
    "content": "hey, standup moved to 10:15am",
    "edited_at": "2026-07-31T09:14:47.001Z"
  }
}
```

### `message.deleted` (server → client)

```json
{
  "event": "message.deleted",
  "data": {
    "id": "b3f1c2b0-...-uuid",
    "channel_id": "a1e4...-uuid"
  }
}
```

### `typing.start` / `typing.stop`

Client → server:

```json
{
  "event": "typing.start",
  "data": { "channel_id": "a1e4...-uuid" }
}
```

Server rebroadcasts to other members of the channel with the sender attached:

```json
{
  "event": "typing.start",
  "data": {
    "channel_id": "a1e4...-uuid",
    "user_id": "9c2d...-uuid"
  }
}
```

`typing.stop` has the identical shape. Clients should also implicitly treat a `typing.start`
as expired client-side after a few seconds without a follow-up, in case a `typing.stop` is
dropped (e.g. app backgrounded).

### `presence.update` (server → client)

```json
{
  "event": "presence.update",
  "data": {
    "user_id": "9c2d...-uuid",
    "status": "online",
    "last_seen": "2026-07-31T09:12:00.000Z"
  }
}
```

`status` is one of `online` / `away` / `offline`.

### `read_receipt.update`

Client → server:

```json
{
  "event": "read_receipt.update",
  "data": { "message_id": "b3f1c2b0-...-uuid" }
}
```

Server rebroadcasts to other channel members:

```json
{
  "event": "read_receipt.update",
  "data": {
    "message_id": "b3f1c2b0-...-uuid",
    "user_id": "9c2d...-uuid",
    "read_at": "2026-07-31T09:15:02.222Z"
  }
}
```

### `notification.new` (server → client)

```json
{
  "event": "notification.new",
  "data": {
    "id": "e5a0...-uuid",
    "type": "mention",
    "payload": {
      "channel_id": "a1e4...-uuid",
      "message_id": "b3f1c2b0-...-uuid",
      "preview": "@you can you review the PR?"
    },
    "is_read": false,
    "created_at": "2026-07-31T09:12:03.600Z"
  }
}
```

### `file.ready` (server → client)

```json
{
  "event": "file.ready",
  "data": {
    "attachment_id": "f9b1...-uuid",
    "message_id": "b3f1c2b0-...-uuid",
    "thumbnail_uri": "local://thumbnails/f9b1....jpg"
  }
}
```

## Delivery Model

Every broadcast is published once to Redis (`channel:{channel_id}` or `user:{user_id}` as the
pub/sub key) and fanned out to whichever backend instance holds the recipient's local socket —
see `ws/manager.py` and architecture §3. This holds even with a single replica today, so adding
replica #2 later requires no protocol or code change, only a deploy config change.
