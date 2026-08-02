"""RBAC + admin module tests: scope gating, tiered role-change permissions,
audit logging, stats, and the identity response headers.
"""

from sqlalchemy import select

from app.db.models import AuditLog, Role
from app.tests.helpers import auth_header, register_and_login


async def _seed_roles(db_session) -> dict[str, str]:
    ids = {}
    for name in ("users", "admin", "superAdmin"):
        role = Role(name=name)
        db_session.add(role)
        await db_session.flush()
        ids[name] = str(role.id)
    await db_session.commit()
    return ids


async def _promote(client, db_session, role_ids, email, password, scope) -> dict:
    """Set role_id directly (bypassing the permission-gated endpoint, since
    this is test setup, not the thing under test), then re-login — scope is
    a token claim from login time, so a DB-level role change needs a fresh
    token to actually take effect (see the endpoint's own docstring)."""
    from sqlalchemy import update as sa_update

    from app.db.models import User

    await db_session.execute(
        sa_update(User).where(User.email == email).values(role_id=role_ids[scope])
    )
    await db_session.commit()
    response = await client.post("/auth/login", json={"email": email, "password": password})
    return response.json()


async def test_list_users_requires_admin_scope(client, db_session):
    await _seed_roles(db_session)
    plain_user = await register_and_login(client, "alice@example.com")
    response = await client.get("/admin/users", headers=auth_header(plain_user))
    assert response.status_code == 403


async def test_list_users_as_admin_works(client, db_session):
    role_ids = await _seed_roles(db_session)
    await register_and_login(client, "alice@example.com")
    admin = await _promote(client, db_session, role_ids, "alice@example.com", "correct horse battery staple", "admin")

    response = await client.get("/admin/users", headers=auth_header(admin))
    assert response.status_code == 200
    emails = {u["email"] for u in response.json()}
    assert "alice@example.com" in emails
    alice_row = next(u for u in response.json() if u["email"] == "alice@example.com")
    assert alice_row["scope"] == "admin"


async def test_admin_can_promote_between_users_and_admin_but_not_superadmin(client, db_session):
    role_ids = await _seed_roles(db_session)
    await register_and_login(client, "alice@example.com")
    admin = await _promote(client, db_session, role_ids, "alice@example.com", "correct horse battery staple", "admin")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]

    ok = await client.patch(
        f"/admin/users/{bob_id}/role", json={"scope": "admin"}, headers=auth_header(admin)
    )
    assert ok.status_code == 200
    assert ok.json()["scope"] == "admin"

    forbidden = await client.patch(
        f"/admin/users/{bob_id}/role", json={"scope": "superAdmin"}, headers=auth_header(admin)
    )
    assert forbidden.status_code == 403


async def test_admin_cannot_touch_an_existing_superadmin(client, db_session):
    role_ids = await _seed_roles(db_session)
    await register_and_login(client, "alice@example.com")
    admin = await _promote(client, db_session, role_ids, "alice@example.com", "correct horse battery staple", "admin")
    await register_and_login(client, "root@example.com")
    root = await _promote(client, db_session, role_ids, "root@example.com", "correct horse battery staple", "superAdmin")
    root_id = (await client.get("/users/me", headers=auth_header(root))).json()["id"]

    response = await client.patch(
        f"/admin/users/{root_id}/role", json={"scope": "users"}, headers=auth_header(admin)
    )
    assert response.status_code == 403


async def test_superadmin_can_grant_and_revoke_superadmin(client, db_session):
    role_ids = await _seed_roles(db_session)
    await register_and_login(client, "root@example.com")
    root = await _promote(client, db_session, role_ids, "root@example.com", "correct horse battery staple", "superAdmin")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]

    promoted = await client.patch(
        f"/admin/users/{bob_id}/role", json={"scope": "superAdmin"}, headers=auth_header(root)
    )
    assert promoted.status_code == 200
    assert promoted.json()["scope"] == "superAdmin"

    demoted = await client.patch(
        f"/admin/users/{bob_id}/role", json={"scope": "users"}, headers=auth_header(root)
    )
    assert demoted.status_code == 200
    assert demoted.json()["scope"] == "users"


async def test_cannot_change_own_scope(client, db_session):
    role_ids = await _seed_roles(db_session)
    await register_and_login(client, "root@example.com")
    root = await _promote(client, db_session, role_ids, "root@example.com", "correct horse battery staple", "superAdmin")
    root_id = (await client.get("/users/me", headers=auth_header(root))).json()["id"]

    response = await client.patch(
        f"/admin/users/{root_id}/role", json={"scope": "admin"}, headers=auth_header(root)
    )
    assert response.status_code == 422


async def test_invalid_scope_rejected(client, db_session):
    role_ids = await _seed_roles(db_session)
    await register_and_login(client, "root@example.com")
    root = await _promote(client, db_session, role_ids, "root@example.com", "correct horse battery staple", "superAdmin")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]

    response = await client.patch(
        f"/admin/users/{bob_id}/role", json={"scope": "wizard"}, headers=auth_header(root)
    )
    assert response.status_code == 422


async def test_role_update_writes_an_audit_log_entry(client, db_session):
    role_ids = await _seed_roles(db_session)
    await register_and_login(client, "root@example.com")
    root = await _promote(client, db_session, role_ids, "root@example.com", "correct horse battery staple", "superAdmin")
    bob = await register_and_login(client, "bob@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]

    await client.patch(f"/admin/users/{bob_id}/role", json={"scope": "admin"}, headers=auth_header(root))

    result = await db_session.execute(select(AuditLog).where(AuditLog.action == "user.scope_updated"))
    entries = result.scalars().all()
    assert len(entries) == 1
    assert str(entries[0].target_id) == bob_id
    assert entries[0].extra_data == {"old_scope": "users", "new_scope": "admin"}

    audit_response = await client.get("/admin/audit-logs", headers=auth_header(root))
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["action"] == "user.scope_updated"


async def test_audit_logs_requires_admin_scope(client, db_session):
    await _seed_roles(db_session)
    plain_user = await register_and_login(client, "alice@example.com")
    response = await client.get("/admin/audit-logs", headers=auth_header(plain_user))
    assert response.status_code == 403


async def test_stats_requires_admin_and_returns_counts(client, db_session):
    role_ids = await _seed_roles(db_session)
    await register_and_login(client, "alice@example.com")
    admin = await _promote(client, db_session, role_ids, "alice@example.com", "correct horse battery staple", "admin")
    await register_and_login(client, "bob@example.com")

    response = await client.get("/admin/stats", headers=auth_header(admin))
    assert response.status_code == 200
    body = response.json()
    assert body["total_users"] >= 2
    assert "total_channels" in body and "total_messages" in body


async def test_identity_headers_present_on_authenticated_response(client, db_session):
    await _seed_roles(db_session)
    tokens = await register_and_login(client, "alice@example.com")
    me_id = (await client.get("/users/me", headers=auth_header(tokens))).json()["id"]

    response = await client.get("/users/me", headers=auth_header(tokens))
    assert response.headers["x-user-id"] == me_id
    assert response.headers["x-scope"] == "users"
    assert response.headers["x-app-id"]  # present, non-empty


async def test_identity_headers_absent_on_unauthenticated_response(client):
    response = await client.get("/health")
    assert "x-user-id" not in response.headers
    assert "x-scope" not in response.headers
    assert response.headers["x-app-id"]  # app id is always present
