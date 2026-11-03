"""Match formats, segments, live tags, training sessions, paper report uploads (addendum 01)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from handball_api.core.db import Base, EntityMixin, TenantMixin
from handball_api.models._types import str_enum
from handball_api.models.enums import AttendanceStatus, UploadStatus


class MatchFormat(Base, EntityMixin, TenantMixin):
    """A club's own format (the built-in templates live in code: services/match_formats.py)."""

    __tablename__ = "match_formats"
    __table_args__ = (
        UniqueConstraint("organization_id", "name"),
        CheckConstraint("period_s BETWEEN 60 AND 3600", name="period_range"),
        CheckConstraint("periods BETWEEN 1 AND 4", name="periods_range"),
    )

    name: Mapped[str] = mapped_column(String(60), nullable=False)
    period_s: Mapped[int] = mapped_column(Integer, nullable=False)
    periods: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)
    court: Mapped[str] = mapped_column(String(20), nullable=False, default="40x20")
    rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class OpponentPlayer(Base, EntityMixin, TenantMixin):
    """Opponent players: number only by default; a name only from a public source (4.9).

    Never public, never named in highlights or share links.
    """

    __tablename__ = "opponent_players"
    __table_args__ = (
        UniqueConstraint("opponent_id", "number"),
        CheckConstraint("number BETWEEN 1 AND 99", name="number_range"),
        CheckConstraint("name IS NULL OR source IS NOT NULL", name="name_needs_source"),
    )

    opponent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opponents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    name: Mapped[str | None] = mapped_column(String(120))
    source: Mapped[str | None] = mapped_column(String(300))  # public source, e.g. league site URL
    position: Mapped[str | None] = mapped_column(String(2))
    entered_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class MatchSegment(Base, EntityMixin, TenantMixin):
    """Several files per match, several matches per video (4.8): where a match lives in a file."""

    __tablename__ = "match_segments"

    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("video_assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_ms: Mapped[int | None] = mapped_column(Integer)
    gap_before_ms: Mapped[int | None] = mapped_column(Integer)  # detected gap to previous segment
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class LiveTagSession(Base, EntityMixin, TenantMixin):
    """Courtside tagging on a phone (5.3), synced to the video later."""

    __tablename__ = "live_tag_sessions"

    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    device: Mapped[str | None] = mapped_column(String(120))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    offset_ms: Mapped[int | None] = mapped_column(Integer)  # device clock -> video time
    sync_confidence: Mapped[float | None] = mapped_column(Float)


class LiveTag(Base, EntityMixin, TenantMixin):
    __tablename__ = "live_tags"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("live_tag_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    device_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    key: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str | None] = mapped_column(String(300))
    event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("events.id", ondelete="SET NULL"))


class TrainingSession(Base, EntityMixin, TenantMixin):
    """Lean training plan (5.7): date, drills with duration, notes."""

    __tablename__ = "training_sessions"

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    on_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    title: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[str | None] = mapped_column(String(160))
    # snapshot of the drills at planning time (5.7), so a later library change keeps the plan:
    # [{"drill_id", "name", "minutes", "focus": [...], "setup", "coaching", "note"}]
    drills: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    external_ref: Mapped[str | None] = mapped_column(String(200))  # ICS UID, Spond id


class Attendance(Base, EntityMixin, TenantMixin):
    """Attendance for a training session or a match (5.7): the player's (or a parent's) reply and
    what the staff recorded afterwards. Absence reasons are free text; no diagnoses."""

    __tablename__ = "attendances"
    __table_args__ = (
        UniqueConstraint("session_id", "player_id"),
        UniqueConstraint("match_id", "player_id"),
        CheckConstraint("num_nonnulls(session_id, match_id) = 1", name="one_target"),
    )

    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("training_sessions.id", ondelete="CASCADE"), index=True
    )
    match_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True, nullable=False
    )
    response: Mapped[str | None] = mapped_column(String(10))  # yes / no, from the player
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[AttendanceStatus | None] = mapped_column(str_enum(AttendanceStatus))
    reason: Mapped[str | None] = mapped_column(String(200))


class PaperReportUpload(Base, EntityMixin, TenantMixin):
    """Photo of a paper match report (5.9): extraction, validation errors, confirmation."""

    __tablename__ = "paper_report_uploads"

    match_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("matches.id", ondelete="SET NULL"), index=True
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    photo_key: Mapped[str] = mapped_column(String(300), nullable=False)
    extraction: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[UploadStatus] = mapped_column(
        str_enum(UploadStatus), nullable=False, default=UploadStatus.PENDING
    )
    confirmed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
