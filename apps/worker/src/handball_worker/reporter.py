"""Reports job progress to the API (internal endpoint, shared-secret header)."""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog

log = structlog.get_logger("worker.reporter")


class Reporter:
    def __init__(
        self,
        api_url: str,
        token: str,
        job_id: str,
        stages: dict[str, float],
        client: httpx.Client | None = None,
    ) -> None:
        self.url = f"{api_url.rstrip('/')}/internal/jobs/{job_id}"
        self.headers = {"x-internal-token": token}
        self.weights = stages
        self.stages: dict[str, dict[str, Any]] = {s: {"status": "pending"} for s in stages}
        self.client = client or httpx.Client(timeout=15)
        self._last = 0.0
        self._current: str | None = None
        self._fraction = 0.0

    def progress(self) -> float:
        done = sum(w for s, w in self.weights.items() if self.stages[s]["status"] == "done")
        cur = self.weights.get(self._current or "", 0.0) * self._fraction
        return round(min(1.0, (done + cur) / sum(self.weights.values())), 4)

    def _send(self, body: dict[str, Any], force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._last < 2:
            return
        self._last = now
        for attempt in range(3):
            try:
                r = self.client.post(self.url, json=body, headers=self.headers)
                if r.status_code < 500:
                    return
            except httpx.HTTPError as exc:
                log.warning("report_failed", attempt=attempt, error=str(exc))
            time.sleep(1 + attempt * 2)

    def stage(self, name: str) -> None:
        if self._current:
            self.stages[self._current] = {
                **self.stages[self._current],
                "status": "done",
                "finished": time.time(),
            }
        self._current, self._fraction = name, 0.0
        self.stages[name] = {"status": "running", "started": time.time()}
        self._send(
            {
                "status": "running",
                "progress": self.progress(),
                "stage": name,
                "stages": self.stages,
            },
            force=True,
        )

    def fraction(self, f: float) -> None:
        self._fraction = max(0.0, min(1.0, f))
        self._send({"status": "running", "progress": self.progress(), "stage": self._current})

    def succeed(self, result: dict[str, Any]) -> None:
        if self._current:
            self.stages[self._current] = {
                **self.stages[self._current],
                "status": "done",
                "finished": time.time(),
            }
        self._send(
            {"status": "succeeded", "progress": 1.0, "stages": self.stages, "result": result},
            force=True,
        )

    def fail(self, error: str) -> None:
        if self._current:
            self.stages[self._current] = {**self.stages[self._current], "status": "failed"}
        self._send(
            {
                "status": "failed",
                "progress": self.progress(),
                "stages": self.stages,
                "error": error[:4000],
            },
            force=True,
        )
