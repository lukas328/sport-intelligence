"""Reports job progress to the API (internal endpoint, shared-secret header)."""

from __future__ import annotations

import threading
import time
from typing import Any

import httpx
import structlog

log = structlog.get_logger("worker.reporter")
ATTEMPTS = 3
# While a stage runs the reporter says it is still there this often, also when the stage itself
# reports no fraction (a download, the court, the upload): a job silent for many minutes has lost
# its worker, and the API's watchdog can restart it instead of the coach waiting for hours.
HEARTBEAT_S = 60.0


class ReportError(RuntimeError):
    """A terminal job update did not reach the API."""


def _answer(r: httpx.Response) -> dict[str, Any] | None:
    try:
        data = r.json()
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def clicked_points(answer: dict[str, Any] | None) -> dict[str, Any] | None:
    """Court points the coach marked on the hall image while this job ran, from the API's answer
    to a stage report: `{"points", "space", "frame_ms"}`, or None."""
    court = (answer or {}).get("court_points")
    if not isinstance(court, dict) or not court.get("points"):
        return None
    return court


class Reporter:
    def __init__(
        self,
        api_url: str,
        token: str,
        job_id: str,
        stages: dict[str, float],
        client: httpx.Client | None = None,
        heartbeat_s: float | None = HEARTBEAT_S,
    ) -> None:
        self.url = f"{api_url.rstrip('/')}/internal/jobs/{job_id}"
        self.headers = {"x-internal-token": token}
        self.weights = stages
        self.stages: dict[str, dict[str, Any]] = {s: {"status": "pending"} for s in stages}
        self.client = client or httpx.Client(timeout=15)
        self._last = 0.0
        self._current: str | None = None
        self._fraction = 0.0
        self._lock = threading.Lock()
        self._heartbeat_s = heartbeat_s
        self._stop = threading.Event()
        self._beat: threading.Thread | None = None

    def progress(self) -> float:
        done = sum(w for s, w in self.weights.items() if self.stages[s]["status"] == "done")
        cur = self.weights.get(self._current or "", 0.0) * self._fraction
        return round(min(1.0, (done + cur) / sum(self.weights.values())), 4)

    def _send(
        self, body: dict[str, Any], force: bool = False, terminal: bool = False
    ) -> dict[str, Any] | None:
        """POST the update, three attempts on network errors and 5xx answers. Progress updates
        give up quietly (the next one follows); a terminal update (succeeded / failed) raises
        ReportError, so RQ marks the job failed instead of the API waiting for it forever. Returns
        the API's answer (the job as the API sees it), None when it was not sent or not readable."""
        with self._lock:
            now = time.monotonic()
            if not (force or terminal) and now - self._last < 2:
                return None
            self._last = now
        error = ""
        for attempt in range(ATTEMPTS):
            try:
                r = self.client.post(self.url, json=body, headers=self.headers)
                if r.status_code < 500:
                    return _answer(r)
                error = f"HTTP {r.status_code}"
            except httpx.HTTPError as exc:
                error = str(exc) or type(exc).__name__
            log.warning("report_failed", attempt=attempt, error=error, status=body.get("status"))
            if attempt < ATTEMPTS - 1:
                time.sleep(1 + attempt * 2)
        if terminal:
            raise ReportError(f"could not report {body.get('status')} to the API: {error}")
        return None

    def _start_heartbeat(self) -> None:
        if not self._heartbeat_s or self._beat is not None or self._stop.is_set():
            return
        self._beat = threading.Thread(target=self._heartbeat, name="job-heartbeat", daemon=True)
        self._beat.start()

    def _heartbeat(self) -> None:
        interval = float(self._heartbeat_s or HEARTBEAT_S)
        while not self._stop.wait(interval):
            if time.monotonic() - self._last < interval / 2:
                continue  # a progress update went out a moment ago
            self._send(
                {"status": "running", "progress": self.progress(), "stage": self._current},
                force=True,
            )

    def stop(self) -> None:
        """No more heartbeats: the job ended (succeed and fail call it)."""
        self._stop.set()

    def stage(self, name: str) -> dict[str, Any] | None:
        """Start stage `name`; returns the API's answer (e.g. court points the coach marked while
        the job ran, `clicked_points`)."""
        if self._current:
            self.stages[self._current] = {
                **self.stages[self._current],
                "status": "done",
                "finished": time.time(),
            }
        self._current, self._fraction = name, 0.0
        self.stages[name] = {"status": "running", "started": time.time()}
        self._start_heartbeat()
        return self._send(
            {
                "status": "running",
                "progress": self.progress(),
                "stage": name,
                "stages": self.stages,
            },
            force=True,
        )

    def share(self, view: dict[str, Any]) -> dict[str, Any] | None:
        """Tell the API what the coach can already use while the job runs (the hall image:
        `{"camera", "panorama": {"width", "height"}}`)."""
        return self._send(
            {
                "status": "running",
                "progress": self.progress(),
                "stage": self._current,
                "view": view,
            },
            force=True,
        )

    def fraction(self, f: float) -> None:
        """How far the running stage is (0 to 1). It goes to the API in the stage itself too: the
        job's progress weighs the stages by fixed shares, the stage's own pace is measured."""
        self._fraction = max(0.0, min(1.0, f))
        if self._current:
            self.stages[self._current] = {
                **self.stages[self._current],
                "fraction": round(self._fraction, 4),
            }
        self._send(
            {
                "status": "running",
                "progress": self.progress(),
                "stage": self._current,
                "stages": self.stages,
            }
        )

    def succeed(self, result: dict[str, Any]) -> None:
        self.stop()
        if self._current:
            self.stages[self._current] = {
                **self.stages[self._current],
                "status": "done",
                "finished": time.time(),
            }
        self._send(
            {"status": "succeeded", "progress": 1.0, "stages": self.stages, "result": result},
            terminal=True,
        )

    def fail(self, error: str) -> None:
        self.stop()
        if self._current:
            self.stages[self._current] = {**self.stages[self._current], "status": "failed"}
        self._send(
            {
                "status": "failed",
                "progress": self.progress(),
                "stages": self.stages,
                "error": error[:4000],
            },
            terminal=True,
        )
