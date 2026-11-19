"""The perspective of a match (app review 19.11., BUG-01 to 07, L4): an observed match (kind
scouting) is neutral. The team of the account does not play, so none of its players can be
named in it; both teams go by shirt number. A match of the team keeps its roster."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from handball_api.models import Match

from .conftest import Api, setup_club
from .test_matches import new_match
from .test_roster import roster_url

pytestmark = pytest.mark.usefixtures("clean_db")


def test_observed_is_the_scouting_kind() -> None:
    assert Match(kind="scouting").observed is True
    assert Match(kind="match").observed is False
    assert Match(kind="training").observed is False


async def test_observed_match_takes_shirt_numbers_not_our_players(
    make_api: Callable[[], Api],
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    org = ids["org"]
    lena = (
        await coach.post(
            roster_url(ids), json={"first_name": "Lena", "last_name": "Muster", "jersey_number": 9}
        )
    ).json()["player_id"]
    observed = await new_match(
        coach,
        ids,
        kind="scouting",
        opponent_name="HC Beobachtet",
        scouting_other="TV Dritte",
    )
    ours = await new_match(coach, ids, opponent_name="HC Beobachtet")
    shot = {"type": "shot", "side": "own", "outcome": "goal", "clock_s": 60}

    # our player cannot score in a match our team does not play
    r = await coach.post(
        f"/v1/orgs/{org}/matches/{observed['id']}/events", json={**shot, "player_id": lena}
    )
    assert r.status_code == 422, r.text
    # either team by its shirt number
    for side in ("own", "opponent"):
        r = await coach.post(
            f"/v1/orgs/{org}/matches/{observed['id']}/events",
            json={**shot, "side": side, "number": 7},
        )
        assert r.status_code == 201, r.text
        assert r.json()["number"] == 7 and r.json()["player_id"] is None
    # an edit cannot bring our player in either
    ev = r.json()["id"]
    r = await coach.patch(f"/v1/orgs/{org}/events/{ev}", json={"player_id": lena})
    assert r.status_code == 422, r.text

    # a match of the team keeps its roster
    r = await coach.post(
        f"/v1/orgs/{org}/matches/{ours['id']}/events", json={**shot, "player_id": lena}
    )
    assert r.status_code == 201, r.text
