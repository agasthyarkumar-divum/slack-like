from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.channels.schemas import ChannelOut
from app.modules.files.schemas import AttachmentOut
from app.modules.messages.schemas import MessageOut
from app.modules.search import service
from app.modules.search.schemas import SearchResponse, SearchType
from app.modules.users.schemas import UserOut

router = APIRouter(prefix="/search", tags=["search"])


@router.get(
    "",
    response_model=SearchResponse,
    summary="Full-text search",
    description="Postgres FTS over one of messages/users/channels/files at a "
    "time (architecture.md §6). Messages and channels are scoped to channels "
    "you're a member of; users are searchable company-wide; files are scoped "
    "to attachments in your channels, matched by filename.",
    responses={
        401: {"description": "Missing or invalid access token."},
        422: {"description": "Validation error."},
    },
)
async def search(
    q: str = Query(..., min_length=1, description="Search text.", examples=["standup"]),
    type: SearchType = Query(..., description="Which entity type to search."),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchResponse:
    if type == "messages":
        results = await service.search_messages(db, user_id=current_user.id, query=q, limit=limit)
        return SearchResponse(type=type, query=q, messages=[MessageOut.from_message(m) for m in results])
    if type == "users":
        results = await service.search_users(db, query=q, limit=limit)
        return SearchResponse(type=type, query=q, users=[UserOut.model_validate(u) for u in results])
    if type == "channels":
        results = await service.search_channels(db, user_id=current_user.id, query=q, limit=limit)
        return SearchResponse(type=type, query=q, channels=[ChannelOut.model_validate(c) for c in results])
    # type == "files"
    results = await service.search_files(db, user_id=current_user.id, query=q, limit=limit)
    return SearchResponse(type=type, query=q, files=[AttachmentOut.from_attachment(a) for a in results])
