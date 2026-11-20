"""The shared frame of the export and reel jobs (handball_worker.artifacts)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from handball_worker import artifacts


class _S3:
    def __init__(self) -> None:
        self.uploaded: list[tuple[str, str, bytes]] = []

    def download_file(self, bucket: str, key: str, dst: str) -> None:
        Path(dst).write_bytes(f"{bucket}/{key}".encode())

    def upload_file(self, src: str, bucket: str, key: str, ExtraArgs: Any = None) -> None:  # noqa: N803
        self.uploaded.append((bucket, key, Path(src).read_bytes()))


class _Settings:
    api_internal_url = "http://api/"
    internal_token = "t"
    work_dir = "/does/not/exist"

    def __init__(self, s3: _S3) -> None:
        self._s3 = s3

    def s3(self) -> _S3:
        return self._s3


class _Log:
    def __init__(self) -> None:
        self.events: list[str] = []

    def warning(self, event: str, **kw: Any) -> None:
        self.events.append(event)


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> tuple[_S3, list[tuple[str, dict[str, Any]]]]:
    s3, posts = _S3(), []

    class _Resp:
        def raise_for_status(self) -> None:
            pass

    def post(url: str, json: dict[str, Any], **kw: Any) -> _Resp:
        posts.append((url, json))
        return _Resp()

    monkeypatch.setattr(artifacts, "WorkerSettings", lambda: _Settings(s3))
    monkeypatch.setattr(httpx, "post", post)
    return s3, posts


PAYLOAD = {"bucket_videos": "v", "bucket_artifacts": "a", "out_key": "o/x.mp4"}


def test_downloads_builds_uploads_and_reports(env: tuple[_S3, list[Any]]) -> None:
    s3, posts = env

    def build(settings: Any, client: Any, work: Path, sources: dict[str, Path]) -> Path:
        out = work / "out.mp4"
        out.write_bytes(sources["1"].read_bytes() + b"!")
        return out

    body = artifacts.run_artifact_job(
        PAYLOAD,
        callback_path="/internal/x",
        build=build,
        log=_Log(),
        failed_event="x_failed",
        sources={"1": "k1"},
    )
    assert body == {"status": "ready", "key": "o/x.mp4"}
    assert s3.uploaded == [("a", "o/x.mp4", b"v/k1!")]
    assert posts == [("http://api/internal/x", body)]


def test_a_failed_build_is_reported(env: tuple[_S3, list[Any]]) -> None:
    s3, posts = env
    log = _Log()

    def build(*a: Any) -> Path:
        raise ValueError("nothing to export")

    body = artifacts.run_artifact_job(
        PAYLOAD, callback_path="/internal/x", build=build, log=log, failed_event="x_failed"
    )
    assert body == {"status": "failed", "error": "nothing to export"}
    assert log.events == ["x_failed"] and not s3.uploaded
    assert posts == [("http://api/internal/x", body)]
