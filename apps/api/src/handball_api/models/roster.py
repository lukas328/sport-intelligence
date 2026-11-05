from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from handball_api.core.db import Base, EntityMixin, TenantMixin
from handball_api.models._types import str_enum
from handball_api.models.enums import ConsentGivenBy, ConsentKind, Hand, Position


class Player(Base, EntityMixin, TenantMixin):
    __tablename__ = "players"

    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    birth_year: Mapped[int | None] = mapped_column(SmallInteger)
    shooting_hand: Mapped[Hand | None] = mapped_column(str_enum(Hand))
    main_position: Mapped[Position | None] = mapped_column(str_enum(Position))
    secondary_positions: Mapped[list[str]] = mapped_column(
        ARRAY(String(2)), nullable=False, default=list
    )
    photo_key: Mapped[str | None] = mapped_column(String(300))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class RosterEntry(Base, EntityMixin, TenantMixin):
    """Player x Team x Season with jersey number."""

    __tablename__ = "roster_entries"
    __table_args__ = (
        UniqueConstraint("season_id", "player_id"),
        CheckConstraint("jersey_number BETWEEN 1 AND 99", name="jersey_range"),
        Index(
            "uq_roster_entries_season_jersey_active",
            "season_id",
            "jersey_number",
            unique=True,
            postgresql_where=text("active"),
        ),
        UniqueConstraint(
            "season_id",
            "official_provider",
            "official_player_id",
            name="uq_roster_entries_official",
        ),
    )

    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True, nullable=False
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    season_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"), index=True, nullable=False
    )
    jersey_number: Mapped[int | None] = mapped_column(SmallInteger)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # from the official player list (federation onboarding): visible to the coach only until
    # the person joins or a consent is recorded
    official_provider: Mapped[str | None] = mapped_column(String(20))
    official_player_id: Mapped[int | None] = mapped_column(Integer)


class Consent(Base, EntityMixin, TenantMixin):
    """Consent per player (BRIEF 12). For youth teams given by a parent or guardian."""

    __tablename__ = "consents"

    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[ConsentKind] = mapped_column(str_enum(ConsentKind, 30), nullable=False)
    given_by: Mapped[ConsentGivenBy] = mapped_column(str_enum(ConsentGivenBy), nullable=False)
    given_by_name: Mapped[str] = mapped_column(String(160), nullable=False)
    given_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    document_ref: Mapped[str | None] = mapped_column(String(300))
    recorded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Guardianship(Base, EntityMixin, TenantMixin):
    """Parent or guardian account of a (usually minor) player (addendum 01, role `parent`)."""

    __tablename__ = "guardianships"
    __table_args__ = (UniqueConstraint("user_id", "player_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True, nullable=False
    )
