"""Password hashing, JWT issue/verify, and refresh-token hashing (architecture.md §7)."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from enum import StrEnum

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_password_hasher = PasswordHasher()


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _password_hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False


def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: uuid.UUID) -> str:
    return _create_token(
        str(user_id), TokenType.ACCESS, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(
        str(user_id), TokenType.REFRESH, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )


def decode_token(token: str, expected_type: TokenType) -> dict:
    """Raises a jwt.PyJWTError subclass if the token is malformed, unsigned by us,
    expired, or not the expected type (access vs. refresh)."""
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != expected_type.value:
        raise jwt.InvalidTokenError(f"expected a {expected_type.value} token")
    return payload


def hash_refresh_token(raw_token: str) -> str:
    """Refresh tokens are high-entropy signed JWTs, so a plain fast hash (not argon2)
    is fine for at-rest storage in `sessions.refresh_token_hash` — brute-forcing a
    200+ byte signed token is infeasible regardless of hash speed. This also makes
    session lookup a deterministic equality match, which argon2's per-hash random
    salt doesn't support.
    """
    return hashlib.sha256(raw_token.encode()).hexdigest()
