"""Auth flow tests (architecture.md §7): register, login, refresh rotation +
reuse detection, logout, and the get_current_user dependency via /users/me.
"""

from sqlalchemy import select

from app.db.models import Role, Session as SessionModel


async def _register(client, email="alice@example.com", password="correct horse battery staple"):
    return await client.post(
        "/auth/register",
        json={"email": email, "password": password, "display_name": "Alice Example"},
    )


async def _register_and_login(client, email="alice@example.com", password="correct horse battery staple"):
    await _register(client, email, password)
    response = await client.post("/auth/login", json={"email": email, "password": password})
    return response.json()


async def test_register_creates_user(client):
    response = await _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["display_name"] == "Alice Example"
    assert "hashed_password" not in body  # never leaks the hash


async def test_register_duplicate_email_conflicts(client):
    await _register(client)
    response = await _register(client)
    assert response.status_code == 409


async def test_register_rejects_short_password(client):
    response = await client.post(
        "/auth/register",
        json={"email": "bob@example.com", "password": "short", "display_name": "Bob"},
    )
    assert response.status_code == 422


async def test_register_assigns_member_role_when_it_exists(client, db_session):
    role = Role(name="member")
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)

    response = await _register(client)
    assert response.status_code == 201
    assert response.json()["role_id"] == str(role.id)


async def test_login_success_returns_token_pair(client):
    await _register(client)
    response = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "correct horse battery staple"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]
    assert body["expires_in"] == 900


async def test_login_wrong_password_fails(client):
    await _register(client)
    response = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "wrong password"}
    )
    assert response.status_code == 401


async def test_login_unknown_email_fails(client):
    response = await client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "whatever12345"}
    )
    assert response.status_code == 401


async def test_me_requires_auth(client):
    response = await client.get("/users/me")
    assert response.status_code == 401


async def test_me_returns_current_user(client):
    tokens = await _register_and_login(client)
    response = await client.get(
        "/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


async def test_me_rejects_garbage_token(client):
    response = await client.get("/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


async def test_refresh_rotates_token_and_invalidates_the_old_one(client):
    tokens = await _register_and_login(client)

    refreshed = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # New access token works.
    me = await client.get(
        "/users/me", headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
    )
    assert me.status_code == 200

    # Old refresh token is now dead (rotated, not just still valid).
    reuse = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuse.status_code == 401


async def test_refresh_reuse_revokes_all_sessions_for_the_account(client, db_session):
    tokens = await _register_and_login(client)

    rotated = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    new_refresh_token = rotated.json()["refresh_token"]

    # Reusing the original (already-rotated) refresh token signals compromise.
    reuse = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuse.status_code == 401

    # The legitimately-rotated token should now ALSO be dead — every session for
    # the account was revoked as a precaution, not just the reused one.
    followup = await client.post("/auth/refresh", json={"refresh_token": new_refresh_token})
    assert followup.status_code == 401

    result = await db_session.execute(select(SessionModel))
    sessions = result.scalars().all()
    assert sessions and all(s.revoked_at is not None for s in sessions)


async def test_logout_revokes_the_session(client):
    tokens = await _register_and_login(client)

    logout = await client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logout.status_code == 204

    reuse = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuse.status_code == 401


async def test_logout_with_unknown_token_is_a_no_op(client):
    response = await client.post("/auth/logout", json={"refresh_token": "not-a-real-token"})
    assert response.status_code == 204
