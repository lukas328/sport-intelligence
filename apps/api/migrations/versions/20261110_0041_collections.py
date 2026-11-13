"""collections: one object of scenes, plays and notes (SPEC 7.7); the old playlists,
presentations and assignments stay and are read as collections

Revision ID: 0041
Revises: 0040
Create Date: 2026-11-10 17:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0041"
down_revision: str | None = "0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tenant(table: str) -> None:
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO handball_app")
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation ON {table} "
        "USING (app_bypass_rls() OR organization_id = app_current_org()) "
        "WITH CHECK (app_bypass_rls() OR organization_id = app_current_org())"
    )


def _base() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "collections",
        sa.Column("team_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("draft", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("match_id", sa.UUID(), nullable=True),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        *_base(),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_collections_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"], name=op.f("fk_collections_team_id_teams"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["match_id"],
            ["matches.id"],
            name=op.f("fk_collections_match_id_matches"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_collections_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_collections")),
    )
    for col in ("organization_id", "team_id", "match_id"):
        op.create_index(op.f(f"ix_collections_{col}"), "collections", [col])
    op.create_table(
        "collection_items",
        sa.Column("collection_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("clip_id", sa.UUID(), nullable=True),
        sa.Column("play_id", sa.UUID(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        *_base(),
        sa.CheckConstraint(
            "kind IN ('scene', 'play', 'note')", name=op.f("ck_collection_items_kind_values")
        ),
        sa.CheckConstraint(
            "(kind = 'scene' AND clip_id IS NOT NULL) OR (kind = 'play' AND play_id IS NOT NULL)"
            " OR (kind = 'note' AND text IS NOT NULL)",
            name=op.f("ck_collection_items_kind_target"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_collection_items_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collections.id"],
            name=op.f("fk_collection_items_collection_id_collections"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clip_id"],
            ["clips.id"],
            name=op.f("fk_collection_items_clip_id_clips"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["play_id"],
            ["plays.id"],
            name=op.f("fk_collection_items_play_id_plays"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_collection_items")),
    )
    for col in ("organization_id", "collection_id"):
        op.create_index(op.f(f"ix_collection_items_{col}"), "collection_items", [col])
    _tenant("collections")
    _tenant("collection_items")


def downgrade() -> None:
    op.drop_table("collection_items")
    op.drop_table("collections")
