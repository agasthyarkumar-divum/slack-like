"""Column patterns shared by every model in architecture.md §5 (except audit_logs,
whose partitioned primary key must also include the partition column — see
db/models/audit_log.py for why it can't use this mixin).
"""

import uuid

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
