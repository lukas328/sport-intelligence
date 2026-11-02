from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class GpuWorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HB_", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    gpu_backend: Literal["local", "runpod", "modal", "k8s"] = "local"
    gpu_queue: str = "gpu"
    # CHF per GPU hour, used for cost accounting per match (BRIEF 6.3 point 7)
    gpu_hourly_cost_chf: float = 0.0
