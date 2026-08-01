"""Auth business logic (architecture.md §7): register, login, refresh rotation
with reuse detection, logout. DB access goes through repository.py; hashing and
JWTs go through core/security.py.
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.models import User
from app.modules.auth import repository


class AuthError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


async def register_user(db: AsyncSession, *, email: str, password: str, display_name: str) -> User:
    if await repository.get_user_by_email(db, email):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An account with this email already exists."
        )
    member_role = await repository.get_role_by_name(db, "member")
    user = await repository.create_user(
        db,
        email=email,
        hashed_password=hash_password(password),
        display_name=display_name,
        role_id=member_role.id if member_role else None,
    )
    await db.commit()
    return user


async def _issue_tokens(db: AsyncSession, user: User) -> tuple[str, str]:
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    await repository.create_session(
        db,
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    await db.commit()
    return access_token, refresh_token


async def login(db: AsyncSession, *, email: str, password: str) -> tuple[str, str]:
    user = await repository.get_user_by_email(db, email)
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        raise AuthError("Incorrect email or password.")
    return await _issue_tokens(db, user)


async def refresh_tokens(db: AsyncSession, *, refresh_token: str) -> tuple[str, str]:
    try:
        payload = decode_token(refresh_token, TokenType.REFRESH)
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid or expired refresh token.") from exc

    token_hash = hash_refresh_token(refresh_token)
    session_row = await repository.get_session_by_token_hash(db, token_hash)
    if session_row is None:
        raise AuthError("Invalid or expired refresh token.")

    if session_row.revoked_at is not None:
        # Reuse of an already-rotated/revoked refresh token — treat as compromise
        # and kill every session for the account (architecture.md §7 step 3).
        await repository.revoke_all_sessions_for_user(db, session_row.user_id)
        await db.commit()
        raise AuthError(
            "This session was revoked; all sessions for this account have been logged out."
        )

    if session_row.expires_at <= datetime.now(timezone.utc):
        raise AuthError("Invalid or expired refresh token.")

    user = await repository.get_user_by_id(db, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthError("Invalid or expired refresh token.")

    await repository.revoke_session(db, session_row)
    return await _issue_tokens(db, user)


async def logout(db: AsyncSession, *, refresh_token: str) -> None:
    token_hash = hash_refresh_token(refresh_token)
    session_row = await repository.get_session_by_token_hash(db, token_hash)
    if session_row is not None and session_row.revoked_at is None:
        await repository.revoke_session(db, session_row)
        await db.commit()
