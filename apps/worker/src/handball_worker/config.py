from __future__ import annotations

from typing import Any

from pydantic import Field

from handball_jobkit import JobSettings, s3_client


class WorkerSettings(JobSettings):
    """CPU worker settings: the shared job settings (Redis, API callback, S3, work dir) plus the
    worker's own (queues, ffmpeg, push)."""

    worker_queues: list[str] = Field(default_factory=lambda: ["pipeline", "default"])
    heartbeat_file: str = "/tmp/handball-worker.heartbeat"
    ffmpeg: str = "ffmpeg"
    expo_access_token: str | None = None  # optional, for Expo push security (5.5)
    ffprobe: str = "ffprobe"
    x264_preset: str = "veryfast"
    hls_segment_s: int = 4
    max_import_bytes: int = 40 * 1024**3

    def s3(self) -> Any:
        return s3_client(
            self.s3_endpoint_url, self.s3_region, self.s3_access_key, self.s3_secret_key
        )
