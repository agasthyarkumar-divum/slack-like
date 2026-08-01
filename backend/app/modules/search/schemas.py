from typing import Literal

from pydantic import BaseModel, Field

from app.modules.channels.schemas import ChannelOut
from app.modules.files.schemas import AttachmentOut
from app.modules.messages.schemas import MessageOut
from app.modules.users.schemas import UserOut

SearchType = Literal["messages", "users", "channels", "files"]


class SearchResponse(BaseModel):
    type: SearchType
    query: str = Field(..., examples=["standup"])
    # Only the field matching `type` is populated; the rest stay null. Split
    # this way (rather than a single untyped `items` list) so Swagger/ReDoc
    # can show the real shape for each search type.
    messages: list[MessageOut] | None = None
    users: list[UserOut] | None = None
    channels: list[ChannelOut] | None = None
    files: list[AttachmentOut] | None = None
