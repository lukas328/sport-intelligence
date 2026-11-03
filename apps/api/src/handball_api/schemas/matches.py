from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, HttpUrl, model_validator

from handball_api.models.enums import JobStatus, MatchFormatKey, MatchStatus, VideoRole, VideoStatus
from handball_api.schemas.common import ApiModel, HexColor, Name


class OpponentCreate(ApiModel):
    name: Name
    primary_color: HexColor | None = None
    secondary_color: HexColor | None = None
    notes: str | None = Field(default=None, max_length=5000)


class OpponentUpdate(ApiModel):
    name: Name | None = None
    primary_color: HexColor | None = None
    secondary_color: HexColor | None = None
    notes: str | None = Field(default=None, max_length=5000)


class OpponentOut(ApiModel):
    id: uuid.UUID
    name: str
    primary_color: str | None
    secondary_color: str | None
    notes: str | None


class OpponentPlayerIn(ApiModel):
    """Number only by default. A name needs a public source (e.g. the league website), addendum
    01 4.9; names are never shown publicly or in highlights."""

    number: int = Field(ge=1, le=99)
    name: Name | None = None
    source: str | None = Field(default=None, max_length=300)
    position: str | None = Field(default=None, pattern=r"^(GK|LW|LB|CB|RB|RW|PV)$")

    @model_validator(mode="after")
    def _source(self) -> OpponentPlayerIn:
        if self.name and not (self.source and self.source.strip()):
            raise ValueError("a name needs the public source it comes from")
        return self


class OpponentPlayerOut(ApiModel):
    id: uuid.UUID
    number: int
    name: str | None
    source: str | None
    position: str | None


class MatchCreate(ApiModel):
    kind: Literal["match", "training"] = Field(
        default="match", description="training: training video without opponent (4.8)"
    )
    season_id: uuid.UUID | None = None
    opponent_id: uuid.UUID | None = None
    opponent_name: Name | None = None
    kickoff_at: datetime
    is_home: bool = True
    competition: Name | None = None
    venue: Name | None = None
    kit_own: HexColor = "#0b6bcb"
    kit_own_gk: HexColor = "#f59e0b"
    kit_opponent: HexColor = "#dc2626"
    kit_opponent_gk: HexColor = "#16a34a"
    format: MatchFormatKey | None = Field(
        default=None, description="template; default adult_2x30, youth teams youth_2x25"
    )
    period_s: int | None = Field(default=None, ge=60, le=3600)
    periods: int | None = Field(default=None, ge=1, le=4)
    is_demo: bool = Field(
        default=False, description="marks demo or synthetic data, shown as Demo in the UI"
    )

    @model_validator(mode="after")
    def _opponent(self) -> MatchCreate:
        if self.kind == "training":
            if self.opponent_id or self.opponent_name:
                raise ValueError("a training has no opponent")
        elif (self.opponent_id is None) == (self.opponent_name is None):
            raise ValueError("give either opponent_id or opponent_name")
        if self.kickoff_at.tzinfo is None:
            raise ValueError("kickoff_at needs a timezone")
        return self


class MatchUpdate(ApiModel):
    kickoff_at: datetime | None = None
    is_home: bool | None = None
    competition: Name | None = None
    venue: Name | None = None
    kit_own: HexColor | None = None
    kit_own_gk: HexColor | None = None
    kit_opponent: HexColor | None = None
    kit_opponent_gk: HexColor | None = None
    format: MatchFormatKey | None = None
    period_s: int | None = Field(default=None, ge=60, le=3600)
    periods: int | None = Field(default=None, ge=1, le=4)
    score_own: int | None = Field(default=None, ge=0, le=99)
    score_opponent: int | None = Field(default=None, ge=0, le=99)
    halftime_own: int | None = Field(default=None, ge=0, le=99)
    halftime_opponent: int | None = Field(default=None, ge=0, le=99)


class SyncOut(ApiModel):
    """Camera sync against the main video. `applied` is false when the audio match was too weak."""

    offset_ms: int | None = None
    confidence: float | None = None
    source: Literal["audio", "user_correction"] | None = None
    applied: bool | None = None


class VideoOut(ApiModel):
    id: uuid.UUID
    role: VideoRole
    status: VideoStatus
    filename: str
    size_bytes: int
    duration_s: float | None
    fps: float | None
    width: int | None
    height: int | None
    codec: str | None
    has_hls: bool
    has_poster: bool
    has_thumbnails: bool
    time_offset_ms: int
    sync: SyncOut | None
    quality_report: dict[str, Any] | None
    error: str | None
    created_at: datetime


class JobOut(ApiModel):
    id: uuid.UUID
    kind: str
    status: JobStatus
    progress: float
    stages: dict[str, Any]
    error: str | None
    video_asset_id: uuid.UUID | None
    started_at: datetime | None
    finished_at: datetime | None


class MatchOut(ApiModel):
    id: uuid.UUID
    team_id: uuid.UUID
    season_id: uuid.UUID
    kind: str
    opponent: OpponentOut | None = Field(description="null for trainings")
    kickoff_at: datetime
    is_home: bool
    competition: str | None
    venue: str | None
    kit_own: str
    kit_own_gk: str
    kit_opponent: str
    kit_opponent_gk: str
    kit_warnings: list[str] = Field(description="kit pairs with similar colours, e.g. own/opponent")
    format: str
    period_s: int
    periods: int
    score_own: int | None
    score_opponent: int | None
    halftime_own: int | None
    halftime_opponent: int | None
    status: MatchStatus
    source: str
    is_demo: bool
    kickoff_ms: dict[str, int] | None
    report_extra: dict[str, Any] | None
    videos: list[VideoOut]
    jobs: list[JobOut]


class MatchSummary(ApiModel):
    id: uuid.UUID
    team_id: uuid.UUID
    kind: str
    opponent_name: str = Field(description="empty for trainings")
    kickoff_at: datetime
    is_home: bool
    competition: str | None
    score_own: int | None
    score_opponent: int | None
    status: MatchStatus
    is_demo: bool
    has_video: bool


class UploadCreate(ApiModel):
    role: VideoRole = VideoRole.MAIN
    filename: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(gt=0)
    content_type: str = Field(default="video/mp4", max_length=100, pattern=r"^video/[\w.+-]+$")


class UploadOut(ApiModel):
    video: VideoOut
    part_size: int
    part_count: int


class PartsRequest(ApiModel):
    numbers: list[int] = Field(min_length=1, max_length=100)


class PartUrl(ApiModel):
    number: int
    url: str


class UploadedPartOut(ApiModel):
    number: int
    etag: str
    size: int


class CompletePart(ApiModel):
    number: int = Field(ge=1, le=10000)
    etag: str = Field(min_length=1, max_length=100)


class UploadComplete(ApiModel):
    parts: list[CompletePart] = Field(min_length=1, max_length=10000)


class LinkImport(ApiModel):
    url: HttpUrl
    role: VideoRole = VideoRole.MAIN


class VideoUpdate(ApiModel):
    time_offset_ms: int = Field(ge=-3_600_000, le=3_600_000)


# ---- clips, playlists, comments, annotations ------------------------------------------------


class ClipCreate(ApiModel):
    match_id: uuid.UUID
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    title: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _window(self) -> ClipCreate:
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be after start_ms")
        if self.end_ms - self.start_ms > 10 * 60 * 1000:
            raise ValueError("a clip is at most 10 minutes long")
        return self


class ClipOut(ApiModel):
    id: uuid.UUID
    match_id: uuid.UUID
    start_ms: int
    end_ms: int
    title: str | None
    source: str


class PlaylistCreate(ApiModel):
    title: Name
    description: str | None = Field(default=None, max_length=2000)
    shared_with_players: bool = False


class PlaylistUpdate(ApiModel):
    title: Name | None = None
    description: str | None = Field(default=None, max_length=2000)
    shared_with_players: bool | None = None


class PlaylistItemCreate(ApiModel):
    clip_id: uuid.UUID | None = None
    clip: ClipCreate | None = None
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _one(self) -> PlaylistItemCreate:
        if (self.clip_id is None) == (self.clip is None):
            raise ValueError("give either clip_id or clip")
        return self


class PlaylistItemOut(ApiModel):
    id: uuid.UUID
    position: int
    note: str | None
    clip: ClipOut
    match_label: str
    video_id: uuid.UUID | None = Field(description="ready main video of the clip's match")


class PlaylistOut(ApiModel):
    id: uuid.UUID
    team_id: uuid.UUID
    title: str
    description: str | None
    shared_with_players: bool
    item_count: int
    created_at: datetime


class PlaylistDetail(PlaylistOut):
    items: list[PlaylistItemOut]


class ReorderIn(ApiModel):
    item_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


class CommentCreate(ApiModel):
    t_ms: int = Field(ge=0)
    body: str = Field(min_length=1, max_length=2000)


class CommentOut(ApiModel):
    id: uuid.UUID
    t_ms: int
    body: str
    author_id: uuid.UUID | None
    author_name: str | None
    created_at: datetime
    can_delete: bool


Point = tuple[float, float]


class Shape(ApiModel):
    kind: Literal["arrow", "line", "circle", "freehand", "spotlight", "text"]
    points: list[tuple[float, float]] = Field(min_length=1, max_length=500)
    color: HexColor = "#facc15"
    width: float = Field(default=3, ge=1, le=20)
    text: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _normalised(self) -> Shape:
        if any(not (0 <= x <= 1 and 0 <= y <= 1) for x, y in self.points):
            raise ValueError("points are normalised to [0, 1]")
        return self


class AnnotationCreate(ApiModel):
    t_ms: int = Field(ge=0)
    duration_ms: int = Field(default=3000, ge=200, le=60_000)
    shapes: list[Shape] = Field(min_length=1, max_length=50)


class AnnotationOut(ApiModel):
    id: uuid.UUID
    t_ms: int
    duration_ms: int
    shapes: list[Shape]
    author_id: uuid.UUID | None
    created_at: datetime


# ---- internal (worker callbacks) ------------------------------------------------------------


class JobUpdate(ApiModel):
    status: JobStatus
    progress: float = Field(ge=0, le=1)
    stage: str | None = None
    stages: dict[str, Any] | None = None
    error: str | None = Field(default=None, max_length=4000)
    result: dict[str, Any] | None = None
    gpu_seconds: float | None = None
    cost_chf: float | None = None


# ---- analysis (pipeline stages 2 to 5) ------------------------------------------------------


class CalibrationOut(ApiModel):
    homography: list[list[float]]
    image_size: list[int]
    confidence: float
    reprojection_px: float
    source: str
    created_at: datetime


class TrackOut(ApiModel):
    track_no: int
    team: str | None
    team_confidence: float | None
    first_ms: int
    last_ms: int
    observed_share: float
    player_id: uuid.UUID | None
    player_confidence: float | None
    number: int | None
    identity_source: str | None
    physical: dict[str, Any] | None
    source: str


class TrackIdentity(ApiModel):
    """Manual identity for a track; both null clears it."""

    player_id: uuid.UUID | None = None
    number: int | None = Field(default=None, ge=0, le=99)


class FormationSegment(ApiModel):
    team: Literal["home", "away"]
    formation: str
    start_ms: int
    end_ms: int
    confidence: float


class AnalysisOut(ApiModel):
    status: Literal["none", "running", "ready", "failed"]
    formations: list[FormationSegment] = Field(default_factory=list)
    calibration: CalibrationOut | None
    tracks: list[TrackOut]
    chunk_ms: int | None
    chunks: int | None
    fps: float | None
    detector: str | None
    elapsed_s: float | None
    error: str | None
    camera: Literal["fixed", "moving"] | None = None
    panorama: PanoramaOut | None = None  # hall image to mark the court on
    needs_calibration: bool = False  # the court was not found automatically
    calibration_error: str | None = None


class CalibrationPoint(ApiModel):
    image: tuple[float, float]
    court: tuple[float, float]

    @model_validator(mode="after")
    def _ranges(self) -> CalibrationPoint:
        x, y = self.court
        if not (-5 <= x <= 45 and -5 <= y <= 25):
            raise ValueError("court point outside the court area")
        if self.image[0] < 0 or self.image[1] < 0:
            raise ValueError("image point must be inside the frame")
        return self


class CalibrationIn(ApiModel):
    points: list[CalibrationPoint] = Field(min_length=4, max_length=40)
    # "frame": image points in the video frame at frame_ms; "panorama": on the hall image
    space: Literal["frame", "panorama"] = "frame"
    frame_ms: int = Field(default=0, ge=0)


class PanoramaOut(ApiModel):
    width: int
    height: int
