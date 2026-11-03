"""Video session content (addendum 01 section 3): presentations, tags, highlight reels, scouting
reports, player feed, self assessments, assistant conversations and public profiles."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
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
from handball_api.models.enums import ReelFormat, ReelStatus, SlideType


class Presentation(Base, EntityMixin, TenantMixin):
    """Video session for the team (4.1)."""

    __tablename__ = "presentations"

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    match_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("matches.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    shared_with_players: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # MP4 export with burned-in drawings (worker): status queued | running | ready | failed
    export_status: Mapped[str | None] = mapped_column(String(20))
    export_key: Mapped[str | None] = mapped_column(String(300))
    export_error: Mapped[str | None] = mapped_column(Text)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PresentationSlide(Base, EntityMixin, TenantMixin):
    """Slide; for `clip`: in/out point, hold points, slow-motion ranges, drawings, spotlight."""

    __tablename__ = "presentation_slides"

    presentation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("presentations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    type: Mapped[SlideType] = mapped_column(str_enum(SlideType), nullable=False)
    clip_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clips.id", ondelete="SET NULL"))
    play_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plays.id", ondelete="SET NULL"))
    # {"in_ms", "out_ms", "holds": [ms], "slow": [[a, b]], "drawings": [...], "spotlight": [ids]}
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class TagSet(Base, EntityMixin, TenantMixin):
    __tablename__ = "tag_sets"
    __table_args__ = (UniqueConstraint("team_id", "name"),)

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)


class Tag(Base, EntityMixin, TenantMixin):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("tag_set_id", "name"),)

    tag_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tag_sets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    color: Mapped[str | None] = mapped_column(String(7))
    hotkey: Mapped[str | None] = mapped_column(String(1))


class ClipTag(Base, EntityMixin, TenantMixin):
    """A team tag on exactly one target: clip, event or play (4.4). Own tags never change automatic
    metrics; they only add a dimension for search, stats and presentations."""

    __tablename__ = "clip_tags"
    __table_args__ = (
        CheckConstraint("num_nonnulls(clip_id, event_id, play_id) = 1", name="one_target"),
        Index("uq_clip_tags_clip", "clip_id", "tag_id", unique=True),
        Index("uq_clip_tags_event", "event_id", "tag_id", unique=True),
        Index("uq_clip_tags_play", "play_id", "tag_id", unique=True),
    )

    clip_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clips.id", ondelete="CASCADE"), index=True
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    play_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("plays.id", ondelete="CASCADE"), index=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), index=True, nullable=False
    )


class SavedFilter(Base, EntityMixin, TenantMixin):
    """Smart playlist: a stored filter over events and tags that updates itself."""

    __tablename__ = "saved_filters"

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    query: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class HighlightReel(Base, EntityMixin, TenantMixin):
    """Match or player highlights (4.3); consent status is checked before rendering."""

    __tablename__ = "highlight_reels"

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    match_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True
    )
    player_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True
    )
    format: Mapped[ReelFormat] = mapped_column(str_enum(ReelFormat, 5), nullable=False)
    status: Mapped[ReelStatus] = mapped_column(
        str_enum(ReelStatus), nullable=False, default=ReelStatus.QUEUED
    )
    output_key: Mapped[str | None] = mapped_column(String(300))
    # {"checked_at": iso, "purpose": "highlights_internal", "missing": [player ids]}
    consent: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    clip_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)


class ScoutingReport(Base, EntityMixin, TenantMixin):
    """Automatic preparation report (4.6): structured facts plus PDF, with its data basis."""

    __tablename__ = "scouting_reports"

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    match_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("matches.id", ondelete="SET NULL"), index=True
    )
    opponent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opponents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    facts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    pdf_key: Mapped[str | None] = mapped_column(String(300))
    # {"matches": n, "events": n, "sources": ["video", "paper_report"]}
    basis: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class PlayerFeedItem(Base, EntityMixin, TenantMixin):
    """'Your scenes' (4.7): a clip for one player with rank and reason."""

    __tablename__ = "player_feed_items"
    __table_args__ = (UniqueConstraint("player_id", "clip_id"),)

    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True, nullable=False
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    clip_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clips.id", ondelete="CASCADE"), nullable=False
    )
    rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    positive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    coach_comment: Mapped[str | None] = mapped_column(Text)


class SelfAssessment(Base, EntityMixin, TenantMixin):
    __tablename__ = "self_assessments"
    __table_args__ = (
        UniqueConstraint("player_id", "match_id"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
    )

    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True, nullable=False
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    text: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConversationThread(Base, EntityMixin, TenantMixin):
    """'Ask your data' (5.1)."""

    __tablename__ = "conversation_threads"

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(160))


class AssistantMessage(Base, EntityMixin, TenantMixin):
    __tablename__ = "assistant_messages"

    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversation_threads.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    tools: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    answer: Mapped[str | None] = mapped_column(Text)
    facts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    clip_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    cost_microchf: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating: Mapped[int | None] = mapped_column(SmallInteger)  # -1, 0, 1


class PublicProfile(Base, EntityMixin, TenantMixin):
    """Opt-in public player profile (5.8); never for youth players."""

    __tablename__ = "public_profiles"

    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # {"clips": [ids], "stats": ["goals", ...], "bio": "..."}
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    consent_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
