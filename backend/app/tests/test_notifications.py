"""Notification tests (architecture.md §9): @mention parsing, blanket DM
notifications, reaction notifications, and the notifications CRUD endpoints.
"""

from app.tests.helpers import auth_header, register_and_login


async def _make_channel(client, tokens, member_ids=None, type="public", name="notif-test"):
    response = await client.post(
        "/channels", json={"name": name, "type": type, "member_ids": member_ids or []},
        headers=auth_header(tokens),
    )
    return response.json()


async def test_mention_notifies_the_mentioned_member(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]
    channel = await _make_channel(client, alice, member_ids=[bob_id])

    await client.post(
        f"/channels/{channel['id']}/messages",
        json={"content": "@bob can you take a look at this?"},
        headers=auth_header(alice),
    )

    notifications = await client.get("/notifications", headers=auth_header(bob))
    assert notifications.status_code == 200
    body = notifications.json()
    assert body["unread_count"] == 1
    assert body["items"][0]["type"] == "mention"
    assert body["items"][0]["payload"]["preview"] == "@bob can you take a look at this?"


async def test_non_mentioned_member_gets_no_notification(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]
    channel = await _make_channel(client, alice, member_ids=[bob_id])

    await client.post(
        f"/channels/{channel['id']}/messages",
        json={"content": "no mentions here"},
        headers=auth_header(alice),
    )

    notifications = await client.get("/notifications", headers=auth_header(bob))
    assert notifications.json()["unread_count"] == 0


async def test_dm_message_notifies_unconditionally(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]
    channel = await _make_channel(client, alice, member_ids=[bob_id], type="dm", name="alice-bob-dm")

    await client.post(
        f"/channels/{channel['id']}/messages",
        json={"content": "hey, no mention needed in a DM"},
        headers=auth_header(alice),
    )

    notifications = await client.get("/notifications", headers=auth_header(bob))
    body = notifications.json()
    assert body["unread_count"] == 1
    assert body["items"][0]["type"] == "dm"


async def test_sender_does_not_notify_themselves(client):
    alice = await register_and_login(client, "alice@example.com")
    channel = await _make_channel(client, alice)

    await client.post(
        f"/channels/{channel['id']}/messages",
        json={"content": f"@alice talking to myself"},
        headers=auth_header(alice),
    )

    notifications = await client.get("/notifications", headers=auth_header(alice))
    assert notifications.json()["unread_count"] == 0


async def test_reaction_notifies_the_message_sender(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]
    channel = await _make_channel(client, alice, member_ids=[bob_id])
    message = (
        await client.post(
            f"/channels/{channel['id']}/messages", json={"content": "funny joke"}, headers=auth_header(alice)
        )
    ).json()

    await client.post(
        f"/messages/{message['id']}/reactions", json={"emoji": "😂"}, headers=auth_header(bob)
    )

    notifications = await client.get("/notifications", headers=auth_header(alice))
    body = notifications.json()
    assert body["unread_count"] == 1
    assert body["items"][0]["type"] == "reaction"
    assert body["items"][0]["payload"]["emoji"] == "😂"


async def test_un_reacting_does_not_notify_again(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]
    channel = await _make_channel(client, alice, member_ids=[bob_id])
    message = (
        await client.post(
            f"/channels/{channel['id']}/messages", json={"content": "joke"}, headers=auth_header(alice)
        )
    ).json()

    await client.post(f"/messages/{message['id']}/reactions", json={"emoji": "😂"}, headers=auth_header(bob))
    await client.post(f"/messages/{message['id']}/reactions", json={"emoji": "😂"}, headers=auth_header(bob))  # un-react

    notifications = await client.get("/notifications", headers=auth_header(alice))
    assert notifications.json()["unread_count"] == 1  # only the add, not the remove


async def test_mark_read_and_mark_all_read(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]
    channel = await _make_channel(client, alice, member_ids=[bob_id])
    await client.post(
        f"/channels/{channel['id']}/messages", json={"content": "@bob one"}, headers=auth_header(alice)
    )
    await client.post(
        f"/channels/{channel['id']}/messages", json={"content": "@bob two"}, headers=auth_header(alice)
    )

    listing = (await client.get("/notifications", headers=auth_header(bob))).json()
    assert listing["unread_count"] == 2

    first_id = listing["items"][0]["id"]
    marked = await client.post(f"/notifications/{first_id}/read", headers=auth_header(bob))
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True

    after_one = (await client.get("/notifications", headers=auth_header(bob))).json()
    assert after_one["unread_count"] == 1

    mark_all = await client.post("/notifications/read-all", headers=auth_header(bob))
    assert mark_all.status_code == 204

    after_all = (await client.get("/notifications", headers=auth_header(bob))).json()
    assert after_all["unread_count"] == 0


async def test_notification_preference_none_suppresses_mentions_and_reactions(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]
    channel = await _make_channel(client, alice, member_ids=[bob_id])

    settings = await client.patch(
        "/users/me", json={"notification_preference": "none"}, headers=auth_header(bob)
    )
    assert settings.status_code == 200
    assert settings.json()["notification_preference"] == "none"

    await client.post(
        f"/channels/{channel['id']}/messages", json={"content": "@bob hi"}, headers=auth_header(alice)
    )

    notifications = await client.get("/notifications", headers=auth_header(bob))
    assert notifications.json()["unread_count"] == 0


async def test_notification_preference_mentions_dms_suppresses_reactions_only(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]
    channel = await _make_channel(client, alice, member_ids=[bob_id])
    message = (
        await client.post(
            f"/channels/{channel['id']}/messages", json={"content": "joke"}, headers=auth_header(alice)
        )
    ).json()

    await client.patch(
        "/users/me", json={"notification_preference": "mentions_dms"}, headers=auth_header(alice)
    )
    await client.post(f"/messages/{message['id']}/reactions", json={"emoji": "😂"}, headers=auth_header(bob))

    notifications = await client.get("/notifications", headers=auth_header(alice))
    assert notifications.json()["unread_count"] == 0  # reaction suppressed

    await client.post(
        f"/channels/{channel['id']}/messages", json={"content": "@alice still there?"}, headers=auth_header(bob)
    )
    notifications_after_mention = await client.get("/notifications", headers=auth_header(alice))
    assert notifications_after_mention.json()["unread_count"] == 1  # mentions still get through


async def test_cannot_mark_someone_elses_notification_read(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]
    channel = await _make_channel(client, alice, member_ids=[bob_id])
    await client.post(
        f"/channels/{channel['id']}/messages", json={"content": "@bob hi"}, headers=auth_header(alice)
    )
    bobs_notification_id = (await client.get("/notifications", headers=auth_header(bob))).json()["items"][0]["id"]

    response = await client.post(f"/notifications/{bobs_notification_id}/read", headers=auth_header(alice))
    assert response.status_code == 404
