import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.messages import service
from app.modules.messages.schemas import (
    ForwardRequest,
    MessageCreate,
    MessageListResponse,
    MessageOut,
    MessageUpdate,
    ReactionCreate,
)

router = APIRouter(tags=["messages"])


@router.get(
    "/channels/{channel_id}/messages",
    response_model=MessageListResponse,
    summary="List messages in a channel",
    description="Cursor-paginated, newest first. Pass the previous response's "
    "`next_cursor` to get the next (older) page.",
    responses={
        401: {"description": "Missing or invalid access token."},
        404: {"description": "Channel not found, or you're not a member."},
        422: {"description": "Invalid cursor."},
    },
)
async def list_messages(
    channel_id: uuid.UUID,
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageListResponse:
    items, next_cursor = await service.list_messages(
        db, channel_id=channel_id, user_id=current_user.id, cursor=cursor, limit=limit
    )
    return MessageListResponse(
        items=[MessageOut.from_message(m) for m in items], next_cursor=next_cursor
    )


@router.post(
    "/channels/{channel_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message",
    responses={
        401: {"description": "Missing or invalid access token."},
        404: {"description": "Channel not found, or you're not a member."},
        422: {"description": "Validation error, or reply_to_id is in a different channel."},
    },
)
async def send_message(
    channel_id: uuid.UUID,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageOut:
    message = await service.send_message(
        db,
        channel_id=channel_id,
        sender_id=current_user.id,
        content=payload.content,
        reply_to_id=payload.reply_to_id,
        attachment_ids=payload.attachment_ids,
    )
    return MessageOut.from_message(message)


@router.patch(
    "/messages/{message_id}",
    response_model=MessageOut,
    summary="Edit a message",
    description="Sender only.",
    responses={
        401: {"description": "Missing or invalid access token."},
        403: {"description": "Not the sender of this message."},
        404: {"description": "Message not found."},
    },
)
async def edit_message(
    message_id: uuid.UUID,
    payload: MessageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageOut:
    message = await service.edit_message(
        db, message_id=message_id, user_id=current_user.id, content=payload.content
    )
    return MessageOut.from_message(message)


@router.delete(
    "/messages/{message_id}",
    response_model=MessageOut,
    summary="Delete a message",
    description="Soft delete — sender, or a channel owner/admin.",
    responses={
        401: {"description": "Missing or invalid access token."},
        403: {"description": "Not the sender, and not an owner/admin."},
        404: {"description": "Message not found."},
    },
)
async def delete_message(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageOut:
    message = await service.delete_message(db, message_id=message_id, user_id=current_user.id)
    return MessageOut.from_message(message)


@router.post(
    "/messages/{message_id}/reactions",
    response_model=MessageOut,
    summary="Toggle a reaction",
    description="Adds the reaction if the current user hasn't reacted with this "
    "emoji yet; removes it if they have.",
    responses={
        401: {"description": "Missing or invalid access token."},
        404: {"description": "Message not found, or you're not a member of its channel."},
    },
)
async def react_to_message(
    message_id: uuid.UUID,
    payload: ReactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageOut:
    message = await service.react_to_message(
        db, message_id=message_id, user_id=current_user.id, emoji=payload.emoji
    )
    return MessageOut.from_message(message)


@router.post(
    "/messages/{message_id}/pin",
    response_model=MessageOut,
    summary="Pin a message",
    description="Owner/admin only.",
    responses={
        401: {"description": "Missing or invalid access token."},
        403: {"description": "Not an owner/admin of this message's channel."},
        404: {"description": "Message not found."},
    },
)
async def pin_message(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageOut:
    message = await service.pin_message(
        db, message_id=message_id, user_id=current_user.id, pinned=True
    )
    return MessageOut.from_message(message)


@router.post(
    "/messages/{message_id}/unpin",
    response_model=MessageOut,
    summary="Unpin a message",
    description="Owner/admin only.",
    responses={
        401: {"description": "Missing or invalid access token."},
        403: {"description": "Not an owner/admin of this message's channel."},
        404: {"description": "Message not found."},
    },
)
async def unpin_message(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageOut:
    message = await service.pin_message(
        db, message_id=message_id, user_id=current_user.id, pinned=False
    )
    return MessageOut.from_message(message)


@router.post(
    "/messages/{message_id}/forward",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Forward a message",
    description="Copies the message's content into another channel you're a member of.",
    responses={
        401: {"description": "Missing or invalid access token."},
        404: {"description": "Message not found, or you're not a member of the source/target channel."},
    },
)
async def forward_message(
    message_id: uuid.UUID,
    payload: ForwardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageOut:
    message = await service.forward_message(
        db,
        message_id=message_id,
        user_id=current_user.id,
        target_channel_id=payload.target_channel_id,
    )
    return MessageOut.from_message(message)
