import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDPKMixin


class Message(UUIDPKMixin, Base):
    __tablename__ = "messages"

    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE")
    )
    sender_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    content: Mapped[str | None] = mapped_column(Text)
    reply_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id")
    )
    forwarded_from_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id")
    )
    is_pinned: Mapped[bool | None] = mapped_column(Boolean, server_default="false")
    is_edited: Mapped[bool | None] = mapped_column(Boolean, server_default="false")
    is_deleted: Mapped[bool | None] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Populated by trg_messages_search (BEFORE INSERT/UPDATE, see the migration).
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)

    # Default (lazy="select") strategy — async SQLAlchemy runs an implicit
    # lazy-load via a greenlet bridge if this is ever accessed unloaded, so it
    # degrades to an extra query rather than crashing. list/get repository
    # functions eager-load it via selectinload() for the hot paths regardless.
    attachments: Mapped[list["Attachment"]] = relationship(foreign_keys="Attachment.message_id")


class Attachment(UUIDPKMixin, Base):
    """architecture.md §5 doesn't include an `uploaded_by` column, but §8's flow
    uploads a file (and returns its id) *before* it's attached to a message —
    without recording who uploaded it, there'd be no way to enforce that only
    the uploader can access a not-yet-attached attachment (message_id NULL), so
    any authenticated user could download any pending upload by guessing its
    UUID. Added here, matching the sender_id/created_by pattern used elsewhere.
    """

    __tablename__ = "attachments"

    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE")
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_uri: Mapped[str | None] = mapped_column(Text)
    file_name: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    is_encrypted: Mapped[bool | None] = mapped_column(Boolean, server_default="true")
    is_compressed: Mapped[bool | None] = mapped_column(Boolean, server_default="false")
    checksum: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Reaction(Base):
    __tablename__ = "reactions"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    emoji: Mapped[str] = mapped_column(String(20), primary_key=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MessageRead(Base):
    __tablename__ = "message_reads"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
