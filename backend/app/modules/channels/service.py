import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Channel, ChannelMember
from app.modules.auth import repository as auth_repository
from app.modules.channels import repository
from app.modules.messages import repository as messages_repository

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


async def list_my_channels(db: AsyncSession, user_id: uuid.UUID) -> list[tuple[Channel, int]]:
    channels = await repository.list_channels_for_user(db, user_id)
    unread_counts = await messages_repository.count_unread_by_channel(db, user_id)
    return [(channel, unread_counts.get(channel.id, 0)) for channel in channels]


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


async def get_or_create_dm(
    db: AsyncSession, *, user_id: uuid.UUID, other_user_id: uuid.UUID
) -> Channel:
    if user_id == other_user_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Can't start a DM with yourself.")
    other_user = await auth_repository.get_user_by_id(db, other_user_id)
    if other_user is None or not other_user.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")

    existing = await repository.find_dm_channel(db, user_id=user_id, other_user_id=other_user_id)
    if existing is not None:
        return existing

    # `name` is never shown as-is for a DM — the client resolves the other
    # member's display name from membership instead (there's no single "DM
    # name" that makes sense from both participants' points of view).
    channel = await repository.create_channel(
        db, name="Direct Message", type="dm", topic=None, created_by=user_id
    )
    await repository.add_member(db, channel_id=channel.id, user_id=user_id, role="member")
    await repository.add_member(db, channel_id=channel.id, user_id=other_user_id, role="member")
    await db.commit()
    await db.refresh(channel)
    return channel
