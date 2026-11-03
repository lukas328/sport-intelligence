from __future__ import annotations

import json
import shutil
import wave
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pytest

from handball_gpu_worker import sync
from handball_jobkit import JobSettings, Reporter


class FakeS3:
    def __init__(self, root: Path) -> None:
        self.root = root

    def download_file(self, bucket: str, key: str, filename: str, Config: Any = None) -> None:  # noqa: N803
        shutil.copy(self.root / bucket / key, filename)


def _wav(path: Path, seconds: float, events: list[float], seed: int) -> None:
    sr = 16000  # resampled to 8 kHz by the loader
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 0.01, int(seconds * sr))
    for t in events:
        i = int(t * sr)
        x[i : i + 800] += np.sin(np.arange(800) * 0.3) * 0.7
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def _reporter() -> tuple[Reporter, list[dict[str, Any]]]:
    posts: list[dict[str, Any]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        posts.append(json.loads(req.content))
        return httpx.Response(200, json={})

    return Reporter(
        "http://api",
        "t",
        "j",
        sync.STAGES,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    ), posts


def test_run_sync(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "s3"
    events = sorted(np.random.default_rng(1).uniform(1, 38, 25).tolist())
    _wav(root / "videos/main.wav", 40, events, 0)
    _wav(root / "videos/cam.wav", 35, [t + 2.5 for t in events if t + 2.5 < 35], 1)
    monkeypatch.setattr(sync, "s3_client", lambda *a: FakeS3(root))
    rep, posts = _reporter()
    res = sync.run_sync(
        "j",
        "videos",
        "main.wav",
        "cam.wav",
        settings=JobSettings(work_dir=str(tmp_path / "work")),
        reporter=rep,
    )
    assert abs(res["offset_ms"] - 2500) <= 20
    assert res["confidence"] > 0.35
    assert posts[-1]["status"] == "succeeded"


def test_run_sync_reports_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync, "s3_client", lambda *a: FakeS3(tmp_path))
    rep, posts = _reporter()
    with pytest.raises(FileNotFoundError):
        sync.run_sync(
            "j",
            "videos",
            "missing.wav",
            "x.wav",
            settings=JobSettings(work_dir=str(tmp_path)),
            reporter=rep,
        )
    assert posts[-1]["status"] == "failed"
