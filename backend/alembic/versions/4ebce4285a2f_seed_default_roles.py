"""seed default roles

Revision ID: 4ebce4285a2f
Revises: b162a8b750e5
Create Date: 2026-07-31 05:22:05.657259

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ebce4285a2f'
down_revision: Union[str, None] = 'b162a8b750e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # RBAC enforcement itself is Phase 4 — this just seeds the three role names
    # the schema's own comments call out (architecture.md §5) so /auth/register
    # has a 'member' role to default new users into. permissions stays the
    # column default ('{}') until Phase 4 defines real permission sets.
    op.execute("""
        INSERT INTO roles (name) VALUES ('admin'), ('member'), ('guest')
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DELETE FROM roles WHERE name IN ('admin', 'member', 'guest');")
