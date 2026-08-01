import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models import Attachment


class AttachmentOut(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID | None
    file_name: str | None
    mime_type: str | None
    size_bytes: int | None
    is_encrypted: bool | None
    is_compressed: bool | None
    checksum: str | None = Field(None, description="SHA-256 of the original upload, for integrity verification.")
    created_at: datetime | None
    status: str = Field(
        ..., description="'processing' while the Celery task runs, 'ready' once downloadable."
    )
    has_thumbnail: bool = Field(..., description="True once a thumbnail has been generated.")

    @classmethod
    def from_attachment(cls, attachment: Attachment) -> "AttachmentOut":
        return cls(
            id=attachment.id,
            message_id=attachment.message_id,
            file_name=attachment.file_name,
            mime_type=attachment.mime_type,
            size_bytes=attachment.size_bytes,
            is_encrypted=attachment.is_encrypted,
            is_compressed=attachment.is_compressed,
            checksum=attachment.checksum,
            created_at=attachment.created_at,
            status="processing" if attachment.storage_uri.startswith("pending://") else "ready",
            has_thumbnail=bool(attachment.thumbnail_uri),
        )
