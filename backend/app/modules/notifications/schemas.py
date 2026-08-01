import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str = Field(..., examples=["mention"], description="'mention', 'dm', or 'reaction'.")
    payload: dict
    is_read: bool | None
    created_at: datetime | None


class NotificationListResponse(BaseModel):
    items: list[NotificationOut]
    unread_count: int = Field(..., description="COUNT(*) WHERE is_read=false — for the in-app badge.")
