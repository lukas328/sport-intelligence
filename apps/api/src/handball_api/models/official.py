"""Official league data (docs/plans/federation-onboarding.md): response cache, suggestions from
the official data, join requests of players and access requests to a claimed club."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from handball_api.core.db import Base, EntityMixin, TenantMixin


class OfficialCache(Base):
    """Raw answers of the official data provider (public data, not tenant data). Keyed by
    provider, operation and variables; the reader decides how old an answer may be."""

    __tablename__ = "official_cache"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    operation: Mapped[str] = mapped_column(String(40), nullable=False)
    variables: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OfficialSuggestion(Base, EntityMixin, TenantMixin):
    """A change the official data proposes for a team (schedule, roster, report, new season).

    Only the team's organisers see them (roster suggestions carry names from the official data).
    One row per team, kind and official key: a dismissed suggestion is not proposed again.
    """

    __tablename__ = "official_suggestions"
    __table_args__ = (
        Index("uq_official_suggestions_key", "team_id", "kind", "official_key", unique=True),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # roster_add | roster_number | roster_left | match_new | match_moved | report | season_new
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    official_key: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="open", server_default="open"
    )
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JoinRequest(Base, EntityMixin, TenantMixin):
    """A signed-in person asks to join a team (way B of the plan); the coach approves."""

    __tablename__ = "join_requests"
    __table_args__ = (
        Index(
            "uq_join_requests_pending",
            "team_id",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    jersey_number: Mapped[int | None] = mapped_column(SmallInteger)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="player")
    message: Mapped[str | None] = mapped_column(Text)
    # the roster entry (player) or open roster suggestion the app thinks this person is
    suggested_player_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL")
    )
    suggested_suggestion_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("official_suggestions.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="pending", server_default="pending"
    )
    player_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL")
    )
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrgAccessRequest(Base, EntityMixin, TenantMixin):
    """Someone found an already claimed club and asks its admins for access instead of creating a
    second organisation (organization_id is the club asked)."""

    __tablename__ = "org_access_requests"
    __table_args__ = (
        Index(
            "uq_org_access_requests_pending",
            "organization_id",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"))
    official_team_id: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="pending", server_default="pending"
    )
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
