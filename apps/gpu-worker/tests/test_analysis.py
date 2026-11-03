from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pytest

from handball_gpu_worker import analysis
from handball_jobkit import JobSettings, Reporter
from handball_vision import geometry
from handball_vision.synthetic import SyntheticConfig, SyntheticMatch

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


class FakeS3:
    def __init__(self, root: Path) -> None:
        self.root = root

    def download_file(self, bucket: str, key: str, filename: str, Config: Any = None) -> None:  # noqa: N803
        shutil.copy(self.root / bucket / key, filename)

    def upload_file(
        self,
        filename: str,
        bucket: str,
        key: str,
        Config: Any = None,  # noqa: N803
        ExtraArgs: Any = None,  # noqa: N803
    ) -> None:
        dst = self.root / bucket / key
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(filename, dst)


@pytest.fixture(scope="module")
def synthetic(tmp_path_factory: pytest.TempPathFactory) -> tuple[SyntheticMatch, Path]:
    root = tmp_path_factory.mktemp("s3")
    (root / "videos" / "o/m/a").mkdir(parents=True)
    m = SyntheticMatch(SyntheticConfig(seconds=8))
    m.write(root / "videos" / "o/m/a/proxy.mp4")
    return m, root


def reporter() -> tuple[Reporter, list[dict[str, Any]]]:
    posts: list[dict[str, Any]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        posts.append(json.loads(req.content))
        return httpx.Response(200, json={})

    return Reporter(
        "http://api",
        "t",
        "j",
        analysis.STAGES,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    ), posts


KITS = {
    "home": "#2828c8",
    "home_gk": "#e6c828",
    "away": "#ebe6e6",
    "away_gk": "#3caa3c",
    "referee": "#191919",
}


def test_run_analysis(
    synthetic: tuple[SyntheticMatch, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _m, root = synthetic
    monkeypatch.setattr(analysis, "s3_client", lambda *a: FakeS3(root))
    rep, posts = reporter()
    res = analysis.run_analysis(
        "j",
        "o",
        "m",
        "a",
        "videos",
        "o/m/a/proxy.mp4",
        "o/m/a/",
        KITS,
        settings=JobSettings(work_dir=str(tmp_path)),
        reporter=rep,
    )
    assert posts[-1]["status"] == "succeeded"
    assert res["calibration"]["source"] == "heuristic"
    assert res["chunks"] == 1 and res["chunk_ms"] == 30000
    assert res["detector"] == "heuristic"
    chunk = np.frombuffer(
        (root / "artifacts/o/m/a/analysis/chunk_00000.bin").read_bytes(), "<f4"
    ).reshape(-1, 4)
    assert chunk[:, 0].max() < 8000 and (chunk[:, 2] > -3).all() and (chunk[:, 2] < 43).all()
    assert (root / "artifacts/o/m/a/analysis/tracks.parquet").exists()
    teams = {t["team"] for t in res["tracks"]}
    assert {"home", "away"} <= teams
    # physical load per track: 8 s of synthetic play, nobody runs a marathon
    longest = max(res["tracks"], key=lambda t: t["last_ms"] - t["first_ms"])
    assert 0 < longest["physical"]["distance_m"] < 80
    assert longest["physical"]["max_speed_ms"] < 10
    assert isinstance(res["formations"], list)


def test_manual_calibration_points(
    synthetic: tuple[SyntheticMatch, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    m, root = synthetic
    monkeypatch.setattr(analysis, "s3_client", lambda *a: FakeS3(root))
    court = [[0, 0], [40, 0], [40, 20], [0, 20]]
    img = geometry.apply(m.h, np.array(court)).tolist()
    pts = [{"image": i, "court": c} for i, c in zip(img, court, strict=True)]
    rep, _ = reporter()
    res = analysis.run_analysis(
        "j",
        "o",
        "m",
        "a",
        "videos",
        "o/m/a/proxy.mp4",
        "o/m/a/",
        KITS,
        calibration_points=pts,
        settings=JobSettings(work_dir=str(tmp_path)),
        reporter=rep,
    )
    assert res["calibration"]["source"] == "user_correction"
    assert res["calibration"]["reprojection_px"] < 0.01


def test_bad_points_report_failure(
    synthetic: tuple[SyntheticMatch, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, root = synthetic
    monkeypatch.setattr(analysis, "s3_client", lambda *a: FakeS3(root))
    rep, posts = reporter()
    pts: list[dict[str, list[float]]] = [{"image": [0.0, 0.0], "court": [0.0, 0.0]}] * 4
    with pytest.raises(Exception):  # noqa: B017
        analysis.run_analysis(
            "j",
            "o",
            "m",
            "a",
            "videos",
            "o/m/a/proxy.mp4",
            "o/m/a/",
            KITS,
            calibration_points=pts,
            settings=JobSettings(work_dir=str(tmp_path)),
            reporter=rep,
        )
    assert posts[-1]["status"] == "failed"
