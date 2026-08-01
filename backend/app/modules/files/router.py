import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.files import service
from app.modules.files.schemas import AttachmentOut
from app.storage.base import StorageBackend
from app.storage.factory import get_storage_backend

router = APIRouter(prefix="/files", tags=["files"])


@router.post(
    "/upload",
    response_model=AttachmentOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a file",
    description="Validates size, stores an attachments row immediately, and "
    "returns its id right away — a Celery task then compresses (if beneficial), "
    "encrypts, and thumbnails (images) it in the background (architecture.md §8). "
    "Poll `status` or wait for the `file.ready` WebSocket event.",
    responses={
        401: {"description": "Missing or invalid access token."},
        413: {"description": "File too large."},
        422: {"description": "Empty file."},
    },
)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttachmentOut:
    raw_bytes = await file.read()
    attachment = await service.upload_file(
        db,
        user_id=current_user.id,
        filename=file.filename,
        content_type=file.content_type,
        raw_bytes=raw_bytes,
    )
    return AttachmentOut.from_attachment(attachment)


@router.get(
    "/{attachment_id}",
    response_model=AttachmentOut,
    summary="Get attachment metadata / processing status",
    responses={
        401: {"description": "Missing or invalid access token."},
        404: {"description": "Not found, or you don't have access to it."},
    },
)
async def get_attachment(
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttachmentOut:
    attachment = await service.get_attachment(db, attachment_id=attachment_id, user_id=current_user.id)
    return AttachmentOut.from_attachment(attachment)


@router.get(
    "/{attachment_id}/download",
    summary="Download a file",
    description="Streams the decrypted file. (On the S3 backend this will "
    "302-redirect to a presigned URL instead — architecture.md §8; the local "
    "backend has no equivalent, so it proxies the bytes through the API.)",
    responses={
        401: {"description": "Missing or invalid access token."},
        404: {"description": "Not found, or you don't have access to it."},
        409: {"description": "Still processing — try again shortly."},
    },
)
async def download_file(
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    data, attachment = await service.download_file(
        db, attachment_id=attachment_id, user_id=current_user.id, storage=storage
    )
    filename = attachment.file_name or str(attachment.id)
    return Response(
        content=data,
        media_type=attachment.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{attachment_id}/thumbnail",
    summary="Download a file's thumbnail",
    responses={
        401: {"description": "Missing or invalid access token."},
        404: {"description": "Not found, no access, or no thumbnail exists for this file."},
    },
)
async def download_thumbnail(
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    data, _attachment = await service.download_thumbnail(
        db, attachment_id=attachment_id, user_id=current_user.id, storage=storage
    )
    return Response(content=data, media_type="image/jpeg")
