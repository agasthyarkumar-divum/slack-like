import uuid

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenType, decode_token
from app.db.base import get_db
from app.db.models import User
from app.modules.auth import repository

_bearer_scheme = HTTPBearer(auto_error=False)

# Scopes, weakest to strongest — architecture kickoff note: "scopes must be
# superAdmin, admin and users". Order matters for the `>=` comparisons the
# require_admin/require_superadmin dependencies use.
SCOPE_USERS = "users"
SCOPE_ADMIN = "admin"
SCOPE_SUPERADMIN = "superAdmin"
_SCOPE_RANK = {SCOPE_USERS: 0, SCOPE_ADMIN: 1, SCOPE_SUPERADMIN: 2}


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        payload = decode_token(credentials.credentials, TokenType.ACCESS)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError) as exc:
        raise unauthorized from exc

    user = await repository.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise unauthorized

    # Picked up by the identity-headers middleware (main.py) to set
    # X-User-Id / X-Scope on the response — set here so it reflects the
    # *token's* scope claim (matches what actually gated this request)
    # without a second DB round-trip to re-derive it from user.role_id.
    request.state.user_id = str(user.id)
    request.state.scope = payload.get("scope", SCOPE_USERS)
    return user


def _require_min_scope(min_scope: str):
    async def _check(request: Request, current_user: User = Depends(get_current_user)) -> User:
        scope = getattr(request.state, "scope", SCOPE_USERS)
        if _SCOPE_RANK.get(scope, 0) < _SCOPE_RANK[min_scope]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires '{min_scope}' scope or higher.")
        return current_user

    return _check


require_admin = _require_min_scope(SCOPE_ADMIN)
require_superadmin = _require_min_scope(SCOPE_SUPERADMIN)


async def get_current_scope(request: Request) -> str:
    """For endpoints that need the exact scope, not just a yes/no gate — e.g.
    admin role-update, where a plain 'admin' and a 'superAdmin' are allowed
    different things (modules/admin/service.py)."""
    return getattr(request.state, "scope", SCOPE_USERS)
