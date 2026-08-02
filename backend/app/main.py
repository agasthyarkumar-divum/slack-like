"""FastAPI application entrypoint (architecture.md §1, §4).

Feature routers (auth, users, channels, messages, files, search, notifications,
admin) and the WS router are included here as each module lands, phase by phase.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.channels.router import router as channels_router
from app.modules.files.router import router as files_router
from app.modules.messages.router import router as messages_router
from app.modules.notifications.router import router as notifications_router
from app.modules.search.router import router as search_router
from app.modules.users.router import router as users_router
from app.ws.manager import manager as ws_manager
from app.ws.router import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await ws_manager.close()


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Internal team chat API: channels, direct messages, files, search, and "
        "realtime presence over WebSockets. See /redoc for the full data model "
        "and docs/websocket-events.md for the WebSocket wire protocol."
    ),
    version=settings.APP_VERSION,
    contact={"name": settings.COMPANY_NAME},
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Browsers hide non-"safe" response headers from JS on cross-origin
    # requests unless the server explicitly opts in — without this, the
    # mobile web client's axios calls would see these headers as absent even
    # though they're actually on the wire.
    expose_headers=["X-App-Id", "X-User-Id", "X-Scope"],
)


@app.middleware("http")
async def add_identity_headers(request: Request, call_next):
    """X-App-Id on every response; X-User-Id/X-Scope on authenticated ones —
    get_current_user (modules/auth/dependencies.py) sets request.state during
    routing, which is what this reads once the handler has run.
    """
    response = await call_next(request)
    response.headers["X-App-Id"] = settings.APP_ID
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        response.headers["X-User-Id"] = user_id
    scope = getattr(request.state, "scope", None)
    if scope:
        response.headers["X-Scope"] = scope
    return response


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(channels_router)
app.include_router(messages_router)
app.include_router(files_router)
app.include_router(search_router)
app.include_router(notifications_router)
app.include_router(admin_router)
app.include_router(ws_router)


@app.get(
    "/health",
    tags=["health"],
    summary="Liveness check",
    description="Returns 200 with basic app metadata if the API process is up. "
    "Does not check downstream dependencies (DB, Redis) — used for container "
    "liveness probes.",
)
async def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
