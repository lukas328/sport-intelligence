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


def test_shot_template_asset_is_versioned_and_consistent() -> None:
    model = gc.load_shot_model()
    raw = json.loads(gc.SHOT_TEMPLATE_PATH.read_text())
    assert model.template.version == raw["version"] and raw["name"] == "shot_candidates"
    assert model.template.channels == gc.load_template().channels
    assert model.template.profile.shape == (50, 4) and np.isfinite(model.template.profile).all()
    assert set(model.weights) <= {"shot", "goal", "lull"} and any(model.weights.values())
    sel = raw["selection"]
    assert sel["default_rate"] == gc.SHOT_DEFAULT_RATE and sel["rates_per_min"] == [2, 4, 6]
    # the estimate is the release (peak minus the median peak - release on the dev shots)
    assert sel["shot_offset_ref"].startswith("release") and 3.0 <= model.offset_s <= 7.0
    # the evaluation that came with it: most shots at the default rate, far above chance
    ev = raw["evaluation_leave_one_game_out"]["shots"]
    assert ev[f"recall@{gc.SHOT_DEFAULT_RATE}"] >= 0.8
    with pytest.raises(ValueError):
        gc.ShotModel.from_dict({**raw, "weights": {"ball": 1.0}})


def test_shot_score_is_the_weighted_sum_of_its_parts() -> None:
    t = np.arange(0, 120, gc.DT)
    rng = np.random.default_rng(3)
    s = {
        "t": t,
        **{c: gc.smooth(rng.normal(size=len(t)), 0.5) for c in ("pan", "cx_v", "vx")},
        "speed": np.abs(gc.smooth(rng.normal(size=len(t)), 0.5)) + 0.5,
    }
    goal = gc.load_template()
    model = gc.load_shot_model()
    only_goal = gc.ShotModel(model.template, {"goal": 1.0, "lull": 1.0}, 1.5)
    np.testing.assert_allclose(gc.shot_score(s, only_goal, goal), gc.score(s, goal), atol=1e-9)
    both = gc.ShotModel(model.template, {"shot": 2.0, "goal": 1.0, "lull": 1.0}, 1.5)
    shot_only = gc.ShotModel(model.template, {"shot": 1.0}, 1.5)
    np.testing.assert_allclose(
        gc.shot_score(s, both, goal),
        gc.score(s, goal) + 2 * gc.shot_score(s, shot_only, goal),
        atol=1e-9,
    )


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


def test_shot_candidate_clip_and_time() -> None:
    d = gc.Candidate(20.0, 0.5, 4, 1).to_dict(30.0, 2.0, (8.0, 4.0))
    assert (d["t_ms"], d["goal_ms"], d["start_ms"], d["end_ms"]) == (20_000, 18_000, 12_000, 24_000)


def test_candidate_clip_and_goal_time() -> None:
    # the goal lies GOAL_OFFSET_S (5 s) before the peak; the clip from 10 s before to 4 s after it
    d = gc.Candidate(12.0, 1.2, 2, 3).to_dict(duration_s=15.0)
    assert d == {
        "t_ms": 12_000,
        "goal_ms": 7000,
        "start_ms": 2000,
        "end_ms": 15_000,
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
    base = rng.uniform(-300, 300, size=12)  # spread over about 5 body heights, as in play
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
    assert out["play_s"] == pytest.approx(360.0) and out["no_play_ms"] == []  # fixed camera
    cands = out["candidates"]
    assert out["warm_up_ms"] == []  # no clock readings: no warm-up known
    assert out["clock_break_ms"] == []
    assert len(cands) == 24  # 4 per minute of play; at most 2 of them in the default list
    assert len([c for c in cands if c["rate"] <= 2]) <= 12
    assert all(c["score"] >= gc.MIN_DEFAULT_SCORE for c in cands if c["rate"] <= 2)
    for c in cands:
        assert c["start_ms"] == max(0, c["t_ms"] - 10_000)
        assert c["end_ms"] == min(360_000, c["t_ms"] + 4000)
    for g in goals:  # each goal is proposed at the default rate (the drawn run starts early)
        near = [c for c in cands if c["rate"] <= 2 and abs(c["t_ms"] - g * 1000) <= 8000]
        assert near, g
    shots = out["shots"]
    model = gc.load_shot_model()
    assert shots["template"] == model.template.version
    assert shots["default_rate"] == 4 and shots["rates"] == [2, 4, 6]
    assert shots["clip_s"] == [-8.0, 4.0]
    sc = shots["candidates"]
    assert len([c for c in sc if c["rate"] <= 4]) == 24  # 4 per minute of play
    for c in sc:
        assert c["goal_ms"] == round(c["t_ms"] - model.offset_s * 1000)
        assert c["start_ms"] == max(0, c["t_ms"] - 8000)
    for g in goals:  # goals are shots
        assert [c for c in sc if c["rate"] <= 4 and abs(c["t_ms"] - g * 1000) <= 8000], g


def test_warm_up_before_the_first_run_of_the_clock() -> None:
    t = np.arange(0, 600, gc.DT)
    # a short run (a countdown tapped during the warm-up) does not count; the throw-off at 200 s
    warm = gc.warm_up(t, [(60_000, 70_000), (200_000, 260_000), (300_000, 400_000)])
    assert warm[t < 179.9].all() and not warm[t > 180.1].any()
    assert not gc.warm_up(t, None).any()
    assert not gc.warm_up(t, [(90_000, 400_000)]).any()  # throw-off right at the start


def test_a_long_gap_between_two_runs_of_the_clock_is_a_break() -> None:
    t = np.arange(0, 3000, gc.DT)
    # first half until 1000 s, half-time break, second half from 1700 s; a 60 s stop at 2200 s
    play = [(100_000, 1_000_000), (1_700_000, 2_200_000), (2_260_000, 2_900_000)]
    brk = gc.clock_breaks(t, play)
    assert brk[(t > 1010.1) & (t < 1689.9)].all()
    assert not brk[(t < 1009.9) | (t > 1690.1)].any()  # the short stop and the edges stay play
    assert not gc.clock_breaks(t, None).any()
    assert not gc.clock_breaks(t, [(100_000, 900_000)]).any()  # one run: no gap to judge


def test_no_candidates_in_the_half_time_break() -> None:
    obs = _synthetic_game([100.0, 251.0])
    out = gc.from_observations(obs, play=[(0, 100_000), (300_000, 360_000)])
    assert out is not None
    assert out["clock_break_ms"] == [[110_100, 290_000]]  # grid steps after 110 s
    assert out["play_s"] == pytest.approx(180.0, abs=0.2)
    assert not [c for c in out["candidates"] if 110_000 < c["t_ms"] < 290_000]
    assert not [c for c in out["shots"]["candidates"] if 110_000 < c["t_ms"] < 290_000]


def test_weak_candidates_leave_the_default_list() -> None:
    found = [
        gc.Candidate(10.0, 2.0, 1, 0),
        gc.Candidate(30.0, 0.5, 1, 1),
        gc.Candidate(50.0, 1.0, 2, 2),
        gc.Candidate(70.0, 0.1, 4, 3),
    ]
    assert [c.rate for c in gc.demote_weak(found)] == [1, 4, 4, 4]


def test_no_goal_candidates_in_the_warm_up() -> None:
    obs = _synthetic_game([100.0, 251.0])
    out = gc.from_observations(obs, play=[(150_000, 360_000)])
    assert out is not None
    assert out["warm_up_ms"] == [[0, 130_000]]
    assert out["play_s"] == pytest.approx(230.0, abs=0.2)
    assert all(c["t_ms"] >= 130_000 for c in out["candidates"])
    assert all(c["t_ms"] >= 130_000 for c in out["shots"]["candidates"])


def test_too_little_to_go_on() -> None:
    obs = _synthetic_game([], minutes=0.4)
    assert gc.from_observations(obs) is None
    empty = observe.Observations(CameraMotion.fixed((1280, 720), 2000), [], {}, FPS, 2000)
    assert gc.from_observations(empty) is None


def _yaw_motion(yaws_deg: NDArray[np.float64], f: float = 1500.0) -> CameraMotion:
    rots: list[NDArray[np.float64] | None] = []
    for d in yaws_deg:
        a = np.radians(d)
        rots.append(
            np.array(
                [[np.cos(a), 0, -np.sin(a)], [0, 1, 0], [np.sin(a), 0, np.cos(a)]], dtype=np.float64
            )
        )
    return CameraMotion(
        (1280, 720),
        True,
        rots,
        [f] * len(rots),
        ref_r=np.eye(3),
        canvas_f=f / 2,
        canvas_c=(2000.0, 400.0),
        canvas_size=(4000, 800),
    )


def test_wide_pans_keep_their_speed() -> None:
    """A steady pan from one goal to the other (-60 to +60 degrees) has the same speed at the
    ends as in the middle: the camera track is an angle, not the planar canvas x, which is
    stretched by 1 / cos^2 (4x at 60 degrees)."""
    n = 1200
    motion = _yaw_motion(np.linspace(-60, 60, n))
    cam_x = gc._camera_x(motion, n)
    speed = np.diff(cam_x) * FPS
    expected = 1500 * np.radians(120 / (n - 1)) * FPS
    assert speed == pytest.approx(np.full(n - 1, expected), rel=1e-6)
    # people standing in the hall stay put on the same cylinder while the camera turns
    pts = np.array([[2000.0 + 750 * np.tan(np.radians(a)), 500.0] for a in (-50, 0, 50)])
    ref = gc._canvas_to_reference(motion, pts)
    assert ref[:, 0] == pytest.approx(1500 * np.radians([-50, 0, 50]))


def test_a_cut_is_no_pan() -> None:
    """A cut moves the camera track by a large step in one frame: it is no pan. A real pan
    stays, also when the stream repeats frames (steps of 0, 0, 3x)."""
    n = 1500
    t = np.arange(n) / FPS
    cam_x = np.where(t < 20, 0.0, 2000.0)  # cut at 20 s
    pan = np.clip((t - 40) * 200, 0, 1000)  # 200 px/s from 40 to 45 s
    cam_x = cam_x + pan[np.arange(n) // 3 * 3]  # every frame shown three times
    pt = np.repeat(np.arange(0, 60, 0.5), 3)
    px = np.tile([100.0, 600.0, 1100.0], len(pt) // 3) + 30 * np.sin(pt)
    s = gc.signals(t, cam_x, pt, px, np.full(len(pt), 500.0), np.full(len(pt), 90.0), 60.0)
    tg = s["t"]
    assert np.abs(s["pan"][(tg > 18) & (tg < 22)]).max() < 1.0
    assert np.mean(s["pan"][(tg > 41) & (tg < 44)]) == pytest.approx(200.0, rel=0.03)
    steps = np.r_[np.zeros(10), 5.0, np.zeros(10)]
    assert gc.drop_jumps(steps).tolist() == steps.tolist()  # small: kept
    steps[10] = 300.0
    assert not gc.drop_jumps(steps).any()


def test_no_play_while_a_moving_camera_is_parked() -> None:
    t = np.arange(0, 600, gc.DT)  # 10 minutes: play, 4 minutes parked, play
    rng = np.random.default_rng(2)
    pan = 120 * np.sin(2 * np.pi * t / 25) + rng.normal(0, 5, len(t))
    parked = (t >= 180) & (t < 420)
    pan[parked] = rng.normal(0, 5, parked.sum())
    s = {"t": t, "pan": pan}
    idle = gc.no_play(s, moving=True)
    assert idle[(t > 260) & (t < 340)].all()
    assert not idle[(t < 175) | (t > 425)].any()
    assert not gc.no_play(s, moving=False).any()  # a fixed camera is always still
    runs = gc.intervals(t, idle)
    assert len(runs) == 1 and 180 <= runs[0][0] < 260 and 340 < runs[0][1] <= 420
    # a parked camera for less than the window (a time-out and the attack after it) is play
    short = pan.copy()
    short[(t >= 180) & (t < 300)] = rng.normal(0, 5, 1200)
    short[(t >= 300) & (t < 420)] = 120 * np.sin(2 * np.pi * t[(t >= 300) & (t < 420)] / 25)
    assert not gc.no_play({"t": t, "pan": short}, moving=True).any()


def test_no_play_while_people_bunch() -> None:
    """A time-out: everybody gathers in one spot for a minute (a fixed camera, so only the people
    tell). Spread out over 5 to 6 body heights in play, within 1.5 during the time-out; a moment
    with fewer than 3 people in view is no evidence either way."""
    rng = np.random.default_rng(5)
    pt, px = [], []
    for f in np.arange(0, 300, 0.5):
        timeout = 120 <= f < 180
        n = 1 if 240 <= f < 260 else 14  # a close-up: one person in view
        width = 135.0 if timeout else 720.0  # body height 90 px
        pt.append(np.full(n, f))
        px.append(400 + rng.uniform(0, width, n) + (0 if timeout else 80 * np.sin(f / 7)))
    t_p, x_p = np.concatenate(pt), np.concatenate(px)
    y_p = 500 + rng.normal(0, 20, len(t_p))
    s = gc.signals(
        np.arange(0, 300, 1 / FPS),
        np.zeros(300 * 25),
        t_p,
        x_p,
        y_p,
        np.full(len(t_p), 90.0),
        300.0,
    )
    t = s["t"]
    assert np.median(s["spread"][(t > 20) & (t < 100)]) == pytest.approx(5.6, abs=0.5)
    assert np.all(s["spread"][(t > 130) & (t < 170)] < 1.5)
    idle = gc.no_play(s, moving=False)
    assert idle[(t > 135) & (t < 165)].all()
    assert not idle[(t < 110) | (t > 190)].any()  # the close-up at 240 to 260 s included
    runs = gc.intervals(t, idle)
    assert len(runs) == 1 and 115 <= runs[0][0] <= 140 and 160 <= runs[0][1] <= 185
    assert not gc.bunched({"t": t, "pan": np.zeros(len(t))}).any()  # no people channel
    nobody = {**s, "spread": np.full(len(t), np.nan)}
    assert not gc.no_play(nobody, moving=False).any()


def test_running_nanmedian() -> None:
    x = np.r_[np.full(100, 2.0), np.full(100, np.nan), np.full(100, 6.0)]
    med = gc.running_nanmedian(x, 4.0)  # 40 samples
    assert med[:80].tolist() == [2.0] * 80 and med[-80:].tolist() == [6.0] * 80
    assert np.isnan(med[130:170]).all()
    assert len(gc.running_nanmedian(np.zeros(0), 4.0)) == 0


def test_pick_skips_no_play_and_scales_the_quota() -> None:
    t = np.arange(0, 360, gc.DT)
    sc = gc.smooth(np.random.default_rng(4).normal(size=len(t)), 1.0)
    play = ~((t >= 60) & (t < 300))  # 2 minutes of play
    got = gc.pick(t, sc, play=play)
    assert all(not 60 <= c.t < 300 for c in got)
    # block 1: 1 minute of play, block 2: 1 minute
    assert [len([c for c in got if c.rate <= r]) for r in gc.RATES] == [2, 4, 8]


def test_a_fixed_camera_with_a_little_drift_is_not_parked() -> None:
    """A tripod camera that drifts a degree or two counts as moving in motion.py; it stands
    still all game, which is not a parked operated camera: the whole video stays play and the
    goals are found (staging 2026-11-19: 2 degrees of pan, no candidates at all)."""
    goals = [100.0, 251.0]
    obs = _synthetic_game(goals)
    n = obs.total
    drifting = _pan_motion(n, 0.0)  # moving, but the camera does not turn
    drifting.canvas_f, drifting.canvas_c, drifting.canvas_size = 1500.0, (640.0, 360.0), (1280, 720)
    drifting.stats = {"pan_deg": 2.0, "zoom_ratio": 1.03}
    obs.motion = drifting
    assert not gc.operated(drifting)
    out = gc.from_observations(obs)
    assert out is not None
    assert out["play_s"] == pytest.approx(out["duration_s"], abs=0.5)
    assert out["no_play_ms"] == []
    found = [c["t_ms"] for c in out["candidates"] if c["rate"] <= gc.DEFAULT_RATE]
    assert all(any(abs(f - g * 1000) <= 8000 for f in found) for g in goals)
    # the same stillness from a camera that follows the play elsewhere in the video is parked
    drifting.stats = {"pan_deg": 60.0, "zoom_ratio": 1.03}
    assert gc.operated(drifting)
    parked = gc.from_observations(obs)
    assert parked is not None
    assert parked["play_s"] == 0.0
    # without the pan range (older motion files) every moving camera is operated, as before
    drifting.stats = {}
    assert gc.operated(drifting)
    assert not gc.operated(CameraMotion.fixed((1280, 720), n))
