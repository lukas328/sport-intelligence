"""Worker settings build on the shared job settings (jobkit)."""

from __future__ import annotations

import pytest

from handball_jobkit import JobSettings
from handball_worker.config import WorkerSettings


def test_worker_settings_extend_job_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HB_S3_ENDPOINT_URL", "http://s3.test:9000")
    monkeypatch.setenv("HB_WORKER_QUEUES", '["pipeline"]')
    monkeypatch.setenv("HB_API_INTERNAL_URL", "http://api.test")
    s = WorkerSettings()
    assert isinstance(s, JobSettings)
    assert (s.s3_endpoint_url, s.api_internal_url, s.worker_queues) == (
        "http://s3.test:9000",
        "http://api.test",
        ["pipeline"],
    )
    assert WorkerSettings(_env_file=None).work_dir == JobSettings().work_dir
    client = s.s3()
    assert client.meta.endpoint_url == "http://s3.test:9000"
    assert client.meta.region_name == s.s3_region


def test_default_queues_are_not_shared() -> None:
    a, b = WorkerSettings(), WorkerSettings()
    a.worker_queues.append("gpu")
    assert b.worker_queues == ["pipeline", "default"]
