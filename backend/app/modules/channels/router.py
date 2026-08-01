import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.channels import service
from app.modules.channels.schemas import (
    ChannelCreate,
    ChannelMemberAdd,
    ChannelMemberOut,
    ChannelOut,
    ChannelUpdate,
)

router = APIRouter(prefix="/channels", tags=["channels"])


@router.post(
    "",
    response_model=ChannelOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a channel",
    description="Creates a channel and adds the creator as its owner, plus any "
    "`member_ids` given as regular members.",
    responses={401: {"description": "Missing or invalid access token."}, 422: {"description": "Validation error."}},
)
async def create_channel(
    payload: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChannelOut:
    channel = await service.create_channel(
        db,
        creator_id=current_user.id,
        name=payload.name,
        type=payload.type,
        topic=payload.topic,
        member_ids=payload.member_ids,
    )
    return ChannelOut.model_validate(channel)


@router.post(
    "/dm/{other_user_id}",
    response_model=ChannelOut,
    summary="Start (or open) a DM with a user",
    description="Returns the existing DM channel with this user if one exists, "
    "otherwise creates it — never creates duplicates.",
    responses={
        401: {"description": "Missing or invalid access token."},
        404: {"description": "User not found."},
        422: {"description": "Can't start a DM with yourself."},
    },
)
async def get_or_create_dm(
    other_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChannelOut:
    channel = await service.get_or_create_dm(db, user_id=current_user.id, other_user_id=other_user_id)
    return ChannelOut.model_validate(channel)


@router.get(
    "",
    response_model=list[ChannelOut],
    summary="List my channels",
    description="Returns every channel the current user is a member of, newest first.",
    responses={401: {"description": "Missing or invalid access token."}},
)
async def list_my_channels(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[ChannelOut]:
    channels_with_counts = await service.list_my_channels(db, current_user.id)
    return [
        ChannelOut(**ChannelOut.model_validate(channel).model_dump(exclude={"unread_count"}), unread_count=count)
        for channel, count in channels_with_counts
    ]


@router.get(
    "/{channel_id}",
    response_model=ChannelOut,
    summary="Get a channel",
    responses={
        401: {"description": "Missing or invalid access token."},
        404: {"description": "Channel not found, or you're not a member."},
    },
)
async def get_channel(
    channel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChannelOut:
    channel = await service.get_channel(db, channel_id=channel_id, user_id=current_user.id)
    return ChannelOut.model_validate(channel)


@router.patch(
    "/{channel_id}",
    response_model=ChannelOut,
    summary="Update a channel",
    description="Owner/admin only.",
    responses={
        401: {"description": "Missing or invalid access token."},
        403: {"description": "Not an owner/admin of this channel."},
        404: {"description": "Channel not found, or you're not a member."},
    },
)
async def update_channel(
    channel_id: uuid.UUID,
    payload: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChannelOut:
    channel = await service.update_channel(
        db,
        channel_id=channel_id,
        user_id=current_user.id,
        name=payload.name,
        topic=payload.topic,
    )
    return ChannelOut.model_validate(channel)


@router.get(
    "/{channel_id}/members",
    response_model=list[ChannelMemberOut],
    summary="List channel members",
    responses={
        401: {"description": "Missing or invalid access token."},
        404: {"description": "Channel not found, or you're not a member."},
    },
)
async def list_members(
    channel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChannelMemberOut]:
    members = await service.list_members(db, channel_id=channel_id, user_id=current_user.id)
    return [ChannelMemberOut.model_validate(m) for m in members]


@router.post(
    "/{channel_id}/members",
    response_model=ChannelMemberOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member",
    description="Owner/admin only.",
    responses={
        401: {"description": "Missing or invalid access token."},
        403: {"description": "Not an owner/admin of this channel."},
        404: {"description": "Channel not found, or you're not a member."},
        409: {"description": "That user is already a member."},
    },
)
async def add_member(
    channel_id: uuid.UUID,
    payload: ChannelMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChannelMemberOut:
    member = await service.add_member(
        db, channel_id=channel_id, user_id=current_user.id, target_user_id=payload.user_id
    )
    return ChannelMemberOut.model_validate(member)


@router.delete(
    "/{channel_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member",
    description="Owner/admin can remove anyone; any member can remove themselves (leave).",
    responses={
        401: {"description": "Missing or invalid access token."},
        403: {"description": "Not an owner/admin of this channel."},
        404: {"description": "Channel not found, you're not a member, or the target isn't a member."},
    },
)
async def remove_member(
    channel_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.remove_member(
        db, channel_id=channel_id, user_id=current_user.id, target_user_id=user_id
    )
