"""Test harness: a dedicated Postgres database (schema via Base.metadata, not
Alembic — auth tests only touch users/sessions/roles, none of which need the
FTS triggers or audit_logs partitioning that only exist in the migration), with
tables truncated before every test and `get_db` overridden to use it.

Requires real Postgres (not SQLite) since the schema uses UUID/JSONB/TSVECTOR
columns — point TEST_DATABASE_URL at the docker-compose `db` service, or let it
default to localhost:5432 (the port docker-compose publishes it on).
"""

import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://company_chat:change-me@localhost:5432/company_chat_test",
)

import asyncpg
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401 — registers all models on Base.metadata
from app.core.config import settings
from app.db.base import Base, get_db
from app.main import app as fastapi_app
from app.ws.manager import manager as ws_manager


@pytest_asyncio.fixture(autouse=True)
async def _reset_ws_manager():
    """The module-level `manager` singleton (imported by messages/service.py to
    broadcast) lazily opens a Redis connection tied to whatever event loop is
    running when it's first used. Since each test gets its own event loop
    (function-scoped), a connection left over from a previous test's now-closed
    loop breaks with "Event loop is closed" — close it before and after every
    test so it's always created fresh in the current one.
    """
    await ws_manager.close()
    yield
    await ws_manager.close()


async def _ensure_database_exists(db_url: str) -> None:
    """asyncpg has no `CREATE DATABASE IF NOT EXISTS` — check pg_database first."""
    base_url, _, db_name = db_url.rpartition("/")
    admin_dsn = (base_url + "/postgres").replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(admin_dsn)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()


@pytest_asyncio.fixture()
async def engine():
    # create_all(checkfirst=True) only creates *missing* tables — it never
    # alters an existing one. If a model gains/loses a column, the test DB
    # (persisted across runs, only its row data gets truncated per-test) goes
    # stale until it's dropped: `DROP DATABASE company_chat_test;` via psql,
    # then it's recreated fresh here on the next run.
    await _ensure_database_exists(settings.DATABASE_URL)
    eng = create_async_engine(settings.DATABASE_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture()
async def db_session(engine):
    """Direct DB access for test setup/assertions outside the app's own
    request-scoped sessions (e.g. seeding a Role row, or asserting on Session rows).
    """
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session


@pytest_asyncio.fixture()
async def client(engine):
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE sessions, users, roles, channels, channel_members, "
                "messages, reactions, message_reads, attachments, notifications "
                "RESTART IDENTITY CASCADE"
            )
        )

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()
