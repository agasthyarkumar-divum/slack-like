"""Messages module tests (architecture.md §6): send/list, cursor pagination
correctness, edit/delete permissions, reactions, pin, and forward.
"""

from app.tests.helpers import auth_header, register_and_login


async def _setup_channel_with_two_members(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]
    channel = await client.post(
        "/channels",
        json={"name": "general", "type": "public", "member_ids": [bob_id]},
        headers=auth_header(alice),
    )
    return alice, bob, channel.json()["id"]


async def test_send_and_list_messages(client):
    alice, bob, channel_id = await _setup_channel_with_two_members(client)

    sent = await client.post(
        f"/channels/{channel_id}/messages", json={"content": "hello"}, headers=auth_header(alice)
    )
    assert sent.status_code == 201
    assert sent.json()["content"] == "hello"

    listed = await client.get(f"/channels/{channel_id}/messages", headers=auth_header(bob))
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1
    assert listed.json()["items"][0]["content"] == "hello"


async def test_send_message_requires_membership(client):
    alice, _bob, channel_id = await _setup_channel_with_two_members(client)
    stranger = await register_and_login(client, "stranger@example.com")

    response = await client.post(
        f"/channels/{channel_id}/messages", json={"content": "sneaky"}, headers=auth_header(stranger)
    )
    assert response.status_code == 404


async def test_cursor_pagination_covers_every_message_exactly_once(client):
    alice, _bob, channel_id = await _setup_channel_with_two_members(client)

    sent_ids = []
    for i in range(5):
        response = await client.post(
            f"/channels/{channel_id}/messages",
            json={"content": f"message {i}"},
            headers=auth_header(alice),
        )
        sent_ids.append(response.json()["id"])

    seen_ids = []
    cursor = None
    for _ in range(10):  # generous upper bound on pages; loop breaks on its own
        params = {"limit": 2}
        if cursor:
            params["cursor"] = cursor
        page = await client.get(
            f"/channels/{channel_id}/messages", params=params, headers=auth_header(alice)
        )
        body = page.json()
        seen_ids.extend(m["id"] for m in body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            break

    assert len(seen_ids) == len(set(seen_ids)) == 5  # no dupes, no skips
    assert seen_ids == list(reversed(sent_ids))  # newest first, oldest last


async def test_edit_message_sender_only(client):
    alice, bob, channel_id = await _setup_channel_with_two_members(client)
    message = (
        await client.post(
            f"/channels/{channel_id}/messages", json={"content": "typo"}, headers=auth_header(alice)
        )
    ).json()

    as_bob = await client.patch(
        f"/messages/{message['id']}", json={"content": "hijacked"}, headers=auth_header(bob)
    )
    as_alice = await client.patch(
        f"/messages/{message['id']}", json={"content": "fixed"}, headers=auth_header(alice)
    )
    assert as_bob.status_code == 403
    assert as_alice.status_code == 200
    assert as_alice.json()["content"] == "fixed"
    assert as_alice.json()["is_edited"] is True


async def test_delete_message_excludes_it_from_listing(client):
    alice, _bob, channel_id = await _setup_channel_with_two_members(client)
    message = (
        await client.post(
            f"/channels/{channel_id}/messages", json={"content": "oops"}, headers=auth_header(alice)
        )
    ).json()

    deleted = await client.delete(f"/messages/{message['id']}", headers=auth_header(alice))
    assert deleted.status_code == 200
    assert deleted.json()["is_deleted"] is True

    listed = await client.get(f"/channels/{channel_id}/messages", headers=auth_header(alice))
    assert listed.json()["items"] == []


async def test_owner_can_delete_someone_elses_message(client):
    alice, bob, channel_id = await _setup_channel_with_two_members(client)
    message = (
        await client.post(
            f"/channels/{channel_id}/messages", json={"content": "bob's message"}, headers=auth_header(bob)
        )
    ).json()

    # alice is channel owner but not the sender — should still be allowed to moderate.
    response = await client.delete(f"/messages/{message['id']}", headers=auth_header(alice))
    assert response.status_code == 200
    assert response.json()["is_deleted"] is True


async def test_reaction_toggles_on_and_off(client):
    alice, bob, channel_id = await _setup_channel_with_two_members(client)
    message = (
        await client.post(
            f"/channels/{channel_id}/messages", json={"content": "funny"}, headers=auth_header(alice)
        )
    ).json()

    react = await client.post(
        f"/messages/{message['id']}/reactions", json={"emoji": "😂"}, headers=auth_header(bob)
    )
    unreact = await client.post(
        f"/messages/{message['id']}/reactions", json={"emoji": "😂"}, headers=auth_header(bob)
    )
    assert react.status_code == 200
    assert unreact.status_code == 200  # toggled off; endpoint still succeeds


async def test_reactions_appear_in_message_response_scoped_per_viewer(client):
    alice, bob, channel_id = await _setup_channel_with_two_members(client)
    message = (
        await client.post(
            f"/channels/{channel_id}/messages", json={"content": "funny"}, headers=auth_header(alice)
        )
    ).json()

    reacted = await client.post(
        f"/messages/{message['id']}/reactions", json={"emoji": "😂"}, headers=auth_header(bob)
    )
    assert reacted.json()["reactions"] == [{"emoji": "😂", "count": 1, "me": True}]

    listed_as_alice = await client.get(f"/channels/{channel_id}/messages", headers=auth_header(alice))
    alice_view = listed_as_alice.json()["items"][0]
    assert alice_view["reactions"] == [{"emoji": "😂", "count": 1, "me": False}]  # alice didn't react

    listed_as_bob = await client.get(f"/channels/{channel_id}/messages", headers=auth_header(bob))
    bob_view = listed_as_bob.json()["items"][0]
    assert bob_view["reactions"] == [{"emoji": "😂", "count": 1, "me": True}]  # bob did


async def test_thread_replies_are_excluded_from_main_list_and_counted_on_parent(client):
    alice, bob, channel_id = await _setup_channel_with_two_members(client)
    parent = (
        await client.post(
            f"/channels/{channel_id}/messages", json={"content": "who's up for lunch?"}, headers=auth_header(alice)
        )
    ).json()

    reply = (
        await client.post(
            f"/channels/{channel_id}/messages",
            json={"content": "me!", "reply_to_id": parent["id"]},
            headers=auth_header(bob),
        )
    ).json()
    assert reply["reply_to_id"] == parent["id"]

    main_list = (await client.get(f"/channels/{channel_id}/messages", headers=auth_header(alice))).json()
    assert [m["id"] for m in main_list["items"]] == [parent["id"]]  # reply not in the main timeline
    assert main_list["items"][0]["reply_count"] == 1

    thread = (
        await client.get(f"/messages/{parent['id']}/replies", headers=auth_header(alice))
    ).json()
    assert thread["parent"]["id"] == parent["id"]
    assert thread["parent"]["reply_count"] == 1
    assert [m["id"] for m in thread["items"]] == [reply["id"]]


async def test_reply_to_message_in_a_different_channel_is_rejected(client):
    alice, _bob, channel_id = await _setup_channel_with_two_members(client)
    parent = (
        await client.post(
            f"/channels/{channel_id}/messages", json={"content": "hi"}, headers=auth_header(alice)
        )
    ).json()
    other_channel = (
        await client.post(
            "/channels", json={"name": "elsewhere", "type": "public", "member_ids": []},
            headers=auth_header(alice),
        )
    ).json()

    response = await client.post(
        f"/channels/{other_channel['id']}/messages",
        json={"content": "wrong channel", "reply_to_id": parent["id"]},
        headers=auth_header(alice),
    )
    assert response.status_code == 422


async def test_pin_requires_manage_role(client):
    alice, bob, channel_id = await _setup_channel_with_two_members(client)
    message = (
        await client.post(
            f"/channels/{channel_id}/messages", json={"content": "important"}, headers=auth_header(alice)
        )
    ).json()

    as_member = await client.post(f"/messages/{message['id']}/pin", headers=auth_header(bob))
    as_owner = await client.post(f"/messages/{message['id']}/pin", headers=auth_header(alice))
    assert as_member.status_code == 403
    assert as_owner.status_code == 200
    assert as_owner.json()["is_pinned"] is True

    unpinned = await client.post(f"/messages/{message['id']}/unpin", headers=auth_header(alice))
    assert unpinned.json()["is_pinned"] is False


async def test_forward_requires_membership_in_target_channel(client):
    alice, bob, channel_id = await _setup_channel_with_two_members(client)
    message = (
        await client.post(
            f"/channels/{channel_id}/messages", json={"content": "fyi"}, headers=auth_header(alice)
        )
    ).json()

    other_channel = (
        await client.post(
            "/channels", json={"name": "private-club", "type": "public", "member_ids": []},
            headers=auth_header(alice),
        )
    ).json()

    forwarded_by_owner = await client.post(
        f"/messages/{message['id']}/forward",
        json={"target_channel_id": other_channel["id"]},
        headers=auth_header(alice),
    )
    forwarded_by_non_member = await client.post(
        f"/messages/{message['id']}/forward",
        json={"target_channel_id": other_channel["id"]},
        headers=auth_header(bob),
    )
    assert forwarded_by_owner.status_code == 201
    assert forwarded_by_owner.json()["forwarded_from_id"] == message["id"]
    assert forwarded_by_non_member.status_code == 404
