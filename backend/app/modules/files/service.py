import hashlib
import uuid
from pathlib import Path

import zstandard
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Attachment
from app.modules.channels.service import require_membership
from app.modules.files import repository
from app.modules.messages import repository as messages_repository
from app.storage.base import StorageBackend


async def upload_file(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    filename: str | None,
    content_type: str | None,
    raw_bytes: bytes,
) -> Attachment:
    if len(raw_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds the {settings.MAX_UPLOAD_SIZE_BYTES} byte limit.",
        )
    if not raw_bytes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Uploaded file is empty.")

    checksum = hashlib.sha256(raw_bytes).hexdigest()
    pending_key = f"pending/{uuid.uuid4()}"

    attachment = await repository.create_pending_attachment(
        db,
        uploaded_by=user_id,
        file_name=filename,
        mime_type=content_type,
        size_bytes=len(raw_bytes),
        checksum=checksum,
        pending_key=pending_key,
    )
    await db.commit()
    await db.refresh(attachment)

    # Staged on the same shared `uploads` volume the api/worker containers both
    # mount — a hand-off point between processes, distinct from the final
    # StorageBackend-managed location the Celery task writes to.
    temp_path = Path(settings.LOCAL_STORAGE_PATH) / "_incoming" / f"{attachment.id}.upload"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_bytes(raw_bytes)

    from app.workers.tasks_files import process_upload  # local import: avoid import at module load

    process_upload.delay(
        attachment_id=str(attachment.id),
        temp_path=str(temp_path),
        pending_key=pending_key,
        content_type=content_type or "application/octet-stream",
    )
    return attachment


async def _require_access(db: AsyncSession, attachment: Attachment | None, user_id: uuid.UUID) -> Attachment:
    if attachment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found.")
    if attachment.message_id is not None:
        message = await messages_repository.get_message_by_id(db, attachment.message_id)
        if message is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found.")
        await require_membership(db, channel_id=message.channel_id, user_id=user_id)
    elif attachment.uploaded_by != user_id:
        # Not attached to any message yet — only the uploader can see it.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found.")
    return attachment


async def get_attachment(db: AsyncSession, *, attachment_id: uuid.UUID, user_id: uuid.UUID) -> Attachment:
    attachment = await repository.get_attachment_by_id(db, attachment_id)
    return await _require_access(db, attachment, user_id)


def _strip_uri_scheme(uri: str) -> str:
    # local://key -> key. (S3 URIs would be handled via get_presigned_url()
    # instead of load()+strip once S3Backend is implemented — architecture.md §8.)
    return uri.split("://", 1)[1]


async def download_file(
    db: AsyncSession, *, attachment_id: uuid.UUID, user_id: uuid.UUID, storage: StorageBackend
) -> tuple[bytes, Attachment]:
    attachment = await get_attachment(db, attachment_id=attachment_id, user_id=user_id)
    if attachment.storage_uri.startswith("pending://"):
        raise HTTPException(status.HTTP_409_CONFLICT, "File is still processing.")
    data = await storage.load(_strip_uri_scheme(attachment.storage_uri))
    if attachment.is_compressed:
        data = zstandard.ZstdDecompressor().decompress(data)
    return data, attachment


async def download_thumbnail(
    db: AsyncSession, *, attachment_id: uuid.UUID, user_id: uuid.UUID, storage: StorageBackend
) -> tuple[bytes, Attachment]:
    attachment = await get_attachment(db, attachment_id=attachment_id, user_id=user_id)
    if not attachment.thumbnail_uri:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No thumbnail for this file.")
    data = await storage.load(_strip_uri_scheme(attachment.thumbnail_uri))
    return data, attachment
