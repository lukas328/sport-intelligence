"""Linking accounts to roster players: invitations, join requests and the staff endpoint."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from handball_api.core.email import MemoryEmailSender

from .conftest import Api, setup_club
from .test_invitations import token_from

pytestmark = pytest.mark.usefixtures("clean_db")


def roster_url(ids: dict[str, Any]) -> str:
    return f"/v1/orgs/{ids['org']}/teams/{ids['team']}/seasons/{ids['season']}/roster"


async def add_player(coach: Api, ids: dict[str, Any], first: str, last: str, n: int) -> str:
    r = await coach.post(
        roster_url(ids), json={"first_name": first, "last_name": last, "jersey_number": n}
    )
    assert r.status_code == 201, r.text
    return str(r.json()["player_id"])


async def invite(coach: Api, ids: dict[str, Any], email: str, **extra: Any) -> Any:
    return await coach.post(
        f"/v1/orgs/{ids['org']}/invitations",
        json={"email": email, "team_id": ids["team"], "team_role": "player", **extra},
    )


async def join(
    make_api: Callable[[], Api], outbox: MemoryEmailSender, email: str, name: str = "Test User"
) -> Api:
    token = token_from(outbox)
    api = make_api()
    assert (await api.register(email, name=name, invitation_token=token)).status_code == 201
    return api


async def test_invited_player_is_linked_and_sees_their_dates(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    org, team = ids["org"], ids["team"]
    mira = await add_player(coach, ids, "Mira", "Tobler", 7)
    r = await invite(coach, ids, "mira@hc-test.ch", player_id=mira)
    assert r.status_code == 201 and r.json()["player_id"] == mira
    soon = (datetime.now(UTC) + timedelta(days=2)).date().isoformat()
    s = (await coach.post(f"/v1/orgs/{org}/teams/{team}/sessions", json={"on_date": soon})).json()

    player = await join(make_api, outbox, "mira@hc-test.ch")
    schedule = (await player.get(f"/v1/orgs/{org}/me/schedule")).json()
    assert [(i["kind"], i["id"], i["player_id"], i["relation"]) for i in schedule] == [
        ("session", s["id"], mira, "self")
    ]
    r = await player.put(
        f"/v1/orgs/{org}/me/attendance",
        json={"kind": "session", "id": s["id"], "player_id": mira, "response": "yes"},
    )
    assert r.status_code == 200, r.text
    roster = (await coach.get(roster_url(ids))).json()
    assert roster[0]["account_user_id"] == player.user["id"]
    # other team members see that the entry has an account, not whose
    assert (await player.get(roster_url(ids))).json()[0]["account_user_id"] is None


async def test_invitation_by_name_and_number(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    noe = await add_player(coach, ids, "Noé", "Gisler", 4)
    await add_player(coach, ids, "Ivo", "Gisler", 5)
    # the last name alone fits two entries: no entry, the coach links later
    r = await invite(coach, ids, "g@hc-test.ch", last_name="Gisler")
    assert r.status_code == 201 and r.json()["player_id"] is None
    # name without accents and the number: exactly one
    r = await invite(coach, ids, "noe@hc-test.ch", first_name="noe", last_name="gisler")
    assert r.json()["player_id"] == noe
    r = await invite(coach, ids, "nr4@hc-test.ch", jersey_number=4)
    assert r.json()["player_id"] == noe
    # a hint that matches nothing leaves the invitation without an entry
    r = await invite(coach, ids, "x@hc-test.ch", last_name="Gisler", jersey_number=9)
    assert r.json()["player_id"] is None
    assert (
        await coach.post(
            f"/v1/orgs/{ids['org']}/invitations",
            json={"email": "a@hc-test.ch", "org_role": "org_admin", "last_name": "Gisler"},
        )
    ).status_code == 422


async def test_onboarding_invitation_links_by_account_name(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    sina = await add_player(coach, ids, "Sina", "Kälin", 11)
    await add_player(coach, ids, "Lou", "Arnold", 12)
    await add_player(coach, ids, "Lou", "Arnold", 13)
    await invite(coach, ids, "sina@hc-test.ch")
    player = await join(make_api, outbox, "sina@hc-test.ch", name="Sina Kaelin")
    # "Kaelin" is not "Kälin" folded: no guess
    assert not any(e["has_account"] for e in (await coach.get(roster_url(ids))).json())
    await invite(coach, ids, "sina2@hc-test.ch")
    player = await join(make_api, outbox, "sina2@hc-test.ch", name="kälin  sina")
    entries = {e["player_id"]: e for e in (await coach.get(roster_url(ids))).json()}
    assert entries[sina]["account_user_id"] == player.user["id"]
    # two entries with the same name: nothing linked
    await invite(coach, ids, "lou@hc-test.ch")
    await join(make_api, outbox, "lou@hc-test.ch", name="Lou Arnold")
    assert sum(e["has_account"] for e in (await coach.get(roster_url(ids))).json()) == 1


async def test_invitation_never_takes_a_linked_entry(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    timo = await add_player(coach, ids, "Timo", "Frei", 8)
    await invite(coach, ids, "timo@hc-test.ch", player_id=timo)
    first_token = token_from(outbox)
    await invite(coach, ids, "fake@hc-test.ch", player_id=timo)
    second_token = token_from(outbox)
    owner = make_api()
    assert (
        await owner.register("timo@hc-test.ch", invitation_token=first_token)
    ).status_code == 201
    # the entry now has an account: a second invitation cannot take it
    other = make_api()
    await other.register("fake@hc-test.ch")
    r = await other.post(f"/v1/invitations/{second_token}/accept")
    assert r.status_code == 409 and r.json()["type"].endswith(":player-linked")
    assert (await other.get(f"/v1/invitations/{second_token}")).json()["status"] == "pending"
    assert (await other.get(f"/v1/orgs/{ids['org']}")).status_code in (403, 404)
    r = await invite(coach, ids, "third@hc-test.ch", player_id=timo)
    assert r.status_code == 409
    # inviting the same person again for their own entry is fine
    assert (await invite(coach, ids, "timo@hc-test.ch", player_id=timo)).status_code == 201
    entry = (await coach.get(roster_url(ids))).json()[0]
    assert entry["account_user_id"] == owner.user["id"]


async def test_staff_link_and_unlink(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    org, team = ids["org"], ids["team"]
    ana = await add_player(coach, ids, "Ana", "Wyss", 3)
    ben = await add_player(coach, ids, "Ben", "Wyss", 6)
    await invite(coach, ids, "ana@hc-test.ch")
    player = await join(make_api, outbox, "ana@hc-test.ch")
    await coach.post(
        f"/v1/orgs/{org}/invitations",
        json={"email": "mum@hc-test.ch", "team_id": team, "team_role": "parent", "player_id": ben},
    )
    parent = await join(make_api, outbox, "mum@hc-test.ch")
    url = f"/v1/orgs/{org}/teams/{team}/players/{ana}/account"

    # players cannot link themselves
    assert (await player.put(url, json={"user_id": player.user["id"]})).status_code == 403
    r = await coach.put(url, json={"user_id": player.user["id"]})
    assert r.status_code == 200, r.text
    assert r.json() == {"player_id": ana, "user_id": player.user["id"], "name": "Test User"}
    assert (await coach.put(url, json={"user_id": player.user["id"]})).status_code == 200
    # no stealing: another account must wait for an unlink
    r = await coach.put(url, json={"user_id": coach.user["id"]})
    assert r.status_code == 409 and r.json()["type"].endswith(":player-linked")
    # a parent is linked to the child by guardianship, never as the player
    r = await coach.put(
        f"/v1/orgs/{org}/teams/{team}/players/{ben}/account", json={"user_id": parent.user["id"]}
    )
    assert r.status_code == 422 and r.json()["type"].endswith(":parent-not-player")
    # only members of this team
    stranger = make_api()
    await stranger.register("stranger@hc-test.ch")
    assert (await coach.put(url, json={"user_id": stranger.user["id"]})).status_code == 404

    assert (await coach.delete(url)).status_code == 204
    entries = {e["player_id"]: e for e in (await coach.get(roster_url(ids))).json()}
    assert entries[ana]["has_account"] is False and entries[ana]["account_user_id"] is None
    assert entries[ben]["has_account"] is False  # the guardianship stays separate
    assert (await coach.put(url, json={"user_id": coach.user["id"]})).status_code == 200

    # another club sees neither the team nor the player
    rival = make_api()
    rival_ids = await setup_club(rival, email="rival@hc-test.ch")
    assert (await rival.put(url, json={"user_id": rival.user["id"]})).status_code == 404
    foreign = f"/v1/orgs/{rival_ids['org']}/teams/{rival_ids['team']}/players/{ana}/account"
    assert (await rival.put(foreign, json={"user_id": rival.user["id"]})).status_code == 404
    assert (await rival.delete(foreign)).status_code == 404


async def test_join_request_approval_with_a_chosen_entry(make_api: Callable[[], Api]) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    org, team = ids["org"], ids["team"]
    taken = await add_player(coach, ids, "Eli", "Huber", 2)
    free = await add_player(coach, ids, "Eli", "Hofer", 9)
    joiner = make_api()
    await joiner.register("eli@hc-test.ch")
    req = (
        await joiner.post(
            f"/v1/teams/{team}/join-requests", json={"first_name": "Eli", "last_name": "H"}
        )
    ).json()
    approve = f"/v1/orgs/{org}/teams/{team}/join-requests/{req['id']}/approve"
    # the first entry already belongs to the coach's own account
    await coach.put(
        f"/v1/orgs/{org}/teams/{team}/players/{taken}/account",
        json={"user_id": coach.user["id"]},
    )
    r = await coach.post(approve, json={"player_id": taken})
    assert r.status_code == 409 and r.json()["type"].endswith(":player-linked")
    r = await coach.post(approve, json={"player_id": free})
    assert r.status_code == 200 and r.json()["player_id"] == free
    entries = {e["player_id"]: e for e in (await coach.get(roster_url(ids))).json()}
    assert entries[free]["account_user_id"] == joiner.user["id"]
    assert entries[taken]["account_user_id"] == coach.user["id"]
