"""Declaration of the v1 analysis pipeline (BRIEF 7.2). Implementations follow from M2/M3 on."""

from __future__ import annotations

from handball_worker.pipeline.graph import PipelineGraph, Stage

PIPELINE_VERSION = "0.1.0"

STAGES: tuple[Stage, ...] = (
    Stage.of("ingest", ["upload"], ["video_asset", "proxy", "hls"]),
    Stage.of("quality", ["proxy"], ["quality_report"]),
    Stage.of("calibration", ["proxy"], ["calibration"], queue="gpu"),
    Stage.of("detection", ["proxy"], ["detections"], queue="gpu"),
    Stage.of("tracking", ["detections", "calibration"], ["tracks"]),
    Stage.of("team_assignment", ["tracks", "proxy", "match_setup"], ["tracks_team"]),
    Stage.of("identity", ["tracks_team", "upload", "roster"], ["tracks_identity"], queue="gpu"),
    Stage.of("pose", ["tracks_team", "proxy"], ["pose"], queue="gpu"),
    Stage.of("ball", ["proxy", "tracks_team"], ["ball_track"], queue="gpu"),
    Stage.of("events", ["tracks_identity", "pose", "ball_track", "calibration"], ["events_raw"]),
    Stage.of("shot_outcome", ["events_raw", "official_feed", "tracks_identity"], ["events"]),
    Stage.of("goal_zone", ["events", "goal_cams"], ["events_zoned"], queue="gpu"),
    Stage.of("possessions", ["events_zoned", "tracks_identity"], ["possessions", "phases"]),
    Stage.of("defense_formation", ["phases", "tracks_identity"], ["defense_formations"]),
    Stage.of(
        "plays", ["phases", "tracks_identity", "events_zoned", "defense_formations"], ["plays"]
    ),
    Stage.of(
        "metrics", ["events_zoned", "possessions", "phases", "plays", "corrections"], ["stats"]
    ),
    Stage.of("insights", ["stats", "plays", "events_zoned"], ["insights"]),
    Stage.of("clips", ["events_zoned", "possessions", "plays", "insights"], ["clips"]),
)

EXTERNAL_INPUTS = ("upload", "match_setup", "roster", "official_feed", "goal_cams", "corrections")


def build_pipeline() -> PipelineGraph:
    return PipelineGraph(STAGES, EXTERNAL_INPUTS)
