"""consent links: consent without an account, one link per team for the team chat

Revision ID: 0042
Revises: 0041
Create Date: 2026-11-10 18:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0042"
down_revision: str | None = "0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consent_links",
        sa.Column("team_id", sa.UUID(), nullable=False),
        sa.Column("season_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answers", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_consent_links_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name=op.f("fk_consent_links_team_id_teams"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["season_id"],
            ["seasons.id"],
            name=op.f("fk_consent_links_season_id_seasons"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_consent_links_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consent_links")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_consent_links_token_hash")),
    )
    op.create_index(op.f("ix_consent_links_organization_id"), "consent_links", ["organization_id"])
    op.create_index(op.f("ix_consent_links_team_id"), "consent_links", ["team_id"])
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON consent_links TO handball_app")
    op.execute("ALTER TABLE consent_links ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE consent_links FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON consent_links "
        "USING (app_bypass_rls() OR organization_id = app_current_org()) "
        "WITH CHECK (app_bypass_rls() OR organization_id = app_current_org())"
    )


def downgrade() -> None:
    op.drop_table("consent_links")
