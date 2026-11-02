"""baseline: extensions and app role for row level security

Revision ID: 0001
Revises:
Create Date: 2026-11-02
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "citext"')
    # Helper used by RLS policies from M1 on: current tenant set per transaction via
    # SET LOCAL app.current_org = '<uuid>' (see docs/adr/005-tenant-isolation.md).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_current_org() RETURNS uuid
        LANGUAGE sql STABLE AS $$
          SELECT NULLIF(current_setting('app.current_org', true), '')::uuid
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS app_current_org()")
