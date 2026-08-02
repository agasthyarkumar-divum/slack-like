import uuid
from collections import Counter
from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models import Message


class MessageCreate(BaseModel):
    content: str | None = Field(None, examples=["hey, standup moved to 10am"])
    reply_to_id: uuid.UUID | None = Field(None, description="Message this is replying to.")
    attachment_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="Already-uploaded (status='ready') attachments to attach to this message. "
        "At least one of content or attachment_ids is required.",
    )


class MessageUpdate(BaseModel):
    content: str = Field(..., min_length=1)


class ReactionSummary(BaseModel):
    emoji: str
    count: int
    me: bool = Field(..., description="Whether the requesting user is one of the reactors.")


class MessageOut(BaseModel):
    id: uuid.UUID
    channel_id: uuid.UUID | None
    sender_id: uuid.UUID | None
    content: str | None
    reply_to_id: uuid.UUID | None
    forwarded_from_id: uuid.UUID | None
    is_pinned: bool | None
    is_edited: bool | None
    is_deleted: bool | None
    created_at: datetime | None
    edited_at: datetime | None
    attachment_ids: list[uuid.UUID] = Field(default_factory=list)
    reactions: list[ReactionSummary] = Field(default_factory=list)
    reply_count: int = Field(0, description="Number of thread replies to this message.")
    last_reply_at: datetime | None = Field(None, description="Newest reply's created_at, if any.")

    @classmethod
    def from_message(
        cls,
        message: Message,
        *,
        current_user_id: uuid.UUID | None = None,
        reply_count: int = 0,
        last_reply_at: datetime | None = None,
    ) -> "MessageOut":
        emoji_counts = Counter(r.emoji for r in message.reactions)
        mine = {r.emoji for r in message.reactions if r.user_id == current_user_id}
        reactions = [
            ReactionSummary(emoji=emoji, count=count, me=emoji in mine)
            for emoji, count in emoji_counts.items()
        ]
        return cls(
            id=message.id,
            channel_id=message.channel_id,
            sender_id=message.sender_id,
            content=message.content,
            reply_to_id=message.reply_to_id,
            forwarded_from_id=message.forwarded_from_id,
            is_pinned=message.is_pinned,
            is_edited=message.is_edited,
            is_deleted=message.is_deleted,
            created_at=message.created_at,
            edited_at=message.edited_at,
            attachment_ids=[a.id for a in message.attachments],
            reactions=reactions,
            reply_count=reply_count,
            last_reply_at=last_reply_at,
        )


class MessageListResponse(BaseModel):
    items: list[MessageOut]
    next_cursor: str | None = Field(
        None, description="Pass as ?cursor= to fetch the next (older) page; null if no more."
    )


class ThreadRepliesResponse(BaseModel):
    parent: MessageOut
    items: list[MessageOut] = Field(..., description="Replies, oldest first.")
    next_cursor: str | None = Field(
        None, description="Pass as ?cursor= to fetch the next (newer) page; null if no more."
    )


class ReactionCreate(BaseModel):
    emoji: str = Field(..., min_length=1, max_length=20, examples=["👍"])


class ForwardRequest(BaseModel):
    target_channel_id: uuid.UUID = Field(..., description="Channel to forward this message into.")
