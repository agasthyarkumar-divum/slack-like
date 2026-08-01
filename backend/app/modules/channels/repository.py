import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Channel, ChannelMember, User


async def create_channel(
    db: AsyncSession, *, name: str, type: str, topic: str | None, created_by: uuid.UUID
) -> Channel:
    channel = Channel(name=name, type=type, topic=topic, created_by=created_by)
    db.add(channel)
    await db.flush()
    await db.refresh(channel)
    return channel


async def get_channel_by_id(db: AsyncSession, channel_id: uuid.UUID) -> Channel | None:
    return await db.get(Channel, channel_id)


async def add_member(
    db: AsyncSession, *, channel_id: uuid.UUID, user_id: uuid.UUID, role: str = "member"
) -> ChannelMember:
    member = ChannelMember(channel_id=channel_id, user_id=user_id, role=role)
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


async def get_membership(
    db: AsyncSession, *, channel_id: uuid.UUID, user_id: uuid.UUID
) -> ChannelMember | None:
    return await db.get(ChannelMember, {"channel_id": channel_id, "user_id": user_id})


async def remove_member(db: AsyncSession, member: ChannelMember) -> None:
    await db.delete(member)
    await db.flush()


async def list_members(db: AsyncSession, channel_id: uuid.UUID) -> list[ChannelMember]:
    result = await db.execute(
        select(ChannelMember).where(ChannelMember.channel_id == channel_id)
    )
    return list(result.scalars().all())


async def list_member_users(db: AsyncSession, channel_id: uuid.UUID) -> list[User]:
    """Full User rows for a channel's members — needed for @mention matching
    against email local-parts (ChannelMember alone only has user_id)."""
    result = await db.execute(
        select(User).join(ChannelMember, ChannelMember.user_id == User.id).where(
            ChannelMember.channel_id == channel_id
        )
    )
    return list(result.scalars().all())


async def find_dm_channel(
    db: AsyncSession, *, user_id: uuid.UUID, other_user_id: uuid.UUID
) -> Channel | None:
    """A 'dm' channel with *exactly* these two members, or None. Used to avoid
    creating a fresh DM channel every time two people message each other.
    """
    result = await db.execute(
        select(Channel)
        .join(ChannelMember, ChannelMember.channel_id == Channel.id)
        .where(Channel.type == "dm")
        .group_by(Channel.id)
        .having(
            func.count(ChannelMember.user_id) == 2,
            func.bool_or(ChannelMember.user_id == user_id),
            func.bool_or(ChannelMember.user_id == other_user_id),
        )
    )
    return result.scalars().first()


async def list_channels_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[Channel]:
    result = await db.execute(
        select(Channel)
        .join(ChannelMember, ChannelMember.channel_id == Channel.id)
        .where(ChannelMember.user_id == user_id)
        .order_by(Channel.created_at.desc())
    )
    return list(result.scalars().all())
