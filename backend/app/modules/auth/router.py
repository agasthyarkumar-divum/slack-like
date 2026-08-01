from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import get_db
from app.db.models import User
from app.modules.auth import service
from app.modules.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.modules.users.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
    description="Registers a new user with an argon2-hashed password. Assigns the "
    "default 'member' role if one exists (architecture.md §7).",
    responses={
        409: {"description": "An account with this email already exists."},
        422: {"description": "Validation error."},
    },
)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> User:
    return await service.register_user(
        db, email=payload.email, password=payload.password, display_name=payload.display_name
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange credentials for an access + refresh token pair",
    description="Verifies the password against the stored argon2 hash and issues a "
    "short-lived access JWT plus a long-lived refresh JWT. The refresh token's hash "
    "is stored in `sessions` for revocation (architecture.md §7).",
    responses={
        401: {"description": "Incorrect email or password."},
        422: {"description": "Validation error."},
    },
)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    access_token, refresh_token = await service.login(
        db, email=payload.email, password=payload.password
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate a refresh token for a new access + refresh token pair",
    description="Validates the refresh token's signature and its `sessions` row "
    "(not revoked, not expired), then rotates it — the old session is revoked and "
    "a new one issued. Reusing an already-rotated refresh token is treated as a "
    "compromise signal and revokes every session on the account (architecture.md §7).",
    responses={
        401: {"description": "Invalid, expired, or reused refresh token."},
        422: {"description": "Validation error."},
    },
)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    access_token, refresh_token = await service.refresh_tokens(
        db, refresh_token=payload.refresh_token
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a session",
    description="Marks the session behind the given refresh token as revoked. The "
    "paired access token keeps working until it naturally expires within its short "
    "TTL (architecture.md §7) — it isn't blocklisted.",
    responses={422: {"description": "Validation error."}},
)
async def logout(payload: LogoutRequest, db: AsyncSession = Depends(get_db)) -> None:
    await service.logout(db, refresh_token=payload.refresh_token)
