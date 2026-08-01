import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChannelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["general"])
    type: str = Field(
        ..., description="'public', 'private', 'dm', or 'group'.", examples=["public"]
    )
    topic: str | None = Field(None, examples=["Company-wide announcements"])
    member_ids: list[uuid.UUID] = Field(
        default_factory=list, description="Additional members to add besides the creator."
    )


class ChannelUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    topic: str | None = None


class ChannelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: str
    topic: str | None
    created_by: uuid.UUID | None
    created_at: datetime | None


class ChannelMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    role: str | None
    muted: bool | None
    joined_at: datetime | None


class ChannelMemberAdd(BaseModel):
    user_id: uuid.UUID = Field(..., description="User to add to the channel.")
