"""Celery task for the files pipeline (architecture.md §8): compress (if
beneficial, non-media only) -> encrypt via StorageBackend.save() -> thumbnail
(images only, via Pillow) -> update the attachments row -> emit ws "file.ready".

Doing this off the request path is what keeps upload latency low even for
large files — the API returns as soon as the row is created and the bytes are
staged, before any of the above happens (architecture.md §8).
"""

import asyncio
import io
import logging
import uuid
from pathlib import Path

import zstandard
from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.modules.files import repository
from app.storage.factory import get_storage_backend
from app.workers.celery_app import celery_app
from app.ws.manager import manager

logger = logging.getLogger(__name__)

# Already-compressed media formats don't benefit from a second compression pass.
_SKIP_COMPRESSION_PREFIXES = ("image/", "video/", "audio/")


def _should_compress(content_type: str) -> bool:
    return not content_type.startswith(_SKIP_COMPRESSION_PREFIXES)


def _make_thumbnail(raw_bytes: bytes) -> bytes | None:
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            img = img.convert("RGB")
            img.thumbnail((settings.THUMBNAIL_MAX_DIMENSION, settings.THUMBNAIL_MAX_DIMENSION))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return buf.getvalue()
    except UnidentifiedImageError:
        return None


async def _process_upload_async(
    *, attachment_id: str, temp_path: str, pending_key: str, content_type: str
) -> None:
    # A dedicated NullPool engine, scoped to this one asyncio.run() call: the
    # module-level app.db.base engine's asyncpg connections are bound to
    # whichever event loop created them, and each Celery task invocation here
    # gets a *fresh* event loop via asyncio.run() — reusing a pooled connection
    # across those would break with "Event loop is closed" on the second task.
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    storage = get_storage_backend()
    path = Path(temp_path)
    attachment_uuid = uuid.UUID(attachment_id)

    try:
        raw_bytes = path.read_bytes()

        payload, is_compressed = raw_bytes, False
        if _should_compress(content_type):
            compressed = zstandard.ZstdCompressor(level=10).compress(raw_bytes)
            if len(compressed) < len(raw_bytes):
                payload, is_compressed = compressed, True

        storage_key = f"attachments/{pending_key.removeprefix('pending/')}"
        storage_uri = await storage.save(storage_key, io.BytesIO(payload), content_type)

        thumbnail_uri = None
        if content_type.startswith("image/"):
            thumb_bytes = _make_thumbnail(raw_bytes)
            if thumb_bytes is not None:
                thumb_key = f"thumbnails/{pending_key.removeprefix('pending/')}.jpg"
                thumbnail_uri = await storage.save(thumb_key, io.BytesIO(thumb_bytes), "image/jpeg")

        async with session_maker() as db:
            attachment = await repository.get_attachment_by_id(db, attachment_uuid)
            if attachment is None:
                logger.warning("attachment %s vanished before processing completed", attachment_id)
                return
            attachment = await repository.mark_ready(
                db,
                attachment,
                storage_uri=storage_uri,
                thumbnail_uri=thumbnail_uri,
                is_compressed=is_compressed,
            )
            await db.commit()
            message_id = str(attachment.message_id) if attachment.message_id else None
            uploaded_by = str(attachment.uploaded_by) if attachment.uploaded_by else None

        if uploaded_by:
            await manager.send_to_user(
                uploaded_by,
                {
                    "event": "file.ready",
                    "data": {
                        "attachment_id": attachment_id,
                        "message_id": message_id,
                        "thumbnail_uri": thumbnail_uri,
                    },
                },
            )
    finally:
        path.unlink(missing_ok=True)
        await engine.dispose()
        # Same event-loop-affinity reasoning as the DB engine above, but for
        # the ws manager's Redis connection — reset it so the *next* task
        # invocation (new event loop) doesn't inherit a dead connection.
        await manager.close()


@celery_app.task(name="files.process_upload")
def process_upload(*, attachment_id: str, temp_path: str, pending_key: str, content_type: str) -> None:
    asyncio.run(
        _process_upload_async(
            attachment_id=attachment_id,
            temp_path=temp_path,
            pending_key=pending_key,
            content_type=content_type,
        )
    )
