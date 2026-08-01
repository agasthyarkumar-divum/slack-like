"""Search module tests (architecture.md §6) — the FTS triggers/indexes only
exist in the migration (not Base.metadata used by the test harness), so these
tests populate search_vector by hand, mirroring exactly what the triggers do.
"""

from sqlalchemy import text

from app.tests.helpers import auth_header, register_and_login


async def _set_search_vector(db_session, table: str, row_id: str, text_value: str) -> None:
    await db_session.execute(
        text(f"UPDATE {table} SET search_vector = to_tsvector('english', :v) WHERE id = :id"),
        {"v": text_value, "id": row_id},
    )
    await db_session.commit()


async def test_search_messages_scoped_to_membership(client, db_session):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")

    channel = (
        await client.post(
            "/channels", json={"name": "search-test", "type": "public", "member_ids": []},
            headers=auth_header(alice),
        )
    ).json()
    message = (
        await client.post(
            f"/channels/{channel['id']}/messages",
            json={"content": "standup moved to 10am"},
            headers=auth_header(alice),
        )
    ).json()
    await _set_search_vector(db_session, "messages", message["id"], "standup moved to 10am")

    as_member = await client.get("/search", params={"q": "standup", "type": "messages"}, headers=auth_header(alice))
    as_stranger = await client.get("/search", params={"q": "standup", "type": "messages"}, headers=auth_header(bob))

    assert as_member.status_code == 200
    body = as_member.json()
    assert body["type"] == "messages"
    assert len(body["messages"]) == 1
    assert body["messages"][0]["id"] == message["id"]
    assert body["users"] is None and body["channels"] is None and body["files"] is None

    assert as_stranger.json()["messages"] == []


async def test_search_matches_on_any_word_not_all_of_them(client, db_session):
    # Regression: plainto_tsquery ANDs every query word together, so searching
    # "lunch meeting" against a message that only contains "lunch" (not
    # "meeting") used to return zero results — search felt broken for any
    # query that wasn't an exact word-for-word match.
    alice = await register_and_login(client, "alice@example.com")
    channel = (
        await client.post(
            "/channels", json={"name": "or-search-test", "type": "public", "member_ids": []},
            headers=auth_header(alice),
        )
    ).json()
    message = (
        await client.post(
            f"/channels/{channel['id']}/messages",
            json={"content": "quick lunch sync moved to tomorrow afternoon"},
            headers=auth_header(alice),
        )
    ).json()
    await _set_search_vector(db_session, "messages", message["id"], "quick lunch sync moved to tomorrow afternoon")

    response = await client.get(
        "/search", params={"q": "lunch meeting", "type": "messages"}, headers=auth_header(alice)
    )
    assert response.status_code == 200
    ids = [m["id"] for m in response.json()["messages"]]
    assert message["id"] in ids


async def test_search_users_is_not_membership_scoped(client, db_session):
    alice = await register_and_login(client, "alice@example.com")
    bob_tokens = await register_and_login(client, "bob@example.com", display_name="Bob Searchable")
    bob_id = (await client.get("/users/me", headers=auth_header(bob_tokens))).json()["id"]
    await _set_search_vector(db_session, "users", bob_id, "Bob Searchable bob@example.com")

    response = await client.get("/search", params={"q": "Searchable", "type": "users"}, headers=auth_header(alice))
    assert response.status_code == 200
    ids = [u["id"] for u in response.json()["users"]]
    assert bob_id in ids


async def test_search_channels_scoped_to_membership(client, db_session):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    channel = (
        await client.post(
            "/channels", json={"name": "engineering", "type": "public", "member_ids": []},
            headers=auth_header(alice),
        )
    ).json()
    await _set_search_vector(db_session, "channels", channel["id"], "engineering")

    as_member = await client.get("/search", params={"q": "engineering", "type": "channels"}, headers=auth_header(alice))
    as_stranger = await client.get("/search", params={"q": "engineering", "type": "channels"}, headers=auth_header(bob))
    assert len(as_member.json()["channels"]) == 1
    assert as_stranger.json()["channels"] == []


async def test_search_files_matches_filename_and_is_scoped(client, db_session):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    channel = (
        await client.post(
            "/channels", json={"name": "files-search", "type": "public", "member_ids": []},
            headers=auth_header(alice),
        )
    ).json()
    uploaded = (
        await client.post(
            "/files/upload",
            files={"file": ("quarterly-report.pdf", b"pdf bytes", "application/pdf")},
            headers=auth_header(alice),
        )
    ).json()
    await client.post(
        f"/channels/{channel['id']}/messages",
        json={"content": None, "attachment_ids": [uploaded["id"]]},
        headers=auth_header(alice),
    )

    as_member = await client.get("/search", params={"q": "quarterly", "type": "files"}, headers=auth_header(alice))
    as_stranger = await client.get("/search", params={"q": "quarterly", "type": "files"}, headers=auth_header(bob))
    assert len(as_member.json()["files"]) == 1
    assert as_member.json()["files"][0]["file_name"] == "quarterly-report.pdf"
    assert as_stranger.json()["files"] == []


async def test_search_requires_type(client):
    alice = await register_and_login(client, "alice@example.com")
    response = await client.get("/search", params={"q": "x"}, headers=auth_header(alice))
    assert response.status_code == 422
