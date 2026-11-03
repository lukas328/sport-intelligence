from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from handball_api.core.db import Base, EntityMixin, TenantMixin
from handball_api.models._types import str_enum
from handball_api.models.enums import DataRegion, OrgRole, Plan, TeamGender, TeamRole


class Organization(Base, EntityMixin):
    """The tenant (club). RLS: visible when it is the current org or the user is a member."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="CH")
    logo_key: Mapped[str | None] = mapped_column(String(300))
    primary_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#0b6bcb")
    secondary_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#ffffff")
    plan: Mapped[Plan] = mapped_column(str_enum(Plan), nullable=False, default=Plan.FREE)
    data_region: Mapped[DataRegion] = mapped_column(
        str_enum(DataRegion), nullable=False, default=DataRegion.CH
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(100))
    # Stripe subscription state (BRIEF 13): trialing, active, past_due, canceled, ...
    subscription_status: Mapped[str | None] = mapped_column(String(30))
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    goalkeeper_seats: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trial_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class StripeEvent(Base):
    """Processed webhook events (idempotency). Global, not tenant data."""

    __tablename__ = "stripe_events"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OrgMembership(Base, EntityMixin, TenantMixin):
    """Everyone in an organisation has one row; org admins have role org_admin."""

    __tablename__ = "org_memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[OrgRole] = mapped_column(str_enum(OrgRole), nullable=False)


class Team(Base, EntityMixin, TenantMixin):
    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    league: Mapped[str | None] = mapped_column(String(120))
    is_youth: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gender: Mapped[TeamGender] = mapped_column(str_enum(TeamGender), nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    @property
    def players_see_team_stats(self) -> bool:
        return bool(self.settings.get("players_see_team_stats", not self.is_youth))


class Season(Base, EntityMixin, TenantMixin):
    __tablename__ = "seasons"
    __table_args__ = (UniqueConstraint("team_id", "label"),)

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    label: Mapped[str] = mapped_column(String(40), nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)


class Membership(Base, EntityMixin, TenantMixin):
    """User x Team with a role (BRIEF 3)."""

    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("team_id", "user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[TeamRole] = mapped_column(str_enum(TeamRole), nullable=False)


class Invitation(Base, EntityMixin, TenantMixin):
    __tablename__ = "invitations"

    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    org_role: Mapped[OrgRole] = mapped_column(str_enum(OrgRole), nullable=False)
    team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    team_role: Mapped[TeamRole | None] = mapped_column(str_enum(TeamRole))
    player_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL")
    )
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
