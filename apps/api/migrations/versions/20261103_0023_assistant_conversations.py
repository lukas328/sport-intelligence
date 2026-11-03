"""assistant conversations

Revision ID: 0023
Revises: 0022
Create Date: 2026-11-03 10:40:42.324532+00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0023'
down_revision: str | None = '0022'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # the A1 placeholders (conversation_threads, assistant_messages) were never used: replace them
    op.drop_table("assistant_messages")
    op.drop_table("conversation_threads")
    op.create_table('assistant_conversations',
    sa.Column('team_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_assistant_conversations_organization_id_organizations'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['team_id'], ['teams.id'], name=op.f('fk_assistant_conversations_team_id_teams'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_assistant_conversations_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_assistant_conversations'))
    )
    op.create_index(op.f('ix_assistant_conversations_organization_id'), 'assistant_conversations', ['organization_id'], unique=False)
    op.create_index(op.f('ix_assistant_conversations_team_id'), 'assistant_conversations', ['team_id'], unique=False)
    op.create_index(op.f('ix_assistant_conversations_user_id'), 'assistant_conversations', ['user_id'], unique=False)
    op.create_table(
        "assistant_messages",
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("transcript", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tool_calls", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model", sa.String(length=60), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("answerable", sa.Boolean(), nullable=False),
        sa.Column("validated", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["assistant_conversations.id"], name=op.f("fk_assistant_messages_conversation_id_assistant_conversations"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_assistant_messages_organization_id_organizations"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assistant_messages")),
    )
    op.create_index(op.f("ix_assistant_messages_conversation_id"), "assistant_messages", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_assistant_messages_organization_id"), "assistant_messages", ["organization_id"], unique=False)
    for table in ("assistant_conversations", "assistant_messages"):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO handball_app")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            "USING (app_bypass_rls() OR organization_id = app_current_org()) "
            "WITH CHECK (app_bypass_rls() OR organization_id = app_current_org())"
        )


def downgrade() -> None:
    op.drop_table("assistant_messages")
    op.drop_table("assistant_conversations")
    op.create_table('conversation_threads',
    sa.Column('team_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.UUID(), autoincrement=False, nullable=True),
    sa.Column('title', sa.VARCHAR(length=160), autoincrement=False, nullable=True),
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('organization_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_conversation_threads_organization_id_organizations'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['team_id'], ['teams.id'], name=op.f('fk_conversation_threads_team_id_teams'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_conversation_threads_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_conversation_threads'))
    )
    op.create_index(op.f('ix_conversation_threads_user_id'), 'conversation_threads', ['user_id'], unique=False)
    op.create_index(op.f('ix_conversation_threads_team_id'), 'conversation_threads', ['team_id'], unique=False)
    op.create_index(op.f('ix_conversation_threads_organization_id'), 'conversation_threads', ['organization_id'], unique=False)
    op.create_table(
        "assistant_messages",
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("tools", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("facts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("clip_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cost_microchf", sa.Integer(), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_assistant_messages_organization_id_organizations"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thread_id"], ["conversation_threads.id"], name=op.f("fk_assistant_messages_thread_id_conversation_threads"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assistant_messages")),
    )
    op.create_index(op.f("ix_assistant_messages_organization_id"), "assistant_messages", ["organization_id"], unique=False)
    op.create_index(op.f("ix_assistant_messages_thread_id"), "assistant_messages", ["thread_id"], unique=False)
    for table in ("conversation_threads", "assistant_messages"):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO handball_app")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            "USING (app_bypass_rls() OR organization_id = app_current_org()) "
            "WITH CHECK (app_bypass_rls() OR organization_id = app_current_org())"
        )
