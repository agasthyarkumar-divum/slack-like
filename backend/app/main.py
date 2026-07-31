"""FastAPI application entrypoint (architecture.md §1, §4).

Feature routers (auth, users, channels, messages, files, search, notifications,
admin) and the WS router are included here as each module lands, phase by phase.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router

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
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)


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
