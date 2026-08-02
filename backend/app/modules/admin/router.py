import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.modules.admin import service
from app.modules.admin.schemas import AdminStatsOut, AdminUserOut, AuditLogOut, UpdateUserRoleRequest
from app.modules.auth.dependencies import get_current_scope, require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


def _to_admin_user_out(user: User, scope: str) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        scope=scope,
        department_id=user.department_id,
        team_id=user.team_id,
        created_at=user.created_at,
    )


@router.get(
    "/users",
    response_model=list[AdminUserOut],
    summary="List all users",
    description="Requires 'admin' scope or higher (architecture.md §6).",
    responses={
        401: {"description": "Missing or invalid access token."},
        403: {"description": "Requires 'admin' scope or higher."},
    },
)
async def list_users(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(require_admin)
) -> list[AdminUserOut]:
    rows = await service.list_users(db)
    return [_to_admin_user_out(user, scope) for user, scope in rows]


@router.patch(
    "/users/{user_id}/role",
    response_model=AdminUserOut,
    summary="Change a user's scope",
    description="Requires 'admin' scope or higher. A plain admin can only move "
    "someone between 'users' and 'admin' — granting/revoking 'superAdmin', or "
    "changing an existing superAdmin's scope at all, requires 'superAdmin'. "
    "Every change is written to the audit log. Note: the target's *current* "
    "access token keeps its old scope until it's refreshed or they log in "
    "again — scope is a token claim, not re-checked against the DB per request.",
    responses={
        401: {"description": "Missing or invalid access token."},
        403: {"description": "Insufficient scope for this change."},
        404: {"description": "User not found."},
        422: {"description": "Invalid scope, or trying to change your own."},
    },
)
async def update_user_role(
    user_id: uuid.UUID,
    payload: UpdateUserRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    current_scope: str = Depends(get_current_scope),
) -> AdminUserOut:
    target_user, new_scope = await service.update_user_role(
        db,
        actor=current_user,
        actor_scope=current_scope,
        target_user_id=user_id,
        new_scope=payload.scope,
    )
    return _to_admin_user_out(target_user, new_scope)


@router.get(
    "/audit-logs",
    response_model=list[AuditLogOut],
    summary="List recent audit log entries",
    description="Requires 'admin' scope or higher. Newest first.",
    responses={
        401: {"description": "Missing or invalid access token."},
        403: {"description": "Requires 'admin' scope or higher."},
    },
)
async def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[AuditLogOut]:
    logs = await service.list_audit_logs(db, limit=limit)
    return [
        AuditLogOut(
            id=log.id,
            actor_id=log.actor_id,
            action=log.action,
            target_type=log.target_type,
            target_id=log.target_id,
            extra_data=log.extra_data,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get(
    "/stats",
    response_model=AdminStatsOut,
    summary="Usage stats",
    description="Requires 'admin' scope or higher.",
    responses={
        401: {"description": "Missing or invalid access token."},
        403: {"description": "Requires 'admin' scope or higher."},
    },
)
async def get_stats(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(require_admin)
) -> AdminStatsOut:
    stats = await service.get_stats(db)
    return AdminStatsOut(**stats)
