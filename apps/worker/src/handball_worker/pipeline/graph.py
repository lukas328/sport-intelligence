"""Pipeline as a directed graph of stages with declared inputs and outputs (BRIEF 6.5, 7.2).

A stage declares the artifacts it consumes and produces. The graph derives execution order
and dependencies from these declarations, so a new stage can be plugged in without touching
existing ones. Each stage gets a cache key from its inputs, version and config, which lets
reprocessing skip unchanged stages (BRIEF 6.3, point 6).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from graphlib import CycleError, TopologicalSorter
from typing import Any


class GraphError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Stage:
    name: str
    inputs: frozenset[str]
    outputs: frozenset[str]
    version: str = "1"
    queue: str = "pipeline"  # "gpu" for stages that need the GPU worker
    config: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def of(
        cls,
        name: str,
        inputs: Iterable[str] = (),
        outputs: Iterable[str] = (),
        **kw: Any,
    ) -> Stage:
        return cls(name, frozenset(inputs), frozenset(outputs), **kw)


class PipelineGraph:
    def __init__(self, stages: Iterable[Stage], external_inputs: Iterable[str] = ()) -> None:
        self.stages: dict[str, Stage] = {}
        self.producer: dict[str, str] = {}
        self.external = frozenset(external_inputs)
        for s in stages:
            if s.name in self.stages:
                raise GraphError(f"duplicate stage {s.name!r}")
            self.stages[s.name] = s
            for out in s.outputs:
                if out in self.producer:
                    raise GraphError(
                        f"artifact {out!r} produced by {self.producer[out]!r} and {s.name!r}"
                    )
                if out in self.external:
                    raise GraphError(f"artifact {out!r} is external and cannot be produced")
                self.producer[out] = s.name
        for s in self.stages.values():
            missing = s.inputs - self.producer.keys() - self.external
            if missing:
                raise GraphError(f"stage {s.name!r} needs unknown inputs {sorted(missing)}")
        try:
            self._order = list(TopologicalSorter(self.dependencies()).static_order())
        except CycleError as exc:
            raise GraphError(f"cycle in pipeline: {exc.args[1]}") from exc

    def dependencies(self) -> dict[str, set[str]]:
        return {
            s.name: {self.producer[i] for i in s.inputs if i in self.producer}
            for s in self.stages.values()
        }

    def order(self) -> list[str]:
        return list(self._order)

    def downstream(self, changed: Iterable[str]) -> list[str]:
        """Stages to recompute when the given artifacts change (e.g. a user correction)."""
        dirty: set[str] = set()
        frontier = set(changed)
        while frontier:
            art = frontier.pop()
            for s in self.stages.values():
                if art in s.inputs and s.name not in dirty:
                    dirty.add(s.name)
                    frontier |= s.outputs
        return [n for n in self._order if n in dirty]

    def cache_key(self, stage: str, input_hashes: Mapping[str, str]) -> str:
        s = self.stages[stage]
        missing = s.inputs - input_hashes.keys()
        if missing:
            raise GraphError(f"missing input hashes for {stage!r}: {sorted(missing)}")
        payload = json.dumps(
            {
                "stage": s.name,
                "version": s.version,
                "config": s.config,
                "inputs": {k: input_hashes[k] for k in sorted(s.inputs)},
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(payload.encode()).hexdigest()
