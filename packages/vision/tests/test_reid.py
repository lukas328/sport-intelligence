"""Re-identification: numbered fragments teach, unnumbered ones are recognised within the rules."""

from __future__ import annotations

import numpy as np

from handball_vision.reid import Fragment, assign, fit_projection

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
