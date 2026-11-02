from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HB_", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    worker_queues: list[str] = ["pipeline", "default"]
    heartbeat_file: str = "/tmp/handball-worker.heartbeat"  # noqa: S108
