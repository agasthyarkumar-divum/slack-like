"""One module per aggregate (architecture.md §4, §5). Imported here so Alembic
autogenerate discovers every model via Base.metadata.
"""

from app.db.models.audit_log import AuditLog
from app.db.models.channel import Channel, ChannelMember
from app.db.models.department import Department
from app.db.models.message import Attachment, Message, MessageRead, Reaction
from app.db.models.notification import Notification
from app.db.models.role import Role
from app.db.models.session import Session
from app.db.models.team import Team
from app.db.models.user import User

__all__ = [
    "AuditLog",
    "Attachment",
    "Channel",
    "ChannelMember",
    "Department",
    "Message",
    "MessageRead",
    "Notification",
    "Reaction",
    "Role",
    "Session",
    "Team",
    "User",
]
