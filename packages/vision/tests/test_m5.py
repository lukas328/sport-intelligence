"""Physical load, jersey-number identity and audio sync (M5)."""

from __future__ import annotations

import numpy as np
import pytest

from handball_vision.audio import estimate_offset, onset_envelope
from handball_vision.identity import Reading, TrackSpan, assign_numbers, to_roster
from handball_vision.physical import BANDS, from_dict, merge, physical
from handball_vision.synthetic import DEMO, SyntheticConfig, SyntheticMatch


def _walk(
    speed: float, seconds: float, hz: int = 25, noise: float = 0.0, seed: int = 0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    t = np.arange(0, seconds * 1000, 1000 / hz)
    x = 5 + speed * t / 1000
    y = np.full_like(t, 10.0)
    return t, x + rng.normal(0, noise, len(t)), y + rng.normal(0, noise, len(t))


def test_constant_speed_distance_and_band() -> None:
    t, x, y = _walk(3.0, 10)
    p = physical(t, x, y)
    assert p.distance_m == pytest.approx(30, rel=0.05)
    assert p.band_distance_m["jog"] == pytest.approx(p.distance_m, rel=0.01)
    assert p.max_speed_ms == pytest.approx(3.0, rel=0.05)
    assert p.sprints == 0
    assert sum(sum(r) for r in p.heatmap) == pytest.approx(1.0)


def test_noise_is_smoothed_out() -> None:
    """A standing player with 0.3 m jitter must not 'run' hundreds of metres."""
    t, x, y = _walk(0.0, 60, noise=0.3)
    raw = float(np.hypot(np.diff(x), np.diff(y)).sum())
    p = physical(t, x, y)
    assert raw > 500
    assert p.distance_m < raw / 5
    assert p.band_distance_m["sprint"] == 0


def test_sprint_detection_and_gaps() -> None:
    t1, x1, y1 = _walk(1.0, 5)
    t2, x2, y2 = _walk(7.0, 3)
    t2 = t2 + 5000
    x2 = x2 - 5 + x1[-1]
    # a 3 s gap (track lost) and a teleport must not count
    t3, x3, y3 = _walk(1.0, 4)
    t3 = t3 + 11000
    x3 = x3 + 10
    p = physical(
        np.concatenate([t1, t2, t3]), np.concatenate([x1, x2, x3]), np.concatenate([y1, y2, y3])
    )
    assert p.sprints == 1
    assert p.max_speed_ms == pytest.approx(7.0, rel=0.1)
    assert p.band_distance_m["sprint"] == pytest.approx(21, rel=0.15)
    assert p.distance_m < 5 + 21 + 4 + 3


def test_identity_jump_is_not_a_sprint() -> None:
    """A track that takes over a neighbour 2 m ahead (an identity switch in an occlusion) jumps
    once. Smoothed first, the jump read as three steps of 9 to 10 m/s (34 km/h top speed); found
    on the raw positions it is dropped and the top speed stays the true 6 m/s."""
    t, x, y = _walk(6.0, 6, noise=0.05)
    x = np.where(t >= 3000, x + 2.0, x)
    p = physical(t, x, y)
    assert p.max_speed_ms == pytest.approx(6.0, rel=0.05)
    assert p.distance_m == pytest.approx(36, rel=0.1)
    assert p.sprints == 2  # the track is two pieces of 3 s, each one sprint


def test_predicted_points_are_left_out() -> None:
    """The tracker coasts a lost player at his last velocity and snaps back on the next
    detection: those predictions are not measurements."""
    t, x, y = _walk(1.0, 6)
    observed = (t < 2000) | (t >= 2800)
    coast = (t >= 2000) & (t < 2800)
    x = np.where(coast, x + 6.0 * (t - 2000) / 1000, x)  # predicted far ahead, then corrected
    raw = physical(t, x, y)
    p = physical(t, x, y, observed)
    assert raw.distance_m > 8  # 4.8 m ahead and back
    assert p.max_speed_ms == pytest.approx(1.0, rel=0.1)
    assert p.distance_m == pytest.approx(6, rel=0.1)
    assert physical(t, x, y, np.zeros(len(t), bool)).distance_m == 0


def test_top_speed_must_be_held_for_a_second() -> None:
    """A 600 ms burst (a box lagging behind and catching up) is no top speed; a longer one is."""
    t, x, y = _walk(3.0, 6)
    burst = (t >= 2000) & (t < 2600)
    x = x + np.cumsum(np.where(burst, 4.0 / 25, 0.0))  # +4 m/s for 600 ms
    assert physical(t, x, y).max_speed_ms < 4.5  # 7 m/s for 600 ms, smoothed
    t2, x2, y2 = _walk(3.0, 6)
    held = (t2 >= 2000) & (t2 < 3400)
    x2 = x2 + np.cumsum(np.where(held, 4.0 / 25, 0.0))
    assert physical(t2, x2, y2).max_speed_ms == pytest.approx(7.0, rel=0.1)


def test_merge_and_roundtrip() -> None:
    a = physical(*_walk(3.0, 10))
    b = physical(*_walk(6.0, 4, seed=1))
    m = merge([a, b])
    assert m.distance_m == pytest.approx(a.distance_m + b.distance_m)
    assert m.max_speed_ms == max(a.max_speed_ms, b.max_speed_ms)
    assert set(m.band_distance_m) == set(BANDS)
    assert from_dict(m.to_dict()).sprints == m.sprints
    assert physical(np.zeros(1), np.zeros(1), np.zeros(1)).distance_m == 0
    assert merge([]).distance_m == 0


def test_assign_numbers_constraints() -> None:
    spans = [
        TrackSpan(1, "home", 0, 60_000),
        TrackSpan(2, "home", 0, 60_000),
        TrackSpan(3, "home", 70_000, 90_000),  # fragment of player 1 after an occlusion
        TrackSpan(4, "away", 0, 60_000),
        TrackSpan(5, "home", 0, 10_000),  # too few readings
    ]
    readings = (
        [Reading(1, 7, 0.9)] * 6
        + [Reading(1, 1, 0.4)] * 2  # misread 7 as 1
        + [Reading(2, 7, 0.6)] * 2  # also looks like 7, but 1 is on court at the same time
        + [Reading(2, 11, 0.9)] * 5
        + [Reading(3, 7, 0.8)] * 4
        + [Reading(4, 7, 0.9)] * 5  # same number in the other team is fine
        + [Reading(5, 9, 0.9)] * 2
    )
    got = {a.track_id: a for a in assign_numbers(spans, readings)}
    assert got[1].number == 7 and got[1].votes == 6
    assert got[2].number == 11
    assert got[3].number == 7  # no time overlap with track 1
    assert got[4].number == 7
    assert 5 not in got
    assert 0 < got[2].confidence < 1

    roster = {7: "p7", 11: "p11"}
    team = {1: "home", 2: "home", 3: "home", 4: "away"}
    mapped = to_roster(list(got.values()), roster, team, "home")
    assert mapped == {
        1: ("p7", got[1].confidence),
        2: ("p11", got[2].confidence),
        3: ("p7", got[3].confidence),
    }


def test_conflicting_tracks_leave_one_unassigned() -> None:
    spans = [TrackSpan(1, "home", 0, 1000), TrackSpan(2, "home", 0, 1000)]
    readings = [Reading(1, 5, 0.9)] * 4 + [Reading(2, 5, 0.8)] * 4
    got = assign_numbers(spans, readings)
    assert [a.track_id for a in got] == [1] or [a.track_id for a in got] == [2]


def _impulses(
    seconds: float, times: list[float], sr: int = 8000, noise: float = 0.01, seed: int = 0
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = rng.normal(0, noise, int(seconds * sr)).astype(np.float32)
    for t in times:
        i = int(t * sr)
        x[i : i + 400] += np.sin(np.arange(400) * 0.6).astype(np.float32) * 0.8
    return x


def test_audio_offset() -> None:
    rng = np.random.default_rng(3)
    events = sorted(rng.uniform(1, 58, 40).tolist())
    main = _impulses(60, events)
    # the goal cam started 7.25 s later: an event at main time t is at t - 7.25 in the goal cam
    other = (
        _impulses(50, [t - 7.25 for t in events if t > 7.25], noise=0.03, seed=1) * 0.3
    ).astype(np.float32)
    res = estimate_offset(main, other)
    assert abs(res.offset_ms - (-7250)) <= 20
    assert res.confidence > 0.35
    # pure noise has no clear peak
    flat = estimate_offset(_impulses(30, [], seed=4), _impulses(30, [], seed=5))
    assert flat.confidence < 0.35
    assert estimate_offset(np.zeros(10, np.float32), np.zeros(10, np.float32)).confidence == 0
    assert len(onset_envelope(np.zeros(10, np.float32))) == 0


@pytest.mark.parametrize("seed", [11, 12])
def test_demo_footage_moves_like_a_match(seed: int) -> None:
    """The demo footage (scripts/seed.py, DEMO): field players cover about 70 to 110 m per
    minute with a few sprints and a top speed in the 20s km/h, as in real handball. The test
    default (a turnover with the whole team sprinting every 12 s) is far above that."""

    def per_minute(cfg: SyntheticConfig) -> tuple[float, float, float]:
        m = SyntheticMatch(cfg)
        dt = 1 / cfg.fps
        tracks: dict[int, list[tuple[float, float, float]]] = {}
        for i in range(int(cfg.seconds * cfg.fps)):
            m._step(i * dt, dt)
            for a in m.agents:
                if a.label in ("home", "away"):
                    tracks.setdefault(a.object_id, []).append((i * dt * 1000, *a.pos))
        ps = [physical(*np.array(v).T) for v in tracks.values()]
        minutes = cfg.seconds / 60
        dist = float(np.mean([p.distance_m for p in ps])) / minutes
        sprints = sum(p.sprints for p in ps) / len(ps) / minutes
        return dist, sprints, max(p.max_speed_ms for p in ps) * 3.6

    dist, sprints, top = per_minute(SyntheticConfig(seconds=300, seed=seed, **DEMO))
    assert 70 <= dist <= 110
    assert sprints <= 1.5
    assert 18 <= top <= 30
    test_dist, test_sprints, _ = per_minute(SyntheticConfig(seconds=300, seed=seed))
    assert test_dist > 150 and test_sprints > 3
