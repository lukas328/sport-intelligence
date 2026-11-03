"""addendum 01: new team roles, consent purposes, guardianships

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-03 09:00:00+00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_ROLES = ("coach", "analyst", "player", "goalkeeper", "guest")
NEW_ROLES = (*OLD_ROLES, "goalkeeper_coach", "athletic_coach", "team_manager", "parent")
OLD_CONSENTS = ("video_analysis", "identification")
NEW_CONSENTS = (
    "analysis",
    "highlights_internal",
    "highlights_public",
    "public_profile",
    "training_data",
)


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def _recheck(table: str, name: str, column: str, values: tuple[str, ...]) -> None:
    op.drop_constraint(op.f(name), table, type_="check")
    op.create_check_constraint(op.f(name), table, _in(column, values))


def upgrade() -> None:
    _recheck("memberships", "ck_memberships_teamrole", "role", NEW_ROLES)
    _recheck("invitations", "ck_invitations_teamrole", "team_role", NEW_ROLES)
    op.drop_constraint(op.f("ck_consents_consentkind"), "consents", type_="check")
    # analysis covers both former kinds (video analysis incl. identification of the player)
    op.execute(
        "UPDATE consents SET kind = 'analysis' WHERE kind IN ('video_analysis', 'identification')"
    )
    op.create_check_constraint(op.f("ck_consents_consentkind"), "consents", _in("kind", NEW_CONSENTS))

    op.create_table(
        "guardianships",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("player_id", sa.UUID(), nullable=False),
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
            name=op.f("fk_guardianships_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name=op.f("fk_guardianships_player_id_players"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_guardianships_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_guardianships")),
        sa.UniqueConstraint("user_id", "player_id", name=op.f("uq_guardianships_user_id")),
    )
    for col in ("organization_id", "user_id", "player_id"):
        op.create_index(op.f(f"ix_guardianships_{col}"), "guardianships", [col], unique=False)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON guardianships TO handball_app")
    op.execute("ALTER TABLE guardianships ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE guardianships FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON guardianships "
        "USING (app_bypass_rls() OR organization_id = app_current_org()) "
        "WITH CHECK (app_bypass_rls() OR organization_id = app_current_org())"
    )


def downgrade() -> None:
    op.drop_table("guardianships")
    op.drop_constraint(op.f("ck_consents_consentkind"), "consents", type_="check")
    op.execute("UPDATE consents SET kind = 'video_analysis' WHERE kind = 'analysis'")
    op.execute("DELETE FROM consents WHERE kind NOT IN ('video_analysis', 'identification')")
    op.create_check_constraint(op.f("ck_consents_consentkind"), "consents", _in("kind", OLD_CONSENTS))
    op.execute("DELETE FROM memberships WHERE " + _in("role", NEW_ROLES[5:]))
    op.execute("DELETE FROM invitations WHERE " + _in("team_role", NEW_ROLES[5:]))
    _recheck("memberships", "ck_memberships_teamrole", "role", OLD_ROLES)
    _recheck("invitations", "ck_invitations_teamrole", "team_role", OLD_ROLES)
