import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., examples=["9c2d4b1a-6e2a-4b7b-9b3a-9d6f7a2e5c11"])
    email: str = Field(..., examples=["alice@example.com"])
    display_name: str = Field(..., examples=["Alice Example"])
    avatar_uri: str | None = Field(
        None, description="Storage URI (backend-agnostic), e.g. 'local://avatars/...'."
    )
    status: str | None = Field(None, examples=["offline"])
    department_id: uuid.UUID | None = None
    team_id: uuid.UUID | None = None
    role_id: uuid.UUID | None = None
    created_at: datetime | None = None
