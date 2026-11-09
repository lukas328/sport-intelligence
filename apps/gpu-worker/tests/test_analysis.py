from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar

import httpx
import numpy as np
import pytest

from handball_gpu_worker import analysis
from handball_jobkit import JobSettings, Reporter
from handball_vision import geometry, goalcandidates, pipeline
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
    m = SyntheticMatch(SyntheticConfig(seconds=5))
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
    assert chunk[:, 0].max() < 5000 and (chunk[:, 2] > -3).all() and (chunk[:, 2] < 43).all()
    assert (root / "artifacts/o/m/a/analysis/tracks.parquet").exists()
    teams = {t["team"] for t in res["tracks"]}
    assert {"home", "away"} <= teams
    # physical load per track: 5 s of synthetic play, nobody runs a marathon
    longest = max(res["tracks"], key=lambda t: t["last_ms"] - t["first_ms"])
    assert 0 < longest["physical"]["distance_m"] < 50
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
    # play switches sides every 2.5 s: the camera pans over the whole court within 6 s
    m = SyntheticMatch(SyntheticConfig(seconds=6, pan=1.0, focal_px=900, phase_s=2.5, walls=True))
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
    m = SyntheticMatch(SyntheticConfig(seconds=4))
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
    # 4 s are too short for goal candidates: what the observation pass would give for a game
    seen: list[int] = []

    def fake_candidates(obs: Any) -> dict[str, Any]:
        seen.append(len(obs.frames))
        return {"template": "t", "candidates": [{"t_ms": 4000, "rate": 1}]}

    monkeypatch.setattr(goalcandidates, "from_observations", fake_candidates)
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
    # goal candidates need no court: they come with the request to mark it
    assert first["goal_candidates"]["candidates"] == [{"t_ms": 4000, "rate": 1}]
    assert (root / "artifacts/o/m/a/analysis/observations.npz").exists()
    # no overlay and no number reader: no clock, the ball is not gated
    assert (root / "artifacts/o/m/a/analysis/play.json").read_text() == "null"
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
    assert second["goal_candidates"]["template"] == "t"
    assert "goal_candidates" not in second["stats"]  # sent on its own, not as a stat
    assert "goal_candidates" in second["timings_s"] and len(seen) == 2 and seen[0] > 0


@pytest.mark.parametrize(
    ("rosters", "expected"),
    [
        ({"home": [7, 14, 7], "away": [3], "away_gk": []}, {"home": {7, 14}, "away": {3}}),
        (None, None),  # older payloads without rosters
    ],
)
def test_rosters_reach_the_number_vote(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rosters: dict[str, list[int]] | None,
    expected: dict[str, set[int]] | None,
) -> None:
    class StopError(Exception):
        pass

    class Detector:
        source = "model"
        model = "stub"

    class Motion:
        moving = False

        def background(self) -> Any:
            return np.zeros((20, 40, 3), np.uint8)

    class Obs:
        motion = Motion()

    seen: dict[str, Any] = {}

    def track(*args: Any, rosters: dict[str, set[int]] | None = None, **kw: Any) -> Any:
        seen["rosters"] = rosters
        raise StopError

    monkeypatch.setattr(analysis, "s3_client", lambda *a: FakeS3(tmp_path))
    monkeypatch.setattr(analysis, "load_detector", lambda settings: Detector())
    monkeypatch.setattr(analysis, "_cached_observations", lambda *a: Obs())
    monkeypatch.setattr(analysis, "_cached_overlay", lambda *a: None)
    monkeypatch.setattr(analysis, "_points_calibration", lambda *a: object())
    monkeypatch.setattr(analysis, "_store_view", lambda *a: None)
    monkeypatch.setattr("handball_vision.observe.track", track)
    rep, _ = reporter()
    with pytest.raises(StopError):
        analysis.run_analysis(
            "j",
            "o",
            "m",
            "a",
            "videos",
            "o/m/a/proxy.mp4",
            "o/m/a/",
            KITS,
            calibration_points=[{"image": [0, 0], "court": [0, 0]}],
            settings=JobSettings(work_dir=str(tmp_path / "w")),
            reporter=rep,
            rosters=rosters,
        )
    assert seen["rosters"] == expected


@pytest.mark.parametrize("referee", [None, "#ff6a13"])
def test_only_the_kits_sent_reach_tracking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, referee: str | None
) -> None:
    """The API sends a referee kit only when it is known (ADR 027 addendum); without one the
    tracking gets no referee colour and finds referees by appearance (roles.py)."""

    class StopError(Exception):
        pass

    class Detector:
        source = "model"
        model = "stub"

    class Motion:
        moving = False

        def background(self) -> Any:
            return np.zeros((20, 40, 3), np.uint8)

    class Obs:
        motion = Motion()

    seen: dict[str, Any] = {}

    def track(obs: Any, calib: Any, kits: dict[str, Any], *args: Any, **kw: Any) -> Any:
        seen["kits"] = kits
        raise StopError

    monkeypatch.setattr(analysis, "s3_client", lambda *a: FakeS3(tmp_path))
    monkeypatch.setattr(analysis, "load_detector", lambda settings: Detector())
    monkeypatch.setattr(analysis, "_cached_observations", lambda *a: Obs())
    monkeypatch.setattr(analysis, "_cached_overlay", lambda *a: None)
    monkeypatch.setattr(analysis, "_points_calibration", lambda *a: object())
    monkeypatch.setattr(analysis, "_store_view", lambda *a: None)
    monkeypatch.setattr("handball_vision.observe.track", track)
    kits = {k: v for k, v in KITS.items() if k != "referee"}
    if referee:
        kits["referee"] = referee
    rep, _ = reporter()
    with pytest.raises(StopError):
        analysis.run_analysis(
            "j",
            "o",
            "m",
            "a",
            "videos",
            "o/m/a/proxy.mp4",
            "o/m/a/",
            kits,
            calibration_points=[{"image": [0, 0], "court": [0, 0]}],
            settings=JobSettings(work_dir=str(tmp_path / "w")),
            reporter=rep,
        )
    expected = {"home", "home_gk", "away", "away_gk"} | ({"referee"} if referee else set())
    assert set(seen["kits"]) == expected
    if referee:
        assert seen["kits"]["referee"] == (0x13, 0x6A, 0xFF)  # BGR


def test_hall_reference_with_most_floor_matches_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Earlier videos of the same hall: a missing hall image or another camera position is
    skipped (and recorded), the reference with most floor matches gives the court."""
    import cv2

    from handball_vision import hallmatch
    from handball_vision.calibration import Calibration

    root = tmp_path / "s3"
    for name in ("b", "c"):
        (root / "artifacts" / name / "analysis").mkdir(parents=True)
        cv2.imwrite(
            str(root / "artifacts" / name / "analysis" / "panorama.jpg"),
            np.full((20, 40, 3), 9 if name == "b" else 7, np.uint8),
        )
    calls: list[int] = []

    def register(reference: Any, court: Any, image: Any) -> Any:
        calls.append(int(reference[0, 0, 0]))
        if reference[0, 0, 0] == 7:
            raise CalibrationError("not the same hall or camera position (3 matches)")
        calib = Calibration(np.asarray(court), 1.0, 0.5, "heuristic", (40, 20))
        return hallmatch.HallMatch(calib, 80, 40, 120, "same_place", 0.5)

    monkeypatch.setattr(hallmatch, "register", register)
    refs: list[dict[str, Any]] = [
        {"video_id": "a", "panorama_key": "a/analysis/panorama.jpg", "homography": np.eye(3)},
        {"video_id": "c", "panorama_key": "c/analysis/panorama.jpg", "homography": np.eye(3)},
        {
            "video_id": "b",
            "panorama_key": "b/analysis/panorama.jpg",
            "homography": (np.eye(3) * 2).tolist(),
            "hall": "Halle Untermosen",
        },
    ]
    tried: list[dict[str, Any]] = []
    found = analysis._hall_calibration(
        FakeS3(root), "artifacts", np.zeros((20, 40, 3), np.uint8), refs, tmp_path, tried
    )
    assert found is not None
    calib, info = found
    assert calib.homography[0, 0] == 2
    assert info["method"] == "hall" and info["reference_video_id"] == "b"
    assert info["hall"] == "Halle Untermosen" and info["floor_inliers"] == 40
    assert [t["video_id"] for t in tried] == ["a", "c", "b"]
    assert tried[0]["error"] == "the earlier hall image is missing"
    assert "not the same hall" in tried[1]["error"]
    assert calls == [7, 9]


def test_no_fitting_hall_reference_leaves_the_automatic_court(tmp_path: Path) -> None:
    tried: list[dict[str, Any]] = []
    refs = [{"video_id": "a", "panorama_key": "a/analysis/panorama.jpg", "homography": np.eye(3)}]
    hall = np.zeros((20, 40, 3), np.uint8)
    assert analysis._hall_calibration(FakeS3(tmp_path), "x", hall, refs, tmp_path, tried) is None
    assert tried == [{"video_id": "a", "error": "the earlier hall image is missing"}]
    assert analysis._hall_calibration(FakeS3(tmp_path), "x", hall, [], tmp_path, tried) is None


@pytest.mark.parametrize("fits", [True, False])
def test_an_earlier_court_of_the_hall_comes_before_the_automatic_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fits: bool
) -> None:
    """A fresh analysis with hall references: the court carried over from the earlier video
    is used when it fits; otherwise the automatic court decides and the attempts are reported
    (here it fails too, so the coach is asked for the points)."""
    from handball_vision import observe as learned
    from handball_vision.calibration import Calibration
    from handball_vision.detection import Detection

    class StopError(Exception):
        pass

    person = Detection(0, 0, 10, 30, 0.9)

    class Detector:
        source = "model"
        model = "stub"

        def detect(self, frames: list[Any]) -> list[list[Any]]:
            return [[person] * 4 for _ in frames]

    class Motion:
        moving = False
        stats: ClassVar[dict[str, float]] = {}

        def background(self) -> Any:
            return np.zeros((20, 40, 3), np.uint8)

    class Frame:
        people = [person] * 4

    class Obs:
        motion = Motion()
        frames = [Frame()] * 5
        fps = 25.0
        timings_s: ClassVar[dict[str, float]] = {}

    carried = Calibration(np.eye(3), 1.0, 0.4, "heuristic", (40, 20))
    seen: dict[str, Any] = {}

    def hall_calibration(s3: Any, bucket: str, hall: Any, refs: Any, work: Any, tried: Any) -> Any:
        seen["refs"] = refs
        if fits:
            tried.append({"video_id": "v1", "floor_inliers": 50})
            return carried, {"method": "hall", "reference_video_id": "v1"}
        tried.append({"video_id": "v1", "error": "not the same hall or camera position"})
        return None

    def auto(obs: Any, hall: Any) -> Any:
        seen["auto"] = True
        raise CalibrationError("the camera sees the floor too flatly", "flat_view")

    def track(obs: Any, calib: Any, *args: Any, **kw: Any) -> Any:
        seen["calib"] = calib
        raise StopError

    monkeypatch.setattr(analysis, "s3_client", lambda *a: FakeS3(tmp_path))
    monkeypatch.setattr(analysis, "load_detector", lambda settings: Detector())
    monkeypatch.setattr(analysis, "sample_frames", lambda *a: [np.zeros((20, 40, 3))] * 12)
    monkeypatch.setattr(analysis, "_open", lambda *a: (None, None, 25.0, 100))
    monkeypatch.setattr(analysis, "load_number_reader", lambda settings: None)
    monkeypatch.setattr(analysis, "upload_dir_files", lambda *a: None)
    monkeypatch.setattr(analysis, "_store_view", lambda *a: None)
    monkeypatch.setattr(analysis, "_hall_calibration", hall_calibration)
    monkeypatch.setattr(analysis, "goal_candidates", lambda obs: None)
    monkeypatch.setattr(learned, "observe", lambda *a, **kw: Obs())
    monkeypatch.setattr(learned, "save_observations", lambda *a: None)
    monkeypatch.setattr(learned, "auto_calibrate", auto)
    monkeypatch.setattr(learned, "track", track)
    (tmp_path / "videos" / "o/m/a").mkdir(parents=True)
    (tmp_path / "videos" / "o/m/a/proxy.mp4").write_bytes(b"x")
    refs = [{"video_id": "v1", "panorama_key": "o/m/v1/analysis/panorama.jpg"}]
    rep, _ = reporter()

    def call() -> dict[str, Any]:
        return analysis.run_analysis(
            "j",
            "o",
            "m",
            "a",
            "videos",
            "o/m/a/proxy.mp4",
            "o/m/a/",
            KITS,
            settings=JobSettings(work_dir=str(tmp_path / "w")),
            reporter=rep,
            hall_references=refs,
        )

    if fits:
        with pytest.raises(StopError):
            call()
        assert seen["calib"] is carried and "auto" not in seen
    else:
        res = call()
        assert res["needs_calibration"] is True and seen["auto"] is True
        assert res["calibration_info"] == {
            "reason": "flat_view",
            "hall_tried": [{"video_id": "v1", "error": "not the same hall or camera position"}],
        }
    assert seen["refs"] == refs


def test_clock_play_from_overlay_or_hall_board() -> None:
    run = [(t * 1000, 100 + t) for t in range(0, 60, 5)] + [
        (t * 1000, 160) for t in range(60, 120, 5)
    ]
    reader = SimpleNamespace(clocks=run)
    play = analysis.clock_play(reader, None)  # type: ignore[arg-type]
    assert play == {"source": "overlay", "clock_readings": 24, "intervals_ms": [[0, 60_000]]}
    assert analysis.play_intervals(play) == [(0, 60_000)]
    readings = [SimpleNamespace(t_ms=t, clock_s=c) for t, c in run] + [
        SimpleNamespace(t_ms=130_000, clock_s=None)
    ]
    board = SimpleNamespace(readings=readings)
    found = analysis.clock_play(None, board)  # type: ignore[arg-type]
    assert found is not None and found["source"] == "hall_scoreboard"
    assert found["clock_readings"] == 24
    # nothing read, or a clock that never ran: no gating
    assert analysis.clock_play(None, None) is None
    assert analysis.clock_play(SimpleNamespace(clocks=[]), None) is None  # type: ignore[arg-type]
    assert analysis.play_intervals(None) is None
    assert analysis.play_intervals({"intervals_ms": []}) is None


def test_stored_clock_play_reaches_tracking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A re-run with clicked points takes the clock stretches of the observation pass."""

    class StopError(Exception):
        pass

    class Detector:
        source = "model"
        model = "stub"

    class Motion:
        moving = False

        def background(self) -> Any:
            return np.zeros((20, 40, 3), np.uint8)

    class Obs:
        motion = Motion()

    seen: dict[str, Any] = {}

    def track(*args: Any, play: list[tuple[int, int]] | None = None, **kw: Any) -> Any:
        seen["play"] = play
        raise StopError

    def cached(*a: Any) -> dict[str, Any] | None:
        return {"intervals_ms": [[1000, 9000], [12_000, 20_000]]} if a[-1] == "play.json" else None

    monkeypatch.setattr(analysis, "s3_client", lambda *a: FakeS3(tmp_path))
    monkeypatch.setattr(analysis, "load_detector", lambda settings: Detector())
    monkeypatch.setattr(analysis, "_cached_observations", lambda *a: Obs())
    monkeypatch.setattr(analysis, "_cached_json", cached)
    monkeypatch.setattr(analysis, "_points_calibration", lambda *a: object())
    monkeypatch.setattr(analysis, "_store_view", lambda *a: None)
    monkeypatch.setattr("handball_vision.observe.track", track)
    rep, _ = reporter()
    with pytest.raises(StopError):
        analysis.run_analysis(
            "j",
            "o",
            "m",
            "a",
            "videos",
            "o/m/a/proxy.mp4",
            "o/m/a/",
            KITS,
            calibration_points=[{"image": [0, 0], "court": [0, 0]}],
            settings=JobSettings(work_dir=str(tmp_path / "w")),
            reporter=rep,
        )
    assert seen["play"] == [(1000, 9000), (12_000, 20_000)]
