"""assignments, assignment statuses, notifications

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-03 02:00:00+00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _base(table: str) -> list[sa.Column]:
    return [
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f(f"fk_{table}_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
    ]


def _rls(table: str) -> None:
    op.create_index(op.f(f"ix_{table}_organization_id"), table, ["organization_id"], unique=False)
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO handball_app")
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation ON {table} "
        "USING (app_bypass_rls() OR organization_id = app_current_org()) "
        "WITH CHECK (app_bypass_rls() OR organization_id = app_current_org())"
    )


def upgrade() -> None:
    op.create_table(
        "assignments",
        sa.Column("team_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("target_id", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        *_base("assignments"),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"], name=op.f("fk_assignments_team_id_teams"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_assignments_created_by_id_users"),
            ondelete="SET NULL",
        ),
    )
    op.create_index(op.f("ix_assignments_team_id"), "assignments", ["team_id"], unique=False)
    _rls("assignments")

    op.create_table(
        "assignment_statuses",
        sa.Column("assignment_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        *_base("assignment_statuses"),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["assignments.id"],
            name=op.f("fk_assignment_statuses_assignment_id_assignments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_assignment_statuses_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "assignment_id", "user_id", name=op.f("uq_assignment_statuses_assignment_id")
        ),
    )
    op.create_index(
        op.f("ix_assignment_statuses_assignment_id"),
        "assignment_statuses",
        ["assignment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignment_statuses_user_id"), "assignment_statuses", ["user_id"], unique=False
    )
    _rls("assignment_statuses")

    op.create_table(
        "notifications",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("link", sa.String(length=400), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        *_base("notifications"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_notifications_user_id_users"), ondelete="CASCADE"
        ),
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)
    _rls("notifications")


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("assignment_statuses")
    op.drop_table("assignments")
