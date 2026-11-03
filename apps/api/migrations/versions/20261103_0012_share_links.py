"""share links

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-03 04:00:00+00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "share_links",
        sa.Column("team_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_share_links_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_share_links_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"], name=op.f("fk_share_links_team_id_teams"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_share_links")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_share_links_token_hash")),
    )
    op.create_index(
        op.f("ix_share_links_organization_id"), "share_links", ["organization_id"], unique=False
    )
    op.create_index(op.f("ix_share_links_team_id"), "share_links", ["team_id"], unique=False)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON share_links TO handball_app")
    op.execute("ALTER TABLE share_links ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE share_links FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON share_links "
        "USING (app_bypass_rls() OR organization_id = app_current_org()) "
        "WITH CHECK (app_bypass_rls() OR organization_id = app_current_org())"
    )


def downgrade() -> None:
    op.drop_table("share_links")
