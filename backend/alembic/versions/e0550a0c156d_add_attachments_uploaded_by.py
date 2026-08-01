"""add attachments.uploaded_by

Revision ID: e0550a0c156d
Revises: 4ebce4285a2f
Create Date: 2026-08-01 13:46:33.194578

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e0550a0c156d'
down_revision: Union[str, None] = '4ebce4285a2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# NOTE: autogenerate also proposed dropping every hand-written index, trigger,
# and the audit_logs partitions from the initial migration — those aren't
# represented in Base.metadata (see that migration's comments), so autogenerate
# always sees them as drift. Stripped back down to just the real change.


def upgrade() -> None:
    op.add_column('attachments', sa.Column('uploaded_by', sa.UUID(), nullable=True))
    op.create_foreign_key(None, 'attachments', 'users', ['uploaded_by'], ['id'])


def downgrade() -> None:
    op.drop_constraint(None, 'attachments', type_='foreignkey')
    op.drop_column('attachments', 'uploaded_by')
