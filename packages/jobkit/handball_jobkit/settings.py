from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class JobSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HB_", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    api_internal_url: str = "http://localhost:8000"
    internal_token: str = "dev-only-internal-token"  # noqa: S105 (local default, overridden in deployments)
    s3_endpoint_url: str | None = "http://localhost:9000"
    s3_region: str = "eu-central-2"
    s3_access_key: str = "handball"
    s3_secret_key: str = "handball-secret"  # noqa: S105
    s3_bucket_artifacts: str = "artifacts"
    work_dir: str = "/tmp/handball-work"  # noqa: S108
    # learned person detector (ADR 025): ONNX weights baked into the GPU worker image; without
    # the file the classical background detector runs (ADR 012)
    detector_model: str = "/models/yolox_s.onnx"
    detect_every: int = 3
    # 3-frame ball net(s) (docs/plans/produkt-analyse-integration.md step 2): comma-separated,
    # each a local ONNX file (ml/ball/export_onnx.py) or a key in the artifacts bucket (e.g.
    # models/ball/ball_hrp1-<sha12>.onnx), fetched once into ball_cache_dir. Two entries =
    # ensemble (hr1 + hrp1, the default for quality), one = single net (cost comparison).
    # ball_model_sha256: the files' SHA-256 in the same order (required for bucket keys).
    # Empty, missing or a wrong checksum: the YOLOX "sports ball" path stays. TEST PHASE: the
    # nets hr1/hrp1 contain DeepSport data (non-commercial) and must be replaced before go-live.
    ball_model: str = ""
    ball_model_sha256: str = ""
    ball_cache_dir: str = "/tmp/handball-models"  # noqa: S108
    ball_every: int = 1  # every 2nd frame costs about 6 points on gold v1 (11 on fast balls)
    ball_batch: int = 8
    detector_threads: int = 0
    # shirt numbers (PP-OCRv4 text models) and re-identification (person appearance network);
    # each step runs only when its model files are installed
    number_det_model: str = "/models/ch_PP-OCRv4_det_infer.onnx"
    number_rec_model: str = "/models/ch_PP-OCRv4_rec_infer.onnx"
    number_every: int = 6  # frames; 3 on the GPU image (every detection frame)
    # read a torso only when it is worth it (numbers.NumberGate): new boxes, unsettled numbers,
    # back-off after failed reads; off = every eligible torso on every number frame (as before)
    number_gate: bool = True
    # at most this many CPU seconds of shirt numbers per video second (0: no limit): keeps a whole
    # game under the job timeout on a CPU worker; on the 4-core profile reading every torso cost
    # 1.4 to 2.8 s per video second, the gate about 0.5
    number_budget: float = 0.75
    # local file or artifacts-bucket key (fetched like the ball nets, with its checksum); test
    # phase: the FastReID weights are trained on MSMT17 (non-commercial), see ml/models
    reid_model: str = "/models/reid.onnx"
    reid_model_sha256: str = ""
    reid_every: int = 30  # frames: about once per second per player
    role_model: str = "/models/roles.onnx"  # player / goalkeeper / referee (ml/roles)
    role_model_sha256: str = ""
    role_every: int = 30
    hallboard_every_s: float = 1.0  # hall scoreboard reading when the video has no overlay
    hallboard_full_every_s: float = 4.0  # whole-frame search for the board while it is not in view
    hallboard_probe_every_s: float = 0.25  # template probes for a locked board out of view
