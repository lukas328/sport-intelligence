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
from handball_vision import geometry, pipeline
from handball_vision.calibration import CalibrationError
from handball_vision.motion import CameraMotion
from handball_vision.synthetic import SyntheticConfig, SyntheticMatch

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


class FakeS3:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.downloads: list[str] = []

    def download_file(self, bucket: str, key: str, filename: str, Config: Any = None) -> None:  # noqa: N803
        self.downloads.append(key)
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
    # the hall image users click on, plus the motion cache for re-runs
    assert res["camera"] == "fixed" and res["needs_calibration"] is False
    assert res["panorama"] == {"width": 1280, "height": 720}
    assert (root / "artifacts/o/m/a/analysis/panorama.jpg").stat().st_size > 10_000
    assert (root / "artifacts/o/m/a/analysis/motion.npz").exists()


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


def test_failed_calibration_asks_the_user(
    synthetic: tuple[SyntheticMatch, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, root = synthetic
    monkeypatch.setattr(analysis, "s3_client", lambda *a: FakeS3(root))

    def no_court(*a: Any, **k: Any) -> Any:
        raise CalibrationError("no plausible court boundary")

    monkeypatch.setattr(pipeline, "calibrate_frames", no_court)
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
    assert res["needs_calibration"] is True and res["calibration"] is None
    assert res["tracks"] == [] and res["chunks"] == 0
    assert res["calibration_error"] == "no plausible court boundary"
    assert (root / "artifacts/o/m/a/analysis/panorama.jpg").exists()


def test_points_on_the_hall_image_of_a_fixed_camera(
    synthetic: tuple[SyntheticMatch, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    m, root = synthetic
    s3 = FakeS3(root)
    monkeypatch.setattr(analysis, "s3_client", lambda *a: s3)
    court = [[0, 0], [40, 0], [40, 20], [0, 20], [20, 0]]
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
        calibration_space="panorama",
        settings=JobSettings(work_dir=str(tmp_path)),
        reporter=rep,
    )
    assert res["calibration"]["source"] == "user_correction"
    assert res["calibration"]["image_size"] == [1280, 720]
    assert len(res["tracks"]) > 5


def test_panning_camera_with_points_on_the_panorama(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A moving camera whose court is marked on the panorama: the re-run reuses the motion."""
    root = tmp_path / "s3"
    (root / "videos/o/m/p").mkdir(parents=True)
    m = SyntheticMatch(SyntheticConfig(seconds=10, pan=1.0, focal_px=900, phase_s=4.0, walls=True))
    truth = m.write(root / "videos/o/m/p/proxy.mp4")
    s3 = FakeS3(root)
    monkeypatch.setattr(analysis, "s3_client", lambda *a: s3)
    args = ("j", "o", "m", "p", "videos", "o/m/p/proxy.mp4", "o/m/p/", KITS)
    first = analysis.run_analysis(
        *args, settings=JobSettings(work_dir=str(tmp_path)), reporter=reporter()[0]
    )
    assert first["camera"] == "moving"
    motion = CameraMotion.load(root / "artifacts/o/m/p/analysis/motion.npz")
    assert first["panorama"] == {"width": motion.canvas_size[0], "height": motion.canvas_size[1]}
    # the user marks five court points on the panorama
    to_canvas = motion.frame_to_canvas(0)
    assert to_canvas is not None and truth[0].homography is not None
    court = [[0, 0], [40, 0], [40, 20], [0, 20], [20, 10]]
    img = geometry.apply(to_canvas @ truth[0].homography, np.array(court)).tolist()
    pts = [{"image": i, "court": c} for i, c in zip(img, court, strict=True)]
    s3.downloads.clear()
    res = analysis.run_analysis(
        *args,
        calibration_points=pts,
        calibration_space="panorama",
        settings=JobSettings(work_dir=str(tmp_path)),
        reporter=reporter()[0],
    )
    assert "o/m/p/analysis/motion.npz" in s3.downloads  # no second motion pass
    assert res["calibration"]["source"] == "user_correction"
    assert res["calibration"]["image_size"] == [motion.canvas_size[0], motion.canvas_size[1]]
    assert res["stats"]["camera"] == "moving"
    # positions agree with the ground truth
    rows = np.frombuffer(
        (root / "artifacts/o/m/p/analysis/chunk_00000.bin").read_bytes(), "<f4"
    ).reshape(-1, 4)
    fps = m.cfg.fps
    gt = {g.index: np.array([[o.x, o.y] for o in g.objects if o.label != "ball"]) for g in truth}
    dist = [
        float(np.min(np.linalg.norm(gt[round(t * fps / 1000)] - [x, y], axis=1)))
        for t, _, x, y in rows
        if round(t * fps / 1000) in gt
    ]
    assert float(np.median(dist)) < 0.6


class _Blind:
    """A learned detector that sees nobody (unusual footage)."""

    source = "model"
    model = "blind"

    def detect(self, frames: list[Any]) -> list[list[Any]]:
        return [[] for _ in frames]


def test_learned_detector_that_sees_nobody_falls_back_to_the_classical_path(
    synthetic: tuple[SyntheticMatch, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _m, root = synthetic
    monkeypatch.setattr(analysis, "s3_client", lambda *a: FakeS3(root))
    monkeypatch.setattr(analysis, "load_detector", lambda settings: _Blind())
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
    assert res["detector"] == "heuristic" and res["needs_calibration"] is False


def test_learned_path_needs_calibration_then_reuses_observations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from handball_vision.detection import Detection

    root = tmp_path / "s3"
    (root / "videos" / "o/m/a").mkdir(parents=True)
    m = SyntheticMatch(SyntheticConfig(seconds=6))
    truth = m.write(root / "videos" / "o/m/a/proxy.mp4")
    boxes = {
        g.index: [Detection(*o.bbox, 0.9) for o in g.objects if o.label != "ball"] for g in truth
    }

    class Oracle:
        source = "model"
        model = "oracle"

        def __init__(self) -> None:
            self.n = 0

        def detect(self, frames: list[Any]) -> list[list[Any]]:
            out = [boxes.get(self.n, [])]
            self.n += 3
            return out

    s3 = FakeS3(root)
    monkeypatch.setattr(analysis, "s3_client", lambda *a: s3)
    monkeypatch.setattr(analysis, "load_detector", lambda settings: Oracle())
    rep, _ = reporter()
    first = analysis.run_analysis(
        "j",
        "o",
        "m",
        "a",
        "videos",
        "o/m/a/proxy.mp4",
        "o/m/a/",
        KITS,
        settings=JobSettings(work_dir=str(tmp_path / "w1")),
        reporter=rep,
    )
    # synthetic goals are not striped: no trustworthy automatic court, the user marks it
    assert first["needs_calibration"] is True and first["detector"] == "model"
    assert (root / "artifacts/o/m/a/analysis/observations.npz").exists()
    # the re-run with clicked corners reuses the stored observations (no second download)
    h = truth[0].homography if truth[0].homography is not None else None
    if h is None:
        from handball_vision.calibration import calibrate_frames

        h = calibrate_frames(
            pipeline.sample_frames(root / "videos" / "o/m/a/proxy.mp4", 8)
        ).homography
    corners = [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (0.0, 20.0), (20.0, 0.0), (20.0, 20.0)]
    pts = [{"image": list(geometry.apply(h, np.array([c]))[0]), "court": list(c)} for c in corners]
    s3.downloads.clear()
    rep2, posts2 = reporter()
    second = analysis.run_analysis(
        "j",
        "o",
        "m",
        "a",
        "videos",
        "o/m/a/proxy.mp4",
        "o/m/a/",
        KITS,
        calibration_points=pts,
        calibration_space="panorama",
        settings=JobSettings(work_dir=str(tmp_path / "w2")),
        reporter=rep2,
    )
    assert posts2[-1]["status"] == "succeeded"
    assert "o/m/a/proxy.mp4" not in s3.downloads
    assert (
        second["needs_calibration"] is False
        and second["calibration"]["source"] == "user_correction"
    )
    assert len(second["tracks"]) >= 8
