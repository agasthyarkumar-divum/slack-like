import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Channel, ChannelMember
from app.modules.channels import repository

_MANAGE_ROLES = {"owner", "admin"}


async def require_membership(
    db: AsyncSession, *, channel_id: uuid.UUID, user_id: uuid.UUID
) -> ChannelMember:
    """404s for both "channel doesn't exist" and "not a member" — deliberately
    not distinguishing the two so a private channel's existence isn't leaked
    to non-members.
    """
    member = await repository.get_membership(db, channel_id=channel_id, user_id=user_id)
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found.")
    return member


def _require_manage_role(member: ChannelMember) -> None:
    if member.role not in _MANAGE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only channel owners/admins can do this.")


async def create_channel(
    db: AsyncSession,
    *,
    creator_id: uuid.UUID,
    name: str,
    type: str,
    topic: str | None,
    member_ids: list[uuid.UUID],
) -> Channel:
    channel = await repository.create_channel(
        db, name=name, type=type, topic=topic, created_by=creator_id
    )
    await repository.add_member(db, channel_id=channel.id, user_id=creator_id, role="owner")
    for user_id in {mid for mid in member_ids if mid != creator_id}:
        await repository.add_member(db, channel_id=channel.id, user_id=user_id, role="member")
    await db.commit()
    await db.refresh(channel)
    return channel


async def list_my_channels(db: AsyncSession, user_id: uuid.UUID) -> list[Channel]:
    return await repository.list_channels_for_user(db, user_id)


async def get_channel(db: AsyncSession, *, channel_id: uuid.UUID, user_id: uuid.UUID) -> Channel:
    await require_membership(db, channel_id=channel_id, user_id=user_id)
    channel = await repository.get_channel_by_id(db, channel_id)
    if channel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found.")
    return channel


async def update_channel(
    db: AsyncSession,
    *,
    channel_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str | None,
    topic: str | None,
) -> Channel:
    member = await require_membership(db, channel_id=channel_id, user_id=user_id)
    _require_manage_role(member)
    channel = await repository.get_channel_by_id(db, channel_id)
    if channel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found.")
    if name is not None:
        channel.name = name
    if topic is not None:
        channel.topic = topic
    await db.commit()
    await db.refresh(channel)
    return channel


async def add_member(
    db: AsyncSession, *, channel_id: uuid.UUID, user_id: uuid.UUID, target_user_id: uuid.UUID
) -> ChannelMember:
    member = await require_membership(db, channel_id=channel_id, user_id=user_id)
    _require_manage_role(member)
    existing = await repository.get_membership(db, channel_id=channel_id, user_id=target_user_id)
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a member.")
    new_member = await repository.add_member(db, channel_id=channel_id, user_id=target_user_id)
    await db.commit()
    await db.refresh(new_member)
    return new_member


async def remove_member(
    db: AsyncSession, *, channel_id: uuid.UUID, user_id: uuid.UUID, target_user_id: uuid.UUID
) -> None:
    member = await require_membership(db, channel_id=channel_id, user_id=user_id)
    if user_id != target_user_id:
        _require_manage_role(member)
    target = await repository.get_membership(db, channel_id=channel_id, user_id=target_user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That user isn't a member.")
    await repository.remove_member(db, target)
    await db.commit()


async def list_members(db: AsyncSession, *, channel_id: uuid.UUID, user_id: uuid.UUID):
    await require_membership(db, channel_id=channel_id, user_id=user_id)
    return await repository.list_members(db, channel_id)
