import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Attachment


async def create_pending_attachment(
    db: AsyncSession,
    *,
    uploaded_by: uuid.UUID,
    file_name: str | None,
    mime_type: str | None,
    size_bytes: int,
    checksum: str,
    pending_key: str,
) -> Attachment:
    attachment = Attachment(
        uploaded_by=uploaded_by,
        file_name=file_name,
        mime_type=mime_type,
        size_bytes=size_bytes,
        checksum=checksum,
        storage_uri=f"pending://{pending_key}",
        is_encrypted=False,
        is_compressed=False,
    )
    db.add(attachment)
    await db.flush()
    await db.refresh(attachment)
    return attachment


async def get_attachment_by_id(db: AsyncSession, attachment_id: uuid.UUID) -> Attachment | None:
    return await db.get(Attachment, attachment_id)


async def mark_ready(
    db: AsyncSession,
    attachment: Attachment,
    *,
    storage_uri: str,
    thumbnail_uri: str | None,
    is_compressed: bool,
) -> Attachment:
    attachment.storage_uri = storage_uri
    attachment.thumbnail_uri = thumbnail_uri
    attachment.is_compressed = is_compressed
    attachment.is_encrypted = True
    await db.flush()
    await db.refresh(attachment)
    return attachment


async def attach_to_message(db: AsyncSession, attachment: Attachment, message_id: uuid.UUID) -> None:
    attachment.message_id = message_id
    await db.flush()
