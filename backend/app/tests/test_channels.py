"""Channels module tests (architecture.md §6): creation/ownership, membership
management, and the "membership required" permission boundary that
`require_membership` enforces for every other channel-scoped module too.
"""

from app.tests.helpers import auth_header, register_and_login


async def _create_channel(client, tokens, name="general", type="public", member_ids=None):
    response = await client.post(
        "/channels",
        json={"name": name, "type": type, "member_ids": member_ids or []},
        headers=auth_header(tokens),
    )
    return response


async def test_create_channel_makes_creator_owner(client):
    alice = await register_and_login(client, "alice@example.com")
    alice_id = (await client.get("/users/me", headers=auth_header(alice))).json()["id"]
    response = await _create_channel(client, alice)
    assert response.status_code == 201
    channel_id = response.json()["id"]

    members = await client.get(f"/channels/{channel_id}/members", headers=auth_header(alice))
    assert members.status_code == 200
    assert len(members.json()) == 1
    assert members.json()[0]["user_id"] == alice_id
    assert members.json()[0]["role"] == "owner"


async def test_create_channel_with_additional_members(client, db_session):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_me = await client.get("/users/me", headers=auth_header(bob))
    bob_id = bob_me.json()["id"]

    response = await _create_channel(client, alice, member_ids=[bob_id])
    assert response.status_code == 201
    channel_id = response.json()["id"]

    members = await client.get(f"/channels/{channel_id}/members", headers=auth_header(alice))
    roles_by_user = {m["user_id"]: m["role"] for m in members.json()}
    assert roles_by_user[bob_id] == "member"


async def test_list_my_channels_only_shows_membership(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    await _create_channel(client, alice, name="alices-channel")

    alice_channels = await client.get("/channels", headers=auth_header(alice))
    bob_channels = await client.get("/channels", headers=auth_header(bob))
    assert len(alice_channels.json()) == 1
    assert bob_channels.json() == []


async def test_unread_count_excludes_own_messages_and_read_ones(client, db_session):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]
    channel_id = (await _create_channel(client, alice, member_ids=[bob_id])).json()["id"]

    # alice sends 3 messages — none should count as unread for alice herself.
    message_ids = []
    for i in range(3):
        sent = await client.post(
            f"/channels/{channel_id}/messages", json={"content": f"msg {i}"}, headers=auth_header(alice)
        )
        message_ids.append(sent.json()["id"])

    alice_channels = (await client.get("/channels", headers=auth_header(alice))).json()
    assert next(c for c in alice_channels if c["id"] == channel_id)["unread_count"] == 0

    bob_channels = (await client.get("/channels", headers=auth_header(bob))).json()
    assert next(c for c in bob_channels if c["id"] == channel_id)["unread_count"] == 3

    # Reacting isn't reading — count should be unaffected.
    await client.post(f"/messages/{message_ids[0]}/reactions", json={"emoji": "x"}, headers=auth_header(bob))
    bob_channels = (await client.get("/channels", headers=auth_header(bob))).json()
    assert next(c for c in bob_channels if c["id"] == channel_id)["unread_count"] == 3

    # Marking one read (normally driven by the read_receipt.update WS event —
    # simulated here directly since this test client is REST-only) should
    # drop the count by exactly one.
    from app.modules.messages import repository as messages_repository

    await messages_repository.mark_read(db_session, message_id=message_ids[0], user_id=bob_id)
    await db_session.commit()
    bob_channels = (await client.get("/channels", headers=auth_header(bob))).json()
    assert next(c for c in bob_channels if c["id"] == channel_id)["unread_count"] == 2


async def test_get_channel_requires_membership(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    channel_id = (await _create_channel(client, alice)).json()["id"]

    as_owner = await client.get(f"/channels/{channel_id}", headers=auth_header(alice))
    as_stranger = await client.get(f"/channels/{channel_id}", headers=auth_header(bob))
    assert as_owner.status_code == 200
    assert as_stranger.status_code == 404


async def test_update_channel_requires_manage_role(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]
    channel_id = (await _create_channel(client, alice, member_ids=[bob_id])).json()["id"]

    as_owner = await client.patch(
        f"/channels/{channel_id}", json={"topic": "new topic"}, headers=auth_header(alice)
    )
    as_member = await client.patch(
        f"/channels/{channel_id}", json={"topic": "hijacked"}, headers=auth_header(bob)
    )
    assert as_owner.status_code == 200
    assert as_owner.json()["topic"] == "new topic"
    assert as_member.status_code == 403


async def test_add_member_requires_manage_role(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    carol = await register_and_login(client, "carol@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]
    carol_id = (await client.get("/users/me", headers=auth_header(carol))).json()["id"]
    channel_id = (await _create_channel(client, alice, member_ids=[bob_id])).json()["id"]

    response = await client.post(
        f"/channels/{channel_id}/members", json={"user_id": carol_id}, headers=auth_header(bob)
    )
    assert response.status_code == 403


async def test_add_duplicate_member_conflicts(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]
    channel_id = (await _create_channel(client, alice, member_ids=[bob_id])).json()["id"]

    response = await client.post(
        f"/channels/{channel_id}/members", json={"user_id": bob_id}, headers=auth_header(alice)
    )
    assert response.status_code == 409


async def test_member_can_leave_but_not_remove_others(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    carol = await register_and_login(client, "carol@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]
    carol_id = (await client.get("/users/me", headers=auth_header(carol))).json()["id"]
    channel_id = (await _create_channel(client, alice, member_ids=[bob_id, carol_id])).json()["id"]

    cannot_remove_carol = await client.delete(
        f"/channels/{channel_id}/members/{carol_id}", headers=auth_header(bob)
    )
    can_leave = await client.delete(
        f"/channels/{channel_id}/members/{bob_id}", headers=auth_header(bob)
    )
    assert cannot_remove_carol.status_code == 403
    assert can_leave.status_code == 204


async def test_owner_can_remove_a_member(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]
    channel_id = (await _create_channel(client, alice, member_ids=[bob_id])).json()["id"]

    response = await client.delete(
        f"/channels/{channel_id}/members/{bob_id}", headers=auth_header(alice)
    )
    assert response.status_code == 204
    still_visible_to_bob = await client.get(f"/channels/{channel_id}", headers=auth_header(bob))
    assert still_visible_to_bob.status_code == 404


async def test_dm_creates_a_channel_with_both_members(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]

    response = await client.post(f"/channels/dm/{bob_id}", headers=auth_header(alice))
    assert response.status_code == 200
    assert response.json()["type"] == "dm"

    members = await client.get(
        f"/channels/{response.json()['id']}/members", headers=auth_header(alice)
    )
    member_ids = {m["user_id"] for m in members.json()}
    assert member_ids == {bob_id, (await client.get("/users/me", headers=auth_header(alice))).json()["id"]}


async def test_dm_is_idempotent(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]

    first = await client.post(f"/channels/dm/{bob_id}", headers=auth_header(alice))
    second = await client.post(f"/channels/dm/{bob_id}", headers=auth_header(alice))
    # Also symmetric: bob starting a DM with alice should find the same channel.
    alice_id = (await client.get("/users/me", headers=auth_header(alice))).json()["id"]
    third = await client.post(f"/channels/dm/{alice_id}", headers=auth_header(bob))

    assert first.json()["id"] == second.json()["id"] == third.json()["id"]


async def test_cannot_dm_yourself(client):
    alice = await register_and_login(client, "alice@example.com")
    alice_id = (await client.get("/users/me", headers=auth_header(alice))).json()["id"]

    response = await client.post(f"/channels/dm/{alice_id}", headers=auth_header(alice))
    assert response.status_code == 422


async def test_dm_with_unknown_user_404s(client):
    alice = await register_and_login(client, "alice@example.com")
    response = await client.post(
        "/channels/dm/00000000-0000-0000-0000-000000000000", headers=auth_header(alice)
    )
    assert response.status_code == 404
