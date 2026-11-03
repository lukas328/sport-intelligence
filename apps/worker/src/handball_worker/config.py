from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HB_", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    worker_queues: list[str] = ["pipeline", "default"]
    heartbeat_file: str = "/tmp/handball-worker.heartbeat"

    api_internal_url: str = "http://localhost:8000"
    internal_token: str = "dev-only-internal-token"
    s3_endpoint_url: str | None = "http://localhost:9000"
    s3_region: str = "eu-central-2"
    s3_access_key: str = "handball"
    s3_secret_key: str = "handball-secret"
    work_dir: str = "/tmp/handball-work"
    ffmpeg: str = "ffmpeg"
    expo_access_token: str | None = None  # optional, for Expo push security (5.5)
    ffprobe: str = "ffprobe"
    x264_preset: str = "veryfast"
    hls_segment_s: int = 4
    max_import_bytes: int = 40 * 1024**3
