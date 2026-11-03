"""Automatic preparation report (addendum 01, 4.6)."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from handball_api.core.email import MemoryEmailSender

from .conftest import Api, setup_club
from .test_matches import new_match

pytestmark = pytest.mark.usefixtures("clean_db")


async def _earlier_match(api: Api, ids: dict[str, str], kickoff: str) -> str:
    m = await new_match(api, ids, opponent_name="TV Gegner", kickoff_at=kickoff)
    ev = f"/v1/orgs/{ids['org']}/matches/{m['id']}/events"
    shots = [
        (7, "goal", (31, 14), "TL", None),
        (7, "goal", (31, 14), "TL", None),
        (7, "goal", (31, 14), "BR", None),
        (7, "miss", (31, 14), None, None),
        (11, "goal", (39, 1), "TR", "fast_break"),
        (11, "goal", (39, 1), "BL", "fast_break"),
        (4, "save", (30, 10), None, None),
    ]
    for i, (num, outcome, zone, gz, st) in enumerate(shots):
        body = {
            "type": "shot",
            "side": "opponent",
            "outcome": outcome,
            "number": num,
            "clock_s": 100 * (i + 1),
            "t_ms": 100_000 * (i + 1),
            "x": zone[0],
            "y": zone[1],
            "goal_zone": gz,
            "shot_type": st,
        }
        r = await api.post(ev, json={k: v for k, v in body.items() if v is not None})
        assert r.status_code == 201, r.text
    await api.post(ev, json={"type": "suspension_2min", "side": "own", "clock_s": 650})
    for i in range(5):
        await api.post(
            ev,
            json={
                "type": "shot",
                "side": "own",
                "outcome": "goal" if i < 4 else "miss",
                "clock_s": 900 + i * 10,
                "x": 39.0,
                "y": 2.0,
            },
        )
    await api.patch(
        f"/v1/orgs/{ids['org']}/matches/{m['id']}", json={"score_own": 25, "score_opponent": 27}
    )
    return str(m["id"])


async def test_report_facts_pdfs_and_access(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    org = ids["org"]
    await _earlier_match(coach, ids, "2026-09-05T18:00:00+02:00")
    await _earlier_match(coach, ids, "2026-10-05T18:00:00+02:00")
    upcoming = await new_match(
        coach, ids, opponent_name="TV Gegner", kickoff_at="2026-12-05T18:00:00+01:00"
    )
    url = f"/v1/orgs/{org}/matches/{upcoming['id']}/scouting"
    assert (await coach.get(url)).status_code == 404
    r = await coach.post(url)
    assert r.status_code == 201, r.text
    rep = r.json()
    f = rep["facts"]
    assert rep["basis"]["matches"] == 2 and rep["basis"]["tagged_matches"] == 2
    assert f["glance"]["record"] == {"won": 0, "drawn": 0, "lost": 2}
    assert f["glance"]["n"] == 14
    top = f["shooters"][0]
    assert (top["number"], top["goals"], top["shots"], top["main_zone"]) == (7, 6, 8, "half_left")
    assert top["goal_zones"]["TL"] == 4
    assert f["fast_break"]["goals"] == 4 and f["fast_break"]["share"] == 0.4
    assert f["numbers"]["they_in_powerplay"]["periods"] == 2
    assert f["plays"] == {"available": False, "reason": "play_detection"}
    assert "play_detection" in f["missing"] and "video" in f["missing"]
    keys = {o["key"] for o in f["observations"]}
    assert {"top_shooter", "fast_break"} <= keys
    assert all(o["n"] >= 5 for o in f["observations"])  # sample size on every observation
    assert (await coach.get(url)).json()["id"] == rep["id"]

    pdf = await coach.get(f"/v1/orgs/{org}/scouting/{rep['id']}/pdf", params={"lang": "fr"})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    card = await coach.get(f"/v1/orgs/{org}/scouting/{rep['id']}/goalkeeper-card")
    assert card.content.startswith(b"%PDF")

    # goalkeepers get the shooter card, not the full report; field players get neither
    async def member(role: str) -> Api:
        await coach.post(
            f"/v1/orgs/{org}/invitations",
            json={"email": f"{role}@hc-test.ch", "team_id": ids["team"], "team_role": role},
        )
        token = re.search(r"/invite/([\w-]+)", outbox.outbox[-1].text)
        assert token
        api = make_api()
        await api.register(f"{role}@hc-test.ch", invitation_token=token.group(1))
        return api

    gk = await member("goalkeeper")
    assert (await gk.get(f"/v1/orgs/{org}/scouting/{rep['id']}/goalkeeper-card")).status_code == 200
    assert (await gk.get(f"/v1/orgs/{org}/scouting/{rep['id']}/pdf")).status_code == 403
    player = await member("player")
    assert (
        await player.get(f"/v1/orgs/{org}/scouting/{rep['id']}/goalkeeper-card")
    ).status_code == 403
    assert (await player.get(url)).status_code in (403, 404)


async def test_reports_are_created_72h_before(make_api: Callable[[], Api]) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    org = ids["org"]
    await _earlier_match(coach, ids, "2026-09-05T18:00:00+02:00")
    soon = (datetime.now(UTC) + timedelta(hours=48)).isoformat()
    later = (datetime.now(UTC) + timedelta(days=10)).isoformat()
    due = await new_match(coach, ids, opponent_name="TV Gegner", kickoff_at=soon)
    await new_match(coach, ids, opponent_name="TV Gegner", kickoff_at=later)
    await new_match(coach, ids, opponent_name="Unbekannt", kickoff_at=soon)  # no data: no report
    token = {"x-internal-token": coach.app.state.settings.internal_token.get_secret_value()}
    assert (await coach.post("/internal/scouting/due")).status_code == 403
    r = await coach.post("/internal/scouting/due", headers=token)
    assert r.json() == {"created": 1}
    assert (await coach.post("/internal/scouting/due", headers=token)).json() == {"created": 0}
    assert (await coach.get(f"/v1/orgs/{org}/matches/{due['id']}/scouting")).status_code == 200
    notes = (await coach.get(f"/v1/orgs/{org}/me/notifications")).json()
    assert any(n["kind"] == "scouting_ready" for n in notes["items"])
