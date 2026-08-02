import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AdminUserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_active: bool | None
    scope: str = Field(..., description="'users', 'admin', or 'superAdmin'.", examples=["admin"])
    department_id: uuid.UUID | None
    team_id: uuid.UUID | None
    created_at: datetime | None


class UpdateUserRoleRequest(BaseModel):
    scope: str = Field(
        ...,
        description="'users', 'admin', or 'superAdmin'.",
        examples=["admin"],
    )


class AuditLogOut(BaseModel):
    id: uuid.UUID
    actor_id: uuid.UUID | None = Field(None, description="Who performed the action.")
    action: str = Field(..., examples=["user.scope_updated"])
    target_type: str | None = Field(None, examples=["user"])
    target_id: uuid.UUID | None
    extra_data: dict | None = Field(None, description="Action-specific details, e.g. old/new scope.")
    created_at: datetime


class AdminStatsOut(BaseModel):
    total_users: int
    active_users: int
    total_channels: int
    total_messages: int
    users_active_today: int = Field(..., description="Users with last_seen == today (UTC).")
