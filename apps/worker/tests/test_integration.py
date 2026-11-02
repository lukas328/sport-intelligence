"""Round trip through the real worker container: `make test-integration`."""

from __future__ import annotations

import os
import time

import pytest
from redis import Redis
from rq import Queue

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("queue", "func", "kwargs"),
    [
        ("default", "handball_worker.jobs.ping", {"payload": "it"}),
        (
            "gpu",
            "handball_gpu_worker.jobs.run_stage",
            {"stage": "smoke", "entrypoint": "handball_gpu_worker.jobs:echo", "params": {"a": 1}},
        ),
    ],
)
def test_job_round_trip(queue: str, func: str, kwargs: dict[str, object]) -> None:
    conn = Redis.from_url(os.environ.get("HB_REDIS_URL", "redis://localhost:6379/0"))
    job = Queue(queue, connection=conn).enqueue(func, kwargs=kwargs)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if job.get_status(refresh=True) in ("finished", "failed"):
            break
        time.sleep(0.2)
    assert job.get_status() == "finished", job.exc_info
    assert job.return_value() is not None
