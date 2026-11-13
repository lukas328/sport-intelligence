"""Names from the official data in event and statistics views (backlog: onboarding gap).

The roster list shows entries taken over from the official data only to the team's organisers
until the person joins or consents (`services/roster.py`); the names an official report gives
own players follow the same rule in the event list, the goal comparison and the PDF report."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.email import MemoryEmailSender
from handball_api.services import report_pdf

from .conftest import Api
from .test_official import base, claim, coach, hch, invite, suggestions

pytestmark = pytest.mark.usefixtures("clean_db", "hch")
__all__ = ["hch"]  # the recorded handball.ch answers (autouse in test_official)


async def test_official_names_in_events_and_stats_follow_the_roster_rule(
    make_api: Callable[[], Api], outbox: MemoryEmailSender, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The names an official report gives own players reach the team (events, the goal
    comparison, the PDF report) only as the roster list shows them: organisers always, the other
    members once the person joined or consented (backlog: onboarding gap)."""
    api = await coach(make_api)
    c = await claim(api)
    roster = {s["payload"]["first_name"]: s for s in await suggestions(api, c, "roster_add")}
    ids = {}
    for name in ("Luca", "Noah", "Simon"):
        r = await api.post(base(c) + f"/official/suggestions/{roster[name]['id']}/accept")
        assert r.status_code == 200, r.text
        ids[name] = r.json()["player_id"]
    report = next(
        s for s in await suggestions(api, c, "report") if s["payload"]["game_id"] == 509192
    )
    r = await api.post(base(c) + f"/official/suggestions/{report['id']}/accept")
    assert r.status_code == 200, r.text
    match = f"/v1/orgs/{c['organization_id']}/matches/{r.json()['match_id']}"
    player = await invite(api, make_api, outbox, c, "player")
    pdf_names: list[dict[str, str]] = []

    def render(*args: Any) -> bytes:
        pdf_names.append(args[5])
        return b"%PDF-1.4"

    monkeypatch.setattr(report_pdf, "render", render)

    async def seen(who: Api) -> tuple[set[str], set[str], set[str]]:
        events = (await who.get(match + "/events")).json()
        named = {e["player_id"] for e in events if e["side"] == "own" and "name" in e["attributes"]}
        goals = (await who.get(match + "/official-report/comparison")).json()["goals"]
        compared = {g["player_id"] for g in goals if g["side"] == "own" and g["name"]}
        assert (await who.get(match + "/report.pdf")).status_code == 200
        return named, compared, set(pdf_names[-1])

    # the coach organises the team: every name
    named, compared, pdf = await seen(api)
    scorers = {ids[n] for n in ids} & named
    assert scorers and scorers <= compared and scorers <= pdf
    # a player sees none of the official-only entries, in no view
    named, compared, pdf = await seen(player)
    assert not named and not compared and not pdf & set(ids.values())
    # a consent makes that person's name visible, the others stay hidden
    luca_or_other = next(n for n in ids if ids[n] in scorers)
    r = await api.post(
        base(c) + f"/players/{ids[luca_or_other]}/consents",
        json={
            "kind": "analysis",
            "given_by": "self",
            "given_by_name": "Volljährig",
            "given_at": "2026-11-01T10:00:00+01:00",
        },
    )
    assert r.status_code == 201, r.text
    named, compared, pdf = await seen(player)
    assert named == compared == {ids[luca_or_other]}
    assert pdf & set(ids.values()) == {ids[luca_or_other]}


def test_a_game_names_its_league_not_the_group_code() -> None:
    """UX test N25/A04: «Männer 1. Liga», never «Hauptrunde - M1-01»; a cup keeps its name."""
    from handball_api.integrations.handball_ch import _game

    base = {"objectId": 1, "gameDateTime": "2026-10-10T18:00:00", "gameStatusId": 0}
    g = _game({**base, "groupName": "Hauptrunde - M1-01", "leagueShortName": "Männer 1. Liga"})
    assert g.competition == "Männer 1. Liga"
    assert _game({**base, "groupName": "Schweizer Cup"}).competition == "Schweizer Cup"
