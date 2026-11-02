from __future__ import annotations

from typing import Any

from handball_gpu_worker.backends import GpuJobSpec, get_backend
from handball_gpu_worker.config import GpuWorkerSettings


def echo(**params: Any) -> dict[str, Any]:
    """Trivial entrypoint for smoke tests of the GPU path."""
    return {"echo": params}


def run_stage(
    stage: str, entrypoint: str, params: dict[str, Any], match_id: str | None = None
) -> dict[str, Any]:
    """RQ job executed on the gpu queue. Delegates to the configured backend."""
    settings = GpuWorkerSettings()
    backend = get_backend(settings.gpu_backend, settings.gpu_hourly_cost_chf)
    r = backend.run(
        GpuJobSpec(stage=stage, entrypoint=entrypoint, params=params, match_id=match_id)
    )
    return {
        "stage": r.stage,
        "output": r.output,
        "device": r.device,
        "gpu_seconds": r.gpu_seconds,
        "cost_chf": r.cost_chf,
        "backend": backend.name,
    }
