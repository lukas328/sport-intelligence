"""progress heartbeat, matches that observe an opponent, files attached to a match

- processing_jobs.heartbeat_at: the last time the worker said it is still on the job (the
  progress view tells «läuft» from «hängt», the watchdog restarts a job that went silent)
- matches.kind 'scouting': a video of the opponent playing somebody else; scouting_other names
  that other team (the own team does not play, its season figures stay untouched)
- match_attachments: photos and PDFs (the paper match report, notes) kept with a match

Revision ID: 0046
Revises: 0045
Create Date: 2026-11-17 01:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0046"
down_revision: str | None = "0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "processing_jobs", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("matches", sa.Column("scouting_other", sa.String(length=120), nullable=True))
    op.drop_constraint(op.f("ck_matches_kind_values"), "matches", type_="check")
    op.create_check_constraint(
        op.f("ck_matches_kind_values"), "matches", "kind IN ('match', 'training', 'scouting')"
    )
    op.create_table(
        "match_attachments",
        sa.Column("match_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(length=400), nullable=False),
        sa.Column("upload_id", sa.String(length=400), nullable=True),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="uploading"),
        sa.Column("note", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('uploading', 'ready')", name=op.f("ck_match_attachments_status_values")
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_match_attachments_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["match_id"],
            ["matches.id"],
            name=op.f("fk_match_attachments_match_id_matches"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_match_attachments_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_match_attachments")),
    )
    op.create_index(
        op.f("ix_match_attachments_organization_id"), "match_attachments", ["organization_id"]
    )
    op.create_index(op.f("ix_match_attachments_match_id"), "match_attachments", ["match_id"])
    op.create_index(
        op.f("ix_match_attachments_created_by_id"), "match_attachments", ["created_by_id"]
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON match_attachments TO handball_app")
    op.execute("ALTER TABLE match_attachments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE match_attachments FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON match_attachments "
        "USING (app_bypass_rls() OR organization_id = app_current_org()) "
        "WITH CHECK (app_bypass_rls() OR organization_id = app_current_org())"
    )


def downgrade() -> None:
    op.drop_table("match_attachments")
    op.drop_constraint(op.f("ck_matches_kind_values"), "matches", type_="check")
    op.execute("DELETE FROM matches WHERE kind = 'scouting'")
    op.create_check_constraint(
        op.f("ck_matches_kind_values"), "matches", "kind IN ('match', 'training')"
    )
    op.drop_column("matches", "scouting_other")
    op.drop_column("processing_jobs", "heartbeat_at")
