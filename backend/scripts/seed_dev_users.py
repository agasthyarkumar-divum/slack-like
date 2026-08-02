"""Seed a handful of dev/test accounts (same password for all) plus a shared
channel with everyone in it, so you can log in as different people and chat
with yourself immediately — multiple browser tabs on the same machine, or
another device on the same network/tunnel pointed at the same API.

Idempotent: safe to re-run — existing users/memberships are skipped, not
duplicated.

Usage:
    python scripts/seed_dev_users.py
    python scripts/seed_dev_users.py --count 8 --password mypassword123
    python scripts/seed_dev_users.py --api-url http://localhost:8000
"""

import argparse
import asyncio
import os
import sys

import httpx

# Let `python scripts/seed_dev_users.py` (run from backend/) import the `app`
# package below — scripts/ itself isn't on sys.path by default.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEFAULT_NAMES = ["Alice", "Bob", "Carol", "Dave", "Erin", "Frank", "Grace", "Heidi", "Ivan", "Judy"]

# The first two seeded accounts double as standing admin/superAdmin fixtures
# for local dev — there's no HTTP path to mint the very first admin (the
# admin API itself requires an existing admin to call it), so this reaches
# around it with a direct DB write.
ROLE_PROMOTIONS = {"Alice": "superAdmin", "Bob": "admin"}


async def _promote_roles(promotions: dict[str, str]) -> None:
    """promotions: {email: scope_name}. Ensures the three canonical roles
    exist, then sets each user's role_id directly."""
    from sqlalchemy import select, update
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.config import settings
    from app.db.models import Role, User

    # A dedicated echo=False engine, not app.db.base's — that one echoes SQL
    # whenever APP_ENV=development, which is exactly this script's env.
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    try:
        async with SessionLocal() as db:
            role_ids: dict[str, object] = {}
            for name in ("users", "admin", "superAdmin"):
                result = await db.execute(select(Role).where(Role.name == name))
                role = result.scalar_one_or_none()
                if role is None:
                    role = Role(name=name)
                    db.add(role)
                    await db.flush()
                role_ids[name] = role.id
            await db.commit()

            for email, scope in promotions.items():
                await db.execute(update(User).where(User.email == email).values(role_id=role_ids[scope]))
            await db.commit()
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api-url", default="http://localhost:8000", help="Backend base URL.")
    parser.add_argument("--count", type=int, default=5, help=f"How many users (max {len(DEFAULT_NAMES)}).")
    parser.add_argument("--password", default="chatchatchat", help="Shared password for every seeded account.")
    parser.add_argument("--domain", default="example.com", help="Email domain for seeded accounts.")
    parser.add_argument("--channel", default="general", help="Shared channel name everyone gets added to.")
    args = parser.parse_args()

    if not (1 <= args.count <= len(DEFAULT_NAMES)):
        print(f"--count must be between 1 and {len(DEFAULT_NAMES)}", file=sys.stderr)
        sys.exit(1)

    client = httpx.Client(base_url=args.api_url, timeout=10)

    accounts: list[tuple[str, str]] = []  # (email, display_name)
    for name in DEFAULT_NAMES[: args.count]:
        email = f"{name.lower()}@{args.domain}"
        response = client.post(
            "/auth/register",
            json={"email": email, "password": args.password, "display_name": name},
        )
        if response.status_code == 201:
            print(f"  created    {email}")
        elif response.status_code == 409:
            print(f"  exists     {email}")
        else:
            print(f"  FAILED     {email} -> {response.status_code} {response.text}", file=sys.stderr)
            continue
        accounts.append((email, name))

    if not accounts:
        print("No accounts available — aborting.", file=sys.stderr)
        sys.exit(1)

    # Log in as everyone once to collect their user id + a token (need each
    # user's own token to fetch /users/me; the owner's token drives channel
    # creation/membership below).
    tokens: dict[str, str] = {}
    user_ids: dict[str, str] = {}
    for email, _name in accounts:
        login = client.post("/auth/login", json={"email": email, "password": args.password})
        login.raise_for_status()
        token = login.json()["access_token"]
        tokens[email] = token
        me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        me.raise_for_status()
        user_ids[email] = me.json()["id"]

    owner_email, _owner_name = accounts[0]
    owner_headers = {"Authorization": f"Bearer {tokens[owner_email]}"}

    channels = client.get("/channels", headers=owner_headers)
    channels.raise_for_status()
    existing = next((c for c in channels.json() if c["name"] == args.channel), None)

    if existing:
        channel_id = existing["id"]
        print(f"\nChannel #{args.channel} already exists — making sure everyone's a member.")
    else:
        member_ids = [user_ids[email] for email, _ in accounts[1:]]
        created = client.post(
            "/channels",
            json={"name": args.channel, "type": "public", "member_ids": member_ids},
            headers=owner_headers,
        )
        created.raise_for_status()
        channel_id = created.json()["id"]
        print(f"\nCreated #{args.channel} with all {len(accounts)} seeded users as members.")

    # Covers both "channel already existed with fewer members" and "freshly
    # created" (where the owner is already in it) — 409 on an existing member
    # is expected and fine.
    for email, _name in accounts:
        if user_ids[email] == user_ids[owner_email]:
            continue
        resp = client.post(
            f"/channels/{channel_id}/members",
            json={"user_id": user_ids[email]},
            headers=owner_headers,
        )
        if resp.status_code not in (201, 409):
            print(f"  WARNING: couldn't add {email} to #{args.channel}: {resp.status_code} {resp.text}", file=sys.stderr)

    promotions = {
        email: ROLE_PROMOTIONS[name] for email, name in accounts if name in ROLE_PROMOTIONS
    }
    if promotions:
        asyncio.run(_promote_roles(promotions))

    scopes = {name: ROLE_PROMOTIONS.get(name, "users") for _email, name in accounts}

    print("\n--- accounts (same password for all) ---")
    print(f"{'name':<8} {'email':<28} {'scope':<11} password")
    for email, name in accounts:
        print(f"{name:<8} {email:<28} {scopes[name]:<11} {args.password}")
    print(f"\nShared channel: #{args.channel}")
    print("\nLog in as any of these on as many tabs/devices as you like — they're all in the same channel.")


if __name__ == "__main__":
    main()
