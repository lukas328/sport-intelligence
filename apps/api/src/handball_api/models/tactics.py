from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from handball_api.core.db import Base, EntityMixin, TenantMixin


class Play(Base, EntityMixin, TenantMixin):
    """A play in the team's library: tactics board frames (format in @handball/tactics) plus an
    optional reference to the video moment it was drawn from."""

    __tablename__ = "plays"

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    formation: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    doc: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # P2 preparation: club playbook; True = visible to all teams of the club
    club_playbook: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # {match_id, t_ms}
    shared_with_players: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
