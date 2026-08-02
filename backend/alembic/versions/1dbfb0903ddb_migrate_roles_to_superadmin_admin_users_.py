"""migrate roles to superAdmin/admin/users scopes

Revision ID: 1dbfb0903ddb
Revises: e0550a0c156d
Create Date: 2026-08-02 00:51:54.125900

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1dbfb0903ddb'
down_revision: Union[str, None] = 'e0550a0c156d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename in place (not delete+recreate) so existing users.role_id FKs
    # keep pointing at a valid row instead of needing a backfill.
    op.execute("UPDATE roles SET name = 'users' WHERE name = 'member';")
    op.execute("INSERT INTO roles (name) VALUES ('superAdmin') ON CONFLICT (name) DO NOTHING;")
    # 'guest' was never actually assigned to anyone (Phase 3 only ever
    # defaulted new users to 'member'/'users') — safe to drop, but only if
    # that's still true, so this can't fail on a DB where it somehow was used.
    op.execute(
        """
        DELETE FROM roles
        WHERE name = 'guest'
        AND NOT EXISTS (SELECT 1 FROM users WHERE users.role_id = roles.id);
        """
    )

    # audit_logs (architecture.md §5, partitioned by month) only had a July
    # 2026 partition + a DEFAULT catch-all (Phase 7's migration) — inserts
    # still would've worked via DEFAULT, but the admin module is the first
    # real writer, so this is a natural point to add August's own partition.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs_2026_08 PARTITION OF audit_logs
            FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_logs_2026_08;")
    op.execute("UPDATE roles SET name = 'member' WHERE name = 'users';")
    op.execute("DELETE FROM roles WHERE name = 'superAdmin';")
    op.execute("INSERT INTO roles (name) VALUES ('guest') ON CONFLICT (name) DO NOTHING;")
