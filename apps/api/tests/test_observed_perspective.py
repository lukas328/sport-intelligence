"""The perspective of a match (app review 19.11., BUG-01 to 07, L4): an observed match (kind
scouting) is neutral. The team of the account does not play, so none of its players can be
named in it; both teams go by shirt number. A match of the team keeps its roster."""

from __future__ import annotations

import uuid
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
    # not a game of the federation's schedule: no «the official report comes» (TXT-06)
    read = (await coach.get(f"/v1/orgs/{org}/matches/{observed['id']}")).json()
    assert read["official_game"] is False
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

    # Szenen (UX-07, BUG-12): the observed match's scenes are found, marked and filterable
    search = f"/v1/orgs/{org}/teams/{ids['team']}/search"
    hits = (await coach.post(search, json={})).json()["hits"]
    assert {h["observed"] for h in hits} == {True, False}
    labels = {h["match_label"] for h in hits if h["observed"]}
    assert labels == {"TV Dritte - HC Beobachtet"}  # home team first, no team of ours
    only = (await coach.post(search, json={"observed": True})).json()["hits"]
    assert only and all(h["observed"] for h in only)
    own = (await coach.post(search, json={"observed": False})).json()["hits"]
    assert own and not any(h["observed"] for h in own)


async def test_observed_match_home_team_from_the_form(make_api: Callable[[], Api]) -> None:
    """The form asks who plays at home (UI check 20.11.): the observed opponent at home is
    `is_home` false (the data's own side is the other team) and every pairing follows it. Without
    the answer the other team stays home, as for the observed matches made before."""
    coach = make_api()
    ids = await setup_club(coach)
    org = ids["org"]
    away = await new_match(
        coach,
        ids,
        kind="scouting",
        opponent_name="HC Beobachtet",
        scouting_other="TV Dritte",
        is_home=False,
    )
    before = await new_match(
        coach, ids, kind="scouting", opponent_name="HC Beobachtet", scouting_other="TV Vierte"
    )
    assert away["is_home"] is False and before["is_home"] is True
    shot = {"type": "shot", "side": "opponent", "outcome": "goal", "clock_s": 60, "number": 5}
    for m in (away, before):
        r = await coach.post(f"/v1/orgs/{org}/matches/{m['id']}/events", json=shot)
        assert r.status_code == 201, r.text
    hits = (
        await coach.post(f"/v1/orgs/{org}/teams/{ids['team']}/search", json={"observed": True})
    ).json()["hits"]
    assert {h["match_label"] for h in hits} == {
        "HC Beobachtet - TV Dritte",
        "TV Vierte - HC Beobachtet",
    }
    # the answer can be changed afterwards
    r = await coach.patch(f"/v1/orgs/{org}/matches/{away['id']}", json={"is_home": True})
    assert r.status_code == 200, r.text
    assert r.json()["is_home"] is True


async def test_goalkeeper_id_is_a_keeper_of_the_match(make_api: Callable[[], Api]) -> None:
    """`goalkeeper_id` names our goalkeeper behind the opponent's shots: a player of the team's
    roster, never an invented id, never in an observed match (UI check 20.11.)."""
    coach = make_api()
    ids = await setup_club(coach)
    org = ids["org"]
    keeper = (
        await coach.post(
            roster_url(ids), json={"first_name": "Nora", "last_name": "Halt", "jersey_number": 1}
        )
    ).json()["player_id"]
    ours = await new_match(coach, ids)
    observed = await new_match(
        coach, ids, kind="scouting", opponent_name="HC Beobachtet", scouting_other="TV Dritte"
    )
    save = {"type": "shot", "side": "opponent", "outcome": "save", "clock_s": 60}
    url = f"/v1/orgs/{org}/matches/{ours['id']}/events"

    r = await coach.post(url, json={**save, "attributes": {"goalkeeper_id": keeper}})
    assert r.status_code == 201, r.text
    ev = r.json()["id"]
    for bad in (str(uuid.uuid4()), "nobody", 7):
        r = await coach.post(url, json={**save, "attributes": {"goalkeeper_id": bad}})
        assert r.status_code == 422, (bad, r.text)
    # our keeper does not stand behind our own shots
    r = await coach.post(url, json={**save, "side": "own", "attributes": {"goalkeeper_id": keeper}})
    assert r.status_code == 422, r.text
    # an edit cannot move the save to the other side (attributes are not editable)
    r = await coach.patch(f"/v1/orgs/{org}/events/{ev}", json={"side": "own"})
    assert r.status_code == 422, r.text
    # an observed match: our keeper does not play, the keeper goes by number
    r = await coach.post(
        f"/v1/orgs/{org}/matches/{observed['id']}/events",
        json={**save, "attributes": {"goalkeeper_id": keeper}},
    )
    assert r.status_code == 422, r.text
    r = await coach.post(
        f"/v1/orgs/{org}/matches/{observed['id']}/events",
        json={**save, "attributes": {"goalkeeper_number": 12}},
    )
    assert r.status_code == 201, r.text
