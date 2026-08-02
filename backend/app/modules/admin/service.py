"""Admin business logic (architecture.md §6): user list, scope changes, audit
log, usage stats. Every scope change is written to audit_logs — the first
real writer that table has had since it was created in Phase 2.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog, User
from app.modules.admin import repository
from app.modules.auth import repository as auth_repository
from app.modules.auth.dependencies import SCOPE_ADMIN, SCOPE_SUPERADMIN, SCOPE_USERS

VALID_SCOPES = {SCOPE_USERS, SCOPE_ADMIN, SCOPE_SUPERADMIN}


async def list_users(db: AsyncSession) -> list[tuple[User, str]]:
    return await repository.list_users_with_scope(db)


async def update_user_role(
    db: AsyncSession,
    *,
    actor: User,
    actor_scope: str,
    target_user_id: uuid.UUID,
    new_scope: str,
) -> tuple[User, str]:
    if new_scope not in VALID_SCOPES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"scope must be one of {sorted(VALID_SCOPES)}."
        )
    if target_user_id == actor.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Can't change your own scope.")

    target = await repository.get_user_with_scope(db, target_user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    target_user, old_scope = target

    # A plain 'admin' may only move someone between 'users' <-> 'admin'.
    # Granting/revoking 'superAdmin', or touching an existing superAdmin's
    # scope at all, requires being a superAdmin — otherwise an admin could
    # promote themselves indirectly by demoting the only superAdmin, or mint
    # new superAdmins unchecked.
    if actor_scope != SCOPE_SUPERADMIN and (new_scope == SCOPE_SUPERADMIN or old_scope == SCOPE_SUPERADMIN):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only a superAdmin can grant or change superAdmin access."
        )

    new_role = await auth_repository.get_role_by_name(db, new_scope)
    if new_role is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Role '{new_scope}' isn't seeded.")

    target_user.role_id = new_role.id
    await repository.create_audit_log(
        db,
        actor_id=actor.id,
        action="user.scope_updated",
        target_type="user",
        target_id=target_user.id,
        metadata={"old_scope": old_scope, "new_scope": new_scope},
    )
    await db.commit()
    return target_user, new_scope


async def list_audit_logs(db: AsyncSession, *, limit: int) -> list[AuditLog]:
    return await repository.list_audit_logs(db, limit=limit)


async def get_stats(db: AsyncSession) -> dict:
    return await repository.get_stats(db)
