"""Re-identification: numbered fragments teach, unnumbered ones are recognised within the rules."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from handball_vision.reid import (
    Fragment,
    anchor_vectors,
    assign,
    contradicts,
    fit_projection,
    fragment_roles,
    plays,
)

FPS = 30.0


def _player_vectors(rng: np.random.Generator, centre: np.ndarray, n: int) -> np.ndarray:
    v = centre + 0.35 * rng.standard_normal((n, centre.size))
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def _setup() -> tuple[np.random.Generator, dict[int, np.ndarray]]:
    rng = np.random.default_rng(0)
    shared = rng.standard_normal(64)  # same shirt: a large common part
    players = {n: shared + 0.6 * rng.standard_normal(64) for n in (4, 7, 11)}
    return rng, players


def _frag(
    tid: int,
    number: int | None,
    first: int,
    last: int,
    vecs: np.ndarray,
    xy: tuple[float, float] = (10.0, 10.0),
) -> Fragment:
    return Fragment(tid, "home", first, last, xy, xy, vecs, number)


def test_projection_separates_teammates() -> None:
    rng, players = _setup()
    proj = fit_projection({n: _player_vectors(rng, c, 30) for n, c in players.items()})
    assert proj is not None
    a = proj(_player_vectors(rng, players[4], 10)).mean(axis=0)
    b = proj(_player_vectors(rng, players[7], 10)).mean(axis=0)
    a2 = proj(_player_vectors(rng, players[4], 10)).mean(axis=0)
    assert np.linalg.norm(a - a2) < 0.5 * np.linalg.norm(a - b)


def test_unnumbered_fragments_find_their_player() -> None:
    rng, players = _setup()
    frags = [
        _frag(1, 4, 0, 300, _player_vectors(rng, players[4], 20)),
        _frag(2, 7, 0, 300, _player_vectors(rng, players[7], 20)),
        _frag(3, 11, 0, 300, _player_vectors(rng, players[11], 20)),
        _frag(10, None, 400, 600, _player_vectors(rng, players[7], 8)),
        _frag(11, None, 400, 600, _player_vectors(rng, players[11], 8)),
    ]
    assert assign(frags, FPS) == {10: 7, 11: 11}


def test_a_player_cannot_be_on_court_twice_or_teleport() -> None:
    rng, players = _setup()
    base = [
        _frag(1, 4, 0, 300, _player_vectors(rng, players[4], 20)),
        _frag(2, 7, 0, 300, _player_vectors(rng, players[7], 20)),
        _frag(3, 11, 0, 300, _player_vectors(rng, players[11], 20)),
    ]
    # looks like #7 but overlaps #7's numbered fragment in time: not #7
    same_time = _frag(10, None, 100, 250, _player_vectors(rng, players[7], 8))
    assert assign([*base, same_time], FPS).get(10) != 7
    # looks like #7, 0.1 s after #7's fragment ended but 30 m away: not #7 either
    far = _frag(11, None, 303, 500, _player_vectors(rng, players[7], 8), xy=(40.0, 10.0))
    assert assign([*base, far], FPS).get(11) != 7


def _mixed_anchor(
    rng: np.random.Generator, players: dict[int, np.ndarray], framed: bool
) -> list[Fragment]:
    """#7's track carries #11 for most of its length (the tracker swapped them in a crowd); the
    number was read only while #7 was in the box (frames 0 to 90)."""
    own = _player_vectors(rng, players[7], 8)
    other = _player_vectors(rng, players[11], 24)
    frames = np.concatenate([np.arange(0, 96, 12), np.arange(200, 680, 20)]).astype(np.int64)
    mixed = Fragment(
        2,
        "home",
        0,
        680,
        (10.0, 10.0),
        (10.0, 10.0),
        np.vstack([own, other]),
        7,
        frames if framed else None,
        tuple((f, 7) for f in range(0, 91, 15)) if framed else (),
    )
    return [
        _frag(1, 4, 0, 680, _player_vectors(rng, players[4], 20)),
        mixed,
        _frag(3, 11, 700, 900, _player_vectors(rng, players[11], 20)),
    ]


def test_anchor_vectors_are_the_read_stretches() -> None:
    rng, players = _setup()
    mixed = _mixed_anchor(rng, players, framed=True)[1]
    assert len(anchor_vectors(mixed, FPS)) == 8  # within 2 s of a reading: #7's own vectors
    plain = _mixed_anchor(rng, players, framed=False)[1]
    assert len(anchor_vectors(plain, FPS)) == 32  # no frames: everything, as before


def test_a_mixed_anchor_teaches_only_its_read_stretch() -> None:
    rng, players = _setup()
    # a later piece of #11: with the whole mixed track teaching, #7 looks like #11 as well and
    # the ratio test gives up; with the read stretches only, #11 is clearly nearest
    probe = _player_vectors(rng, players[11], 8)
    got = {}
    for framed in (True, False):
        base = _mixed_anchor(np.random.default_rng(1), players, framed)
        got[framed] = assign([*base, _frag(10, None, 950, 1100, probe)], FPS).get(10)
    assert got == {True: 11, False: None}


def test_own_readings_veto_another_number() -> None:
    rng, players = _setup()
    base = [
        _frag(1, 4, 0, 300, _player_vectors(rng, players[4], 20)),
        _frag(2, 7, 0, 300, _player_vectors(rng, players[7], 20)),
        _frag(3, 11, 0, 300, _player_vectors(rng, players[11], 20)),
    ]
    looks_like_7 = _player_vectors(rng, players[7], 8)
    read_33 = Fragment(
        10,
        "home",
        400,
        600,
        (10.0, 10.0),
        (10.0, 10.0),
        looks_like_7,
        None,
        None,
        ((420, 33), (450, 33)),
    )
    assert contradicts(read_33, 7) and not contradicts(read_33, 33)
    read_1 = replace(read_33, readings=((420, 1), (450, 1)))
    assert not contradicts(read_1, 7)  # 1 <-> 7 is a known misreading
    assert assign([*base, read_33], FPS).get(10) is None
    assert assign([*base, read_1], FPS).get(10) == 7


PLAYER, REFEREE, KEEPER = (0.95, 0.03, 0.02), (0.1, 0.0, 0.9), (0.2, 0.75, 0.05)


def test_role_of_a_fragment_from_the_looks_next_to_its_readings() -> None:
    looks = [(f, np.array(PLAYER)) for f in (0, 30, 60)] + [
        (f, np.array(REFEREE)) for f in (300, 330, 360)
    ]
    whole = fragment_roles(looks, (), None, FPS)
    assert whole is not None and abs(whole[0] - 0.525) < 1e-9
    read = fragment_roles(looks, ((30, 7), (45, 7), (330, 9)), 7, FPS)
    assert read is not None and abs(read[0] - 0.95) < 1e-9  # where #7 was read: a player
    assert fragment_roles(looks[:1], (), None, FPS) is None  # one look is not enough
    assert fragment_roles([], (), None, FPS) is None
    vecs = np.zeros((3, 4))
    assert plays(Fragment(1, "home", 0, 1, (0, 0), (0, 0), vecs, role_p=PLAYER))
    assert plays(Fragment(1, "home", 0, 1, (0, 0), (0, 0), vecs))  # no role model: the label
    assert not plays(Fragment(1, "home", 0, 1, (0, 0), (0, 0), vecs, role_p=REFEREE))
    assert not plays(Fragment(1, "away", 0, 1, (0, 0), (0, 0), vecs, role_p=KEEPER))
    assert not plays(Fragment(1, "away_gk", 0, 1, (0, 0), (0, 0), vecs, role_p=PLAYER))


def test_referees_and_goalkeepers_neither_teach_nor_get_numbers() -> None:
    rng, players = _setup()
    base = [
        _frag(1, 4, 0, 300, _player_vectors(rng, players[4], 20)),
        _frag(2, 7, 0, 300, _player_vectors(rng, players[7], 20)),
        _frag(3, 11, 0, 300, _player_vectors(rng, players[11], 20)),
    ]
    # a referee track in the home colour read as 9 (a dirty anchor) and a later piece of it
    ref = rng.standard_normal(64)
    dirty = _frag(4, 9, 0, 300, _player_vectors(rng, ref, 20))
    later = _frag(10, None, 400, 600, _player_vectors(rng, ref, 8))
    assert assign([*base, dirty, later], FPS) == {10: 9}  # the label alone lets it teach
    # with its role it does not teach, so #9 is never given out
    assert assign([*base, replace(dirty, role_p=REFEREE), later], FPS) == {}
    # and a piece that looks like #7 but like a referee to the role classifier (a referee or
    # staff member in a similar shirt) gets no player's number
    like_7 = _frag(10, None, 400, 600, _player_vectors(rng, players[7], 8))
    assert assign([*base, like_7], FPS) == {10: 7}
    assert assign([*base, replace(like_7, role_p=REFEREE)], FPS) == {}
    keeper = replace(_frag(11, None, 400, 600, _player_vectors(rng, players[7], 8)), team="home_gk")
    assert assign([*base, keeper], FPS) == {}
