from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
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
from handball_api.models.enums import ClipSource, JobStatus, MatchStatus, VideoRole, VideoStatus


class Opponent(Base, EntityMixin, TenantMixin):
    __tablename__ = "opponents"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    primary_color: Mapped[str | None] = mapped_column(String(7))
    secondary_color: Mapped[str | None] = mapped_column(String(7))
    notes: Mapped[str | None] = mapped_column(Text)


class Match(Base, EntityMixin, TenantMixin):
    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("score_own IS NULL OR score_own >= 0", name="score_own_positive"),
        CheckConstraint("score_opponent IS NULL OR score_opponent >= 0", name="score_opp_positive"),
        CheckConstraint("kind IN ('match', 'training')", name="kind_values"),
        CheckConstraint(
            "kind = 'training' OR opponent_id IS NOT NULL", name="opponent_for_matches"
        ),
        # the same official game may be in two clubs (both teams use the app), once per team
        UniqueConstraint(
            "team_id", "official_provider", "official_game_id", name="uq_matches_official"
        ),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    season_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # null only for training videos (kind = training, addendum 01 4.8)
    opponent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("opponents.id", ondelete="RESTRICT"), index=True
    )
    kind: Mapped[str] = mapped_column(String(10), nullable=False, default="match")
    kickoff_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    is_home: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    competition: Mapped[str | None] = mapped_column(String(120))
    venue: Mapped[str | None] = mapped_column(String(160))
    # Kit colours help team assignment in the pipeline (BRIEF 7.2 stage 5)
    kit_own: Mapped[str] = mapped_column(String(7), nullable=False, default="#0b6bcb")
    kit_own_gk: Mapped[str] = mapped_column(String(7), nullable=False, default="#f59e0b")
    kit_opponent: Mapped[str] = mapped_column(String(7), nullable=False, default="#dc2626")
    kit_opponent_gk: Mapped[str] = mapped_column(String(7), nullable=False, default="#16a34a")
    # only when known (the user's choice): referees often wear black like many teams, and a guessed
    # referee colour takes those players away from their team (ADR 027 addendum)
    kit_referee: Mapped[str | None] = mapped_column(String(7))
    score_own: Mapped[int | None] = mapped_column(SmallInteger)
    score_opponent: Mapped[int | None] = mapped_column(SmallInteger)
    halftime_own: Mapped[int | None] = mapped_column(SmallInteger)
    halftime_opponent: Mapped[int | None] = mapped_column(SmallInteger)
    status: Mapped[MatchStatus] = mapped_column(
        str_enum(MatchStatus), nullable=False, default=MatchStatus.SCHEDULED
    )
    # paper_report, video, demo: where the match data comes from (BRIEF 15)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="video")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # analysis failed: the match does not count against the plan (addendum 01, 4.11)
    quota_credit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # video time (ms) of the throw-off of each half: maps match clock <-> video time
    kickoff_ms: Mapped[dict[str, int] | None] = mapped_column(JSONB)
    # extra content of an imported paper report (score every 5 min, tactics notes by zone)
    report_extra: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # match format (addendum 01, 4.8): template key plus the resolved values used by the clock
    format: Mapped[str] = mapped_column(String(20), nullable=False, default="adult_2x30")
    period_s: Mapped[int] = mapped_column(Integer, nullable=False, default=1800)
    periods: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)
    # official game (federation onboarding): schedule sync and automatic report import
    official_provider: Mapped[str | None] = mapped_column(String(20))
    official_game_id: Mapped[int | None] = mapped_column(Integer)
    official_report_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VideoAsset(Base, EntityMixin, TenantMixin):
    __tablename__ = "video_assets"

    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[VideoRole] = mapped_column(str_enum(VideoRole), nullable=False)
    status: Mapped[VideoStatus] = mapped_column(
        str_enum(VideoStatus), nullable=False, default=VideoStatus.UPLOADING
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(400), nullable=False)
    upload_id: Mapped[str | None] = mapped_column(String(400))
    part_size: Mapped[int] = mapped_column(Integer, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2000))
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    duration_s: Mapped[float | None] = mapped_column(Float)
    fps: Mapped[float | None] = mapped_column(Float)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    codec: Mapped[str | None] = mapped_column(String(40))
    hls_prefix: Mapped[str | None] = mapped_column(String(400))
    proxy_key: Mapped[str | None] = mapped_column(String(400))
    poster_key: Mapped[str | None] = mapped_column(String(400))
    time_offset_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # sync against the main video: offset_ms, confidence, source (audio or user_correction)
    sync: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    quality_report: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # P2 preparation (half-time report): a partial upload analysed before the match ends
    is_partial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # storage policy (addendum 01, 4.12): original reduced to the compressed versions
    purge_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    original_purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # camera clock from the file metadata: orders several files of one match (4.8)
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # result metadata of the latest analysis run (chunks, fps, detector, timings, versions)
    analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)


class ProcessingJob(Base, EntityMixin, TenantMixin):
    __tablename__ = "processing_jobs"

    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    video_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("video_assets.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        str_enum(JobStatus), nullable=False, default=JobStatus.QUEUED
    )
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stages: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gpu_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost_chf: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class Clip(Base, EntityMixin, TenantMixin):
    """A time window in a match video. Clips are not cut; they are played from HLS (BRIEF 6.2)."""

    __tablename__ = "clips"
    __table_args__ = (CheckConstraint("end_ms > start_ms", name="window"),)

    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200))
    source: Mapped[ClipSource] = mapped_column(
        str_enum(ClipSource), nullable=False, default=ClipSource.MANUAL
    )
    source_ref: Mapped[uuid.UUID | None] = mapped_column()
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class Playlist(Base, EntityMixin, TenantMixin):
    __tablename__ = "playlists"

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    shared_with_players: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class PlaylistItem(Base, EntityMixin, TenantMixin):
    __tablename__ = "playlist_items"

    playlist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("playlists.id", ondelete="CASCADE"), index=True, nullable=False
    )
    clip_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clips.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)


class Comment(Base, EntityMixin, TenantMixin):
    """Time-stamped comment on a match video (BRIEF 11.5)."""

    __tablename__ = "comments"

    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    t_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    clip_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clips.id", ondelete="CASCADE"))


class Annotation(Base, EntityMixin, TenantMixin):
    """Drawing on the video at a point in time: shapes in normalised [0,1] coordinates."""

    __tablename__ = "annotations"

    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    t_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=3000)
    shapes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)


class CameraCalibration(Base, EntityMixin, TenantMixin):
    """Image <-> court homography of a video (BRIEF 5 "Calibration"). Latest row wins."""

    __tablename__ = "calibrations"

    video_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("video_assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    homography: Mapped[list[list[float]]] = mapped_column(JSONB, nullable=False)
    image_size: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reprojection_px: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    points: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)  # manual correspondences
    pipeline_version: Mapped[str] = mapped_column(String(20), nullable=False)


class Track(Base, EntityMixin, TenantMixin):
    """One tracked person in a video (summary; frames live in Parquet on object storage)."""

    __tablename__ = "tracks"

    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    video_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("video_assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    track_no: Mapped[int] = mapped_column(Integer, nullable=False)
    team: Mapped[str | None] = mapped_column(String(20))  # home, home_gk, away, away_gk, referee
    team_confidence: Mapped[float | None] = mapped_column(Float)
    first_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    last_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_share: Mapped[float] = mapped_column(Float, nullable=False)
    player_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL")
    )
    player_confidence: Mapped[float | None] = mapped_column(Float)
    number: Mapped[int | None] = mapped_column(Integer)  # jersey number, read or set by hand
    identity_source: Mapped[str | None] = mapped_column(String(20))  # model, user_correction
    physical: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="heuristic")
    pipeline_version: Mapped[str] = mapped_column(String(20), nullable=False)


class Event(Base, EntityMixin, TenantMixin):
    """Match event (BRIEF 4.5). Every event carries confidence and source."""

    __tablename__ = "events"
    # offline clients retry with the same id; the event is created once
    __table_args__ = (UniqueConstraint("match_id", "client_id"),)

    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column()
    type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # own, opponent
    period: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    clock_s: Mapped[float | None] = mapped_column(Float)
    t_ms: Mapped[int | None] = mapped_column(Integer)
    t_end_ms: Mapped[int | None] = mapped_column(Integer)
    player_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL"), index=True
    )
    number: Mapped[int | None] = mapped_column(SmallInteger)
    x: Mapped[float | None] = mapped_column(Float)
    y: Mapped[float | None] = mapped_column(Float)
    outcome: Mapped[str | None] = mapped_column(String(20))
    shot_zone: Mapped[str | None] = mapped_column(String(20))
    goal_zone: Mapped[str | None] = mapped_column(String(2))
    shot_type: Mapped[str | None] = mapped_column(String(20))
    turnover_type: Mapped[str | None] = mapped_column(String(20))
    assist_player_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL")
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    pipeline_version: Mapped[str | None] = mapped_column(String(20))
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class Possession(Base, EntityMixin, TenantMixin):
    __tablename__ = "possessions"

    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    start_type: Mapped[str | None] = mapped_column(String(30))
    outcome: Mapped[str | None] = mapped_column(String(30))
    phase: Mapped[str | None] = mapped_column(String(30))
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source: Mapped[str] = mapped_column(String(20), nullable=False)


class GoalCandidate(Base, EntityMixin, TenantMixin):
    """A moment of the video that is probably a goal (kind "goal") or a shot (kind "shot",
    handball_vision.goalcandidates): the coach confirms it (a shot event of the chosen side and
    outcome) or rejects it. Reviewed candidates survive a re-analysis; rejected ones are kept as
    hard negatives for training."""

    __tablename__ = "goal_candidates"

    kind: Mapped[str] = mapped_column(
        String(10), nullable=False, default="goal", server_default="goal"
    )

    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    video_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("video_assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    t_ms: Mapped[int] = mapped_column(Integer, nullable=False)  # score peak
    goal_ms: Mapped[int] = mapped_column(Integer, nullable=False)  # estimated goal / shot time
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)  # clip
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    rate: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # candidates per minute
    rank: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    suggested_side: Mapped[str | None] = mapped_column(String(10))  # own, opponent
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="open")
    side: Mapped[str | None] = mapped_column(String(10))  # confirmed shot of this side
    outcome: Mapped[str | None] = mapped_column(String(10))  # confirmed: goal, save, miss, ...
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), index=True
    )
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    template_version: Mapped[str | None] = mapped_column(String(20))
    pipeline_version: Mapped[str | None] = mapped_column(String(20))


class Correction(Base, EntityMixin, TenantMixin):
    """User correction of an event (BRIEF 10.2): kept as training data."""

    __tablename__ = "corrections"

    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column()
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # create, update, delete
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class StatsCache(Base, EntityMixin, TenantMixin):
    """Derived statistics cache, keyed by scope and a version over its inputs (BRIEF 6.4)."""

    __tablename__ = "stats_cache"
    __table_args__ = (UniqueConstraint("scope", "scope_id"),)

    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    version: Mapped[str] = mapped_column(String(120), nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
