"""Event baseline from tracks (addendum 01, A3), on exact synthetic positions."""

from __future__ import annotations

from handball_vision.events import detect, score
from handball_vision.synthetic import DEMO, SyntheticConfig, SyntheticMatch


def _positions(
    cfg: SyntheticConfig,
) -> tuple[SyntheticMatch, list[tuple[int, int, float, float]], dict[int, str]]:
    m = SyntheticMatch(cfg)
    pts: list[tuple[int, int, float, float]] = []
    teams: dict[int, str] = {}
    dt = 1 / cfg.fps
    for i in range(int(cfg.seconds * cfg.fps)):
        t = i * dt
        m._step(t, dt)
        for a in m.agents:
            teams[a.object_id] = a.label
            pts.append((round(t * 1000), a.object_id, float(a.pos[0]), float(a.pos[1])))
    return m, pts, teams


def test_throw_offs_goals_possession_and_side_change() -> None:
    cfg = SyntheticConfig(seconds=200, restarts=True, side_change_s=100, phase_s=20)
    m, pts, teams = _positions(cfg)
    r = detect(pts, teams)
    truth = m.events()
    assert score(r.events, truth, "throw_off", 1500) == {
        "found": 7,
        "truth": 7,
        "precision": 1.0,
        "recall": 1.0,
    }
    goals = score(r.events, truth, "goal", 3000)
    assert goals["precision"] == 1.0 and goals["recall"] >= 0.8
    assert score(r.events, truth, "side_change", 20_000)["recall"] == 1.0
    pc = score(r.events, truth, "possession_change", 3000)
    assert pc["precision"] == 1.0 and pc["recall"] == 1.0
    assert [s for _, s in r.sides] == ["left", "right"]
    assert all(0 < e.confidence <= 1 for e in r.events)
    assert {p.outcome for p in r.possessions[:-1]} <= {"goal", "lost"}


def test_without_goalkeepers_nothing_is_guessed() -> None:
    cfg = SyntheticConfig(seconds=60, restarts=True, phase_s=20)
    _, pts, teams = _positions(cfg)
    no_gk = {k: v for k, v in teams.items() if not v.endswith("_gk")}
    r = detect([p for p in pts if p[1] in no_gk], no_gk)
    assert r.events == [] and r.missing == ["goalkeepers"]


def test_half_opening_throw_off_is_not_a_goal() -> None:
    cfg = SyntheticConfig(seconds=100, restarts=True, phase_s=20, goal_share=0.0, side_change_s=60)
    _, pts, teams = _positions(cfg)
    r = detect(pts, teams)
    assert [e.type for e in r.events if e.type == "goal"] == []
    assert len([e for e in r.events if e.type == "throw_off"]) == 2  # match start and second half


def test_tournament_video_boundary_suggestion() -> None:
    cfg = SyntheticConfig(seconds=60, restarts=True, phase_s=20)
    _, pts1, teams = _positions(cfg)
    _, pts2, _ = _positions(SyntheticConfig(seconds=60, restarts=True, phase_s=20, seed=9))
    shift = 180_000  # two minutes without players between the matches
    pts = pts1 + [(t + shift, tid, x, y) for t, tid, x, y in pts2]
    r = detect(pts, teams)
    boundaries = [e for e in r.events if e.type == "match_boundary"]
    assert len(boundaries) == 1
    assert 60_000 <= boundaries[0].t_ms <= shift + 1000
    assert [e for e in r.events if e.type == "pause"]
    assert not [e for e in r.events if e.type == "goal" and 60_000 < e.t_ms < shift]


def test_formation_corrects_uncertain_team_labels() -> None:
    from handball_vision.events import refine_teams

    cfg = SyntheticConfig(seconds=120, restarts=True, phase_s=20, goal_share=1.0)
    _, pts, teams = _positions(cfg)
    wrong = {k: ("away" if v == "home" else "home" if v == "away" else v) for k, v in teams.items()}
    # half of the field players got the wrong colour label with low confidence
    flipped = [k for k, v in teams.items() if v in ("home", "away")][::2]
    labels = {k: (wrong[k] if k in flipped else v) for k, v in teams.items()}
    conf = {k: (0.3 if k in flipped else 0.95) for k in teams}
    fixed = refine_teams(pts, labels, conf)
    assert all(fixed[k] == teams[k] for k in teams)
    # confident labels are never overridden
    assert refine_teams(pts, labels, {k: 0.99 for k in teams}) == labels


def test_fast_breaks_follow_lost_balls_not_throw_offs() -> None:
    """A counter after a lost ball is a fast break; an attack opened by the team's own throw-off
    (after a goal) is not, although the team runs up from the centre line just as fast."""
    cfg = SyntheticConfig(seconds=300, restarts=True, phase_s=20, goal_share=0.5)
    m, pts, teams = _positions(cfg)
    r = detect(pts, teams)
    throw_offs = [e.t_ms for e in r.events if e.type == "throw_off"]
    assert len(throw_offs) >= 4
    for p in r.possessions:
        phase = round(p.start_ms / 1000 / cfg.phase_s - 0.25)  # starts a few seconds into a phase
        after_lost = phase > 0 and m.outcomes[phase - 1] == "lost"
        if m.restart(phase):
            assert p.phase is None, p
        elif after_lost:
            assert p.phase == "fast_break", p
    assert any(p.phase == "fast_break" for p in r.possessions)


def test_demo_flow_has_few_fast_breaks() -> None:
    """The flow of the demo footage (scripts/seed.py): goals with throw-offs, longer attacks;
    only counters after a lost ball are fast breaks."""
    cfg = SyntheticConfig(seconds=300, **DEMO)
    m, pts, teams = _positions(cfg)
    r = detect(pts, teams)
    fast = [p for p in r.possessions if p.phase == "fast_break"]
    lost = sum(o == "lost" for o in m.outcomes[: int(cfg.seconds // cfg.phase_s)])
    assert len(fast) <= lost < len(r.possessions)


def test_side_hint_holds_without_goalkeepers() -> None:
    """A second half in a file of its own (Q-VIDEO-PARTS): the API knows the home team defends
    the other side than at the end of the first half. Without goalkeepers in view the hint holds
    instead of nothing being found."""
    cfg = SyntheticConfig(seconds=60, restarts=True, phase_s=20)
    _, pts, teams = _positions(cfg)
    no_gk = {k: v for k, v in teams.items() if not v.endswith("_gk")}
    r = detect([p for p in pts if p[1] in no_gk], no_gk, side_hint="left")
    assert [s for _, s in r.sides] == ["left"]
    assert r.missing != ["goalkeepers"]
    assert any(e.type == "throw_off" for e in r.events)


def test_clear_goalkeepers_win_over_the_side_hint() -> None:
    cfg = SyntheticConfig(seconds=60, restarts=True, phase_s=20)
    _, pts, teams = _positions(cfg)
    assert [s for _, s in detect(pts, teams).sides] == ["left"]
    # a wrong hint (the order of the files was wrong) does not overrule what the keepers show
    assert [s for _, s in detect(pts, teams, side_hint="right").sides] == ["left"]
    assert [s for _, s in detect(pts, teams, side_hint="nonsense").sides] == ["left"]
