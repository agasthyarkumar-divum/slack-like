"""GET /users/{id} — public profile lookup by id, used by the mobile client to
resolve display names for message senders, typing indicators, and DM titles.
"""

from app.tests.helpers import auth_header, register_and_login


async def test_get_user_by_id(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com", display_name="Bob Example")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]

    response = await client.get(f"/users/{bob_id}", headers=auth_header(alice))
    assert response.status_code == 200
    assert response.json()["display_name"] == "Bob Example"


async def test_get_user_by_id_requires_auth(client):
    alice = await register_and_login(client, "alice@example.com")
    alice_id = (await client.get("/users/me", headers=auth_header(alice))).json()["id"]

    response = await client.get(f"/users/{alice_id}")
    assert response.status_code == 401


async def test_get_user_by_id_404_for_unknown_user(client):
    alice = await register_and_login(client, "alice@example.com")
    response = await client.get(
        "/users/00000000-0000-0000-0000-000000000000", headers=auth_header(alice)
    )
    assert response.status_code == 404
