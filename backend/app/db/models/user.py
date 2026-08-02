import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import UUIDPKMixin


class User(UUIDPKMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_uri: Mapped[str | None] = mapped_column(Text)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id")
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"))
    role_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"))
    status: Mapped[str | None] = mapped_column(String(20), server_default="offline")
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool | None] = mapped_column(Boolean, server_default="true")
    # 'all' | 'mentions_dms' | 'none' — read by notifications/service.notify_user
    # before creating a Notification row (Settings screen's radio group).
    notification_preference: Mapped[str | None] = mapped_column(String(20), server_default="all")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Populated by trg_users_search (BEFORE INSERT/UPDATE, see the migration) —
    # never set from application code.
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)
