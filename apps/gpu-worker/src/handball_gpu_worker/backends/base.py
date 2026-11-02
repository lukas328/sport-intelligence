"""Provider-agnostic GPU execution (ports and adapters, BRIEF 6.5).

Domain code submits a ``GpuJobSpec`` and receives a ``GpuJobResult`` with GPU seconds and cost.
Which provider runs the job is configuration (``HB_GPU_BACKEND``), not code.
"""

from __future__ import annotations

import importlib
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class GpuJobSpec:
    stage: str
    entrypoint: str  # "module:function", resolved inside the GPU image
    params: Mapping[str, Any] = field(default_factory=dict)
    match_id: str | None = None


@dataclass(frozen=True, slots=True)
class GpuJobResult:
    stage: str
    output: Any
    device: str
    gpu_seconds: float
    cost_chf: float


@runtime_checkable
class GpuBackend(Protocol):
    name: str

    def device(self) -> str: ...

    def run(self, spec: GpuJobSpec) -> GpuJobResult: ...


def resolve_entrypoint(entrypoint: str) -> Callable[..., Any]:
    module, _, func = entrypoint.partition(":")
    if not module or not func:
        raise ValueError(f"invalid entrypoint {entrypoint!r}, expected 'module:function'")
    fn: Callable[..., Any] = getattr(importlib.import_module(module), func)
    return fn


class LocalBackend:
    """Runs in-process on the local CPU or GPU. Used locally, in CI and on single-GPU hosts."""

    name = "local"

    def __init__(self, hourly_cost_chf: float = 0.0) -> None:
        self.hourly_cost_chf = hourly_cost_chf

    def device(self) -> str:
        if os.environ.get("CUDA_VISIBLE_DEVICES") not in (None, "", "-1"):
            return "cuda"
        return "cpu"

    def run(self, spec: GpuJobSpec) -> GpuJobResult:
        fn = resolve_entrypoint(spec.entrypoint)
        start = time.perf_counter()
        output = fn(**dict(spec.params))
        elapsed = time.perf_counter() - start
        device = self.device()
        gpu_s = elapsed if device == "cuda" else 0.0
        return GpuJobResult(
            stage=spec.stage,
            output=output,
            device=device,
            gpu_seconds=gpu_s,
            cost_chf=round(gpu_s / 3600 * self.hourly_cost_chf, 6),
        )


class _NotConfiguredBackend:
    def __init__(self, name: str) -> None:
        self.name = name

    def device(self) -> str:
        return "remote"

    def run(self, spec: GpuJobSpec) -> GpuJobResult:
        raise NotImplementedError(
            f"GPU backend {self.name!r} is planned (see docs/OPEN_QUESTIONS.md) but not implemented"
        )


_REGISTRY: dict[str, Callable[[float], GpuBackend]] = {
    "local": lambda cost: LocalBackend(cost),
    "runpod": lambda _: _NotConfiguredBackend("runpod"),
    "modal": lambda _: _NotConfiguredBackend("modal"),
    "k8s": lambda _: _NotConfiguredBackend("k8s"),
}


def register_backend(name: str, factory: Callable[[float], GpuBackend]) -> None:
    _REGISTRY[name] = factory


def get_backend(name: str, hourly_cost_chf: float = 0.0) -> GpuBackend:
    try:
        return _REGISTRY[name](hourly_cost_chf)
    except KeyError as exc:
        raise ValueError(f"unknown GPU backend {name!r}, known: {sorted(_REGISTRY)}") from exc
