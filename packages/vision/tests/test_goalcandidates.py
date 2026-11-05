"""Goal candidates from the observation pass (handball_vision.goalcandidates)."""

from __future__ import annotations

import itertools
import json

import numpy as np
import pytest
from numpy.typing import NDArray

from handball_vision import goalcandidates as gc
from handball_vision import observe
from handball_vision.detection import Detection
from handball_vision.motion import CameraMotion

FPS = 25.0


def test_template_asset_is_versioned_and_consistent() -> None:
    tmpl = gc.load_template()
    raw = json.loads(gc.TEMPLATE_PATH.read_text())
    assert tmpl.version == raw["version"] and tmpl.version
    assert tmpl.channels == ("pan", "cx_v", "vx", "speed")
    assert tmpl.sign_cols == (0, 1, 2)
    assert tmpl.profile.shape == (50, 4)
    assert np.isfinite(tmpl.profile).all()
    assert raw["selection"]["default_rate"] == gc.DEFAULT_RATE
    # the evaluation that came with it: about 80 % of the goals at 2 candidates per minute
    assert raw["evaluation_leave_one_game_out"]["all"]["recall@2"] >= 0.8
    with pytest.raises(ValueError):
        gc.Template.from_dict({**raw, "profile": raw["profile"][:-1]})


def test_rolling_statistics_on_a_short_video_are_global() -> None:
    rng = np.random.default_rng(1)
    x = rng.normal(3, 2, size=(900, 2))  # 90 s, shorter than the window
    z = gc.rolling_standardise(x)
    np.testing.assert_allclose(z, (x - x.mean(axis=0)) / (x.std(axis=0) + 1e-6), atol=1e-6)
    v = rng.normal(size=900)
    q1, q2, q3 = np.percentile(v, [25, 50, 75])
    np.testing.assert_allclose(gc.rolling_rz(v), np.clip((v - q2) / (q3 - q1), -3, 10), atol=1e-9)
    # a long video: the window follows a change of level
    long = np.r_[np.zeros(3000), np.full(3000, 50.0)] + rng.normal(size=6000)
    zl = gc.rolling_standardise(long[:, None])[:, 0]
    assert abs(zl[1000]) < 3 and abs(zl[5000]) < 3


def test_pick_rates_are_prefixes_with_suppression_and_edges() -> None:
    t = np.arange(0, 360, gc.DT)  # 6 minutes
    rng = np.random.default_rng(0)
    sc = gc.smooth(rng.normal(size=len(t)), 1.0)
    sc[(t < 1.0) | (t > 359.0)] = 100  # the ends never give candidates
    got = gc.pick(t, sc)
    times = [c.t for c in got]
    assert all(2.0 <= x <= 358.0 for x in times)
    assert all(b - a > gc.NMS_S for a, b in itertools.pairwise(times))
    by_rate = {r: [c for c in got if c.rate <= r] for r in gc.RATES}
    assert [len(by_rate[r]) for r in gc.RATES] == [6, 12, 24]  # two blocks of 3 minutes
    # within a block, a higher rate only adds candidates with lower scores
    for block in (0, 1):
        inb = [c for c in got if block * 180 <= c.t < (block + 1) * 180]
        low = [c.score for c in inb if c.rate == 1]
        rest = [c.score for c in inb if c.rate > 1]
        assert min(low) >= max(rest)
        assert sorted(c.rank for c in inb) == list(range(12))


def test_candidate_clip_and_goal_time() -> None:
    d = gc.Candidate(5.0, 1.2, 2, 3).to_dict(duration_s=7.0)
    assert d == {
        "t_ms": 5000,
        "goal_ms": 3500,
        "start_ms": 0,
        "end_ms": 7000,
        "score": 1.2,
        "rate": 2,
        "rank": 3,
    }


def test_static_people_are_dropped() -> None:
    pt = np.repeat(np.arange(0, 40, 0.5), 2)
    px = np.where(np.arange(len(pt)) % 2 == 0, 100.0, 300.0 + 40 * pt)  # bench, runner
    py = np.full(len(pt), 500.0)
    static = gc.static_mask(pt, px, py)
    assert static[::2].all() and not static[1::2].any()


def test_people_motion_matches_neighbours() -> None:
    pt = np.repeat([0.0, 0.5, 1.0], 3)
    x0 = np.array([100.0, 400.0, 800.0])
    px = np.r_[x0, x0 + 50, x0 + 100]  # everyone runs right at 100 px/s
    py = np.full(9, 500.0)
    ph = np.full(9, 100.0)
    frames, med, vx, sp = gc.people_motion(pt, px, py, ph, np.ones(9, bool))
    assert frames.tolist() == [0.0, 0.5, 1.0]
    assert med.tolist() == [400.0, 450.0, 500.0]
    assert np.isnan(vx[0]) and vx[1:] == pytest.approx([100.0, 100.0])
    assert sp[1:] == pytest.approx([1.0, 1.0])  # one body height per second


def test_template_finds_its_own_profile() -> None:
    tmpl = gc.load_template()
    rng = np.random.default_rng(3)
    ch = rng.normal(size=(600, 4))
    at = 300
    i0 = at + round(tmpl.window_s[0] / gc.DT)
    goal = tmpl.profile.copy()
    goal[:, list(tmpl.sign_cols)] *= -1  # the same goal in the other direction
    ch[i0 : i0 + len(goal)] = goal
    series = gc.template_series(ch, tmpl)
    assert series[at] == pytest.approx(1.0, abs=1e-6)
    assert int(np.argmax(series)) == at


def _pan_motion(n: int, yaw_deg_per_frame: float) -> CameraMotion:
    rots: list[NDArray[np.float64] | None] = []
    for i in range(n):
        a = np.radians(yaw_deg_per_frame * i)
        rots.append(
            np.array(
                [[np.cos(a), 0, -np.sin(a)], [0, 1, 0], [np.sin(a), 0, np.cos(a)]], dtype=np.float64
            )
        )
    f = 1500.0
    return CameraMotion(
        (1280, 720),
        True,
        rots,
        [f] * n,
        ref_r=np.eye(3),
        canvas_f=f / 2,  # canvas at half the frame scale
        canvas_c=(1000.0, 400.0),
        canvas_size=(2000, 800),
    )


def test_moving_camera_inputs_are_in_reference_pixels() -> None:
    """Players standing still in the hall keep their canvas position while the camera pans;
    the camera speed is in pixels of the frame at the median zoom."""
    n = 250
    motion = _pan_motion(n, 0.05)
    k = np.array([[1500.0, 0, 640], [0, 1500.0, 360], [0, 0, 1]])
    world = np.array([[x, 0.3, 1.0] for x in (-0.1, 0.05, 0.2)])  # directions of three players
    frames = []
    for i in range(0, n, 3):
        people = []
        r = motion.rotations[i]
        assert r is not None
        for d in world:
            p = k @ r @ d
            u, v = p[0] / p[2], p[1] / p[2]
            people.append(Detection(u - 20, v - 100, u + 20, v, 0.9))
        frames.append(observe.FrameObservation(i, people, [None] * 3, []))
    obs = observe.Observations(motion, frames, {}, FPS, n)
    _cam_t, cam_x, pt, px, _py, ph, duration = gc.inputs_from_observations(obs)
    assert duration == pytest.approx(10.0)
    assert len(np.unique(pt)) == 20  # 2 Hz
    for j in range(3):
        xs = px[j::3]
        assert np.ptp(xs) < 2.0  # in the hall, not in the frame
    assert np.median(ph) == pytest.approx(100.0, rel=0.05)
    speed = np.diff(cam_x) * FPS  # px/s at the frame's scale
    assert np.median(speed) == pytest.approx(1500 * np.radians(0.05) * FPS, rel=0.02)


def _synthetic_game(
    goals: list[float], minutes: float = 6.0, seed: int = 0
) -> observe.Observations:
    """Fixed camera, 12 players attacking back and forth; after each goal everyone runs to the
    other half, then walks for 25 s before the play picks up again."""
    rng = np.random.default_rng(seed)
    n = int(minutes * 60 * FPS)
    t = np.arange(n) / FPS
    centre = np.zeros(n)
    speed = np.ones(n)
    side, last = 1.0, 0.0
    regular = [
        x for x in np.arange(17, minutes * 60, 23) if all(not g - 8 < x < g + 30 for g in goals)
    ]
    switches = sorted([*regular, *goals])
    for s in switches:  # possession changes: the play moves to the other half
        m = (t >= last) & (t < s)
        centre[m] = side * 350
        side, last = -side, s
    centre[t >= last] = side * 350
    centre = gc.smooth(np.interp(np.arange(0, n / FPS, gc.DT), t, centre), 2.5)
    centre = np.interp(t, np.arange(len(centre)) * gc.DT, centre)
    for g in goals:
        speed[(t > g + 3) & (t < g + 28)] = 0.15
    base = rng.uniform(-150, 150, size=12)
    phase = rng.uniform(0, 2 * np.pi, size=12)
    frames = []
    for i in range(0, n, 3):
        people = []
        for p in range(12):
            wobble = 60 * speed[i] * np.sin(1.3 * t[i] + phase[p])
            x = 640 + centre[i] + base[p] + wobble + rng.normal(0, 3)
            y = 420 + 25 * p + rng.normal(0, 2)
            people.append(Detection(x - 15, y - 90, x + 15, y, 0.8))
        frames.append(observe.FrameObservation(i, people, [None] * 12, []))
    return observe.Observations(CameraMotion.fixed((1280, 720), n), frames, {}, FPS, n)


def test_goal_candidates_from_observations() -> None:
    goals = [100.0, 251.0]
    out = gc.from_observations(_synthetic_game(goals))
    assert out is not None
    assert out["template"] == gc.load_template().version
    assert out["default_rate"] == 2 and out["rates"] == [1, 2, 4]
    assert out["duration_s"] == pytest.approx(360.0)
    cands = out["candidates"]
    assert len([c for c in cands if c["rate"] <= 2]) == 12
    for c in cands:
        assert c["start_ms"] == max(0, c["t_ms"] - 10_000)
        assert c["end_ms"] == min(360_000, c["t_ms"] + 4000)
    for g in goals:  # each goal is proposed at the default rate (the drawn run starts early)
        near = [c for c in cands if c["rate"] <= 2 and abs(c["t_ms"] - g * 1000) <= 8000]
        assert near, g


def test_too_little_to_go_on() -> None:
    obs = _synthetic_game([], minutes=0.4)
    assert gc.from_observations(obs) is None
    empty = observe.Observations(CameraMotion.fixed((1280, 720), 2000), [], {}, FPS, 2000)
    assert gc.from_observations(empty) is None
