"""add notification_preference to users

Revision ID: be76a9920c19
Revises: 1dbfb0903ddb
Create Date: 2026-08-02 01:48:43.041782

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'be76a9920c19'
down_revision: Union[str, None] = '1dbfb0903ddb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Autogenerate also flagged a pile of indexes/partitions (idx_*, the
    # audit_logs_* partitions) as "removed" — those are created by raw SQL in
    # earlier migrations, not declared as SQLAlchemy Table/Index objects, so
    # they're invisible to metadata diffing and were never actually dropped.
    # Only this column is a real change.
    op.add_column(
        'users',
        sa.Column('notification_preference', sa.String(length=20), server_default='all', nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'notification_preference')
