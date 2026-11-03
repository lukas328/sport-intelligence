"""Live mark synchronisation (5.3): unit cases and a synthetic evaluation of the acceptance
criterion (within 2 s in 90 % of the cases after the sync)."""

from __future__ import annotations

import random

from handball_metrics.sync import REACTION_MS, estimate_offset

KICKOFF = 1_790_000_000_000  # device clock, epoch ms


def test_exact_and_fallbacks() -> None:
    offset = -KICKOFF + 120_000  # video started two minutes before the device's kickoff
    goals_video = [300_000, 900_000, 1_500_000, 2_400_000]
    taps = [g - offset + REACTION_MS for g in goals_video]
    r = estimate_offset(taps, goals_video, prior_offset_ms=offset + 45_000)
    assert r.source == "events" and r.offset_ms == offset and r.matched == 4
    # one goal: not enough to trust, the metadata prior is used
    r = estimate_offset(taps[:1], goals_video[:1], prior_offset_ms=offset + 45_000)
    assert r.source == "metadata" and r.offset_ms == offset + 45_000 and r.confidence == 0.3
    assert estimate_offset([], [], None).source == "none"
    # no metadata: the anchors alone
    r = estimate_offset(taps, goals_video, None)
    assert r.offset_ms == offset


def _trial(rng: random.Random) -> int | None:
    true = -KICKOFF + rng.randint(-600_000, 600_000)
    n_goals = rng.randint(30, 60)
    goals = sorted(rng.sample(range(60_000, 3_900_000, 1000), n_goals))
    taps = [g - true + rng.randint(500, 4000) for g in goals if rng.random() < 0.85]
    # detected goals (inferred from throw-offs): 70 % recall, 1.5 s noise, some false ones
    anchors = [g + rng.randint(-1500, 1500) for g in goals if rng.random() < 0.7]
    anchors += [rng.randint(60_000, 3_900_000) for _ in range(rng.randint(0, 5))]
    prior = None if rng.random() < 0.2 else true + rng.randint(-120_000, 120_000)
    r = estimate_offset(taps, anchors, prior)
    return None if r.offset_ms is None else abs(r.offset_ms - true)


def test_synthetic_acceptance() -> None:
    rng = random.Random(53)
    errors = [_trial(rng) for _ in range(200)]
    within = sum(1 for e in errors if e is not None and e <= 2000) / len(errors)
    assert within >= 0.9, within
