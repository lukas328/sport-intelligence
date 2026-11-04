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
    detector_threads: int = 0
    # shirt numbers (PP-OCRv4 text models) and re-identification (person appearance network);
    # each step runs only when its model files are installed
    number_det_model: str = "/models/ch_PP-OCRv4_det_infer.onnx"
    number_rec_model: str = "/models/ch_PP-OCRv4_rec_infer.onnx"
    number_every: int = 6  # frames; 3 on the GPU image (every detection frame)
    reid_model: str = "/models/reid.onnx"
    reid_every: int = 30  # frames: about once per second per player
