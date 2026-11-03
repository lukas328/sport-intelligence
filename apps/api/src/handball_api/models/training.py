from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from handball_api.core.db import Base, EntityMixin, TenantMixin


class Assignment(Base, EntityMixin, TenantMixin):
    """Homework for players: watch a playlist, study a play, read a drill (M7)."""

    __tablename__ = "assignments"

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # playlist, play, match, drill
    target_id: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class AssignmentStatus(Base, EntityMixin, TenantMixin):
    __tablename__ = "assignment_statuses"
    __table_args__ = (UniqueConstraint("assignment_id", "user_id"),)

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Notification(Base, EntityMixin, TenantMixin):
    """In-app notification; the text is rendered in the client from `kind` and `params`."""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    link: Mapped[str | None] = mapped_column(String(400))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FocusPlan(Base, EntityMixin, TenantMixin):
    """From a problem to training (5.6): an insight of a match turned into a training focus, with
    the session, evidence playlist and assignment it created and the metric that is followed over
    the next matches (shown as an observation, not as proof)."""

    __tablename__ = "focus_plans"

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    match_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("matches.id", ondelete="SET NULL")
    )
    insight_key: Mapped[str] = mapped_column(String(60), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    focus: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    metric: Mapped[str | None] = mapped_column(String(30))
    filter: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    higher_is_better: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("training_sessions.id", ondelete="SET NULL")
    )
    playlist_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("playlists.id", ondelete="SET NULL")
    )
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assignments.id", ondelete="SET NULL")
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
