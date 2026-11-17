"""The product's four roles (K18): Trainer, Co-Trainer, Spieler, Eltern, on top of the stored
organisation and team roles; and the honest entry without mail delivery (L2, L10)."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

import pytest
import structlog

from handball_api.core.email import ConsoleEmailSender, Email, MemoryEmailSender
from handball_api.core.ratelimit import MemoryRateLimiter
from handball_api.models.enums import OrgRole, PersonRole, TeamRole
from handball_api.services.policies import person_role, stored_roles

from .conftest import Api, setup_club
from .test_matches import new_match, upload

pytestmark = pytest.mark.usefixtures("clean_db")


def test_person_role_mapping() -> None:
    assert person_role(OrgRole.ORG_ADMIN, TeamRole.COACH) == PersonRole.TRAINER
    assert person_role(OrgRole.MEMBER, TeamRole.COACH) == PersonRole.CO_TRAINER
    for older in (
        TeamRole.ANALYST,
        TeamRole.TEAM_MANAGER,
        TeamRole.GOALKEEPER_COACH,
        TeamRole.ATHLETIC_COACH,
    ):
        assert person_role(OrgRole.MEMBER, older) == PersonRole.CO_TRAINER
        assert person_role(OrgRole.ORG_ADMIN, older) == PersonRole.TRAINER
    assert person_role(OrgRole.MEMBER, TeamRole.GOALKEEPER) == PersonRole.PLAYER
    assert person_role(OrgRole.MEMBER, TeamRole.PLAYER) == PersonRole.PLAYER
    assert person_role(OrgRole.MEMBER, TeamRole.PARENT) == PersonRole.PARENT
    # guests only see shared links: no role in the team
    assert person_role(OrgRole.MEMBER, TeamRole.GUEST) is None
    assert person_role(OrgRole.ORG_ADMIN, None) == PersonRole.TRAINER
    assert stored_roles(PersonRole.TRAINER) == (OrgRole.ORG_ADMIN, TeamRole.COACH)
    assert stored_roles(PersonRole.CO_TRAINER) == (OrgRole.MEMBER, TeamRole.COACH)


async def _member(
    make_api: Callable[[], Api],
    outbox: MemoryEmailSender,
    coach: Api,
    ids: dict[str, Any],
    email: str,
    team_role: str,
    org_role: str = "member",
) -> Api:
    body = {"email": email, "team_id": ids["team"], "team_role": team_role, "org_role": org_role}
    r = await coach.post(f"/v1/orgs/{ids['org']}/invitations", json=body)
    assert r.status_code == 201, r.text
    token = re.search(r"/invite/([\w-]+)", outbox.outbox[-1].text)
    assert token
    api = make_api()
    api.app.state.rate_limiter = MemoryRateLimiter()
    assert (await api.register(email, invitation_token=token.group(1))).status_code == 201
    return api


async def test_player_uploads_but_does_not_delete(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    player = await _member(make_api, outbox, coach, ids, "lea@hc-test.ch", "player")
    m = await new_match(player, ids)
    video = await upload(player, ids, m["id"], b"v" * 100)
    # a scene and a collection of her own
    r = await player.post(
        f"/v1/orgs/{ids['org']}/clips", json={"match_id": m["id"], "start_ms": 0, "end_ms": 900}
    )
    assert r.status_code == 201, r.text
    r = await player.post(
        f"/v1/orgs/{ids['org']}/teams/{ids['team']}/collections", json={"title": "Meine"}
    )
    assert r.status_code == 201, r.text
    # an arrived video and the match are deleted by the staff only
    assert (await player.delete(f"/v1/orgs/{ids['org']}/videos/{video['id']}")).status_code == 403
    assert (await player.delete(f"/v1/orgs/{ids['org']}/matches/{m['id']}")).status_code == 403
    # inviting and the squad are not hers
    r = await player.post(
        f"/v1/orgs/{ids['org']}/invitations",
        json={"email": "x@hc-test.ch", "team_id": ids["team"], "team_role": "player"},
    )
    assert r.status_code == 403
    assert (await coach.delete(f"/v1/orgs/{ids['org']}/matches/{m['id']}")).status_code == 204


async def test_player_cancels_own_running_upload(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    player = await _member(make_api, outbox, coach, ids, "lea@hc-test.ch", "goalkeeper")
    m = await new_match(coach, ids)
    r = await player.post(
        f"/v1/orgs/{ids['org']}/matches/{m['id']}/videos",
        json={"filename": "a.mp4", "size_bytes": 100, "content_type": "video/mp4"},
    )
    assert r.status_code == 201, r.text
    vid = r.json()["video"]["id"]
    assert (await player.delete(f"/v1/orgs/{ids['org']}/videos/{vid}")).status_code == 204


async def test_player_revokes_only_own_links(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    player = await _member(make_api, outbox, coach, ids, "lea@hc-test.ch", "player")
    base = f"/v1/orgs/{ids['org']}/teams/{ids['team']}"
    coll = (await coach.post(f"{base}/collections", json={"title": "Abwehr"})).json()
    theirs = await coach.post(
        f"{base}/share-links", json={"kind": "collection", "target_id": coll["id"], "days": 7}
    )
    mine = await player.post(
        f"{base}/share-links", json={"kind": "collection", "target_id": coll["id"], "days": 7}
    )
    assert theirs.status_code == 201, theirs.text
    assert mine.status_code == 201, mine.text
    org = f"/v1/orgs/{ids['org']}"
    assert (await player.delete(f"{org}/share-links/{theirs.json()['id']}")).status_code == 403
    assert (await player.delete(f"{org}/share-links/{mine.json()['id']}")).status_code == 204
    assert (await coach.delete(f"{org}/share-links/{mine.json()['id']}")).status_code == 204


async def test_person_role_and_members(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    trainer = make_api()
    ids = await setup_club(trainer)
    co = await _member(make_api, outbox, trainer, ids, "co@hc-test.ch", "analyst")
    lea = await _member(make_api, outbox, trainer, ids, "lea@hc-test.ch", "player")
    base = f"/v1/orgs/{ids['org']}/teams/{ids['team']}/members"
    members = {m["email"]: m for m in (await trainer.get(base)).json()}
    assert members["coach@hc-test.ch"]["person_role"] == "trainer"
    # the older analyst reads as Co-Trainer and keeps its stored role
    assert members["co@hc-test.ch"]["person_role"] == "co_trainer"
    assert members["co@hc-test.ch"]["role"] == "analyst"
    assert members["lea@hc-test.ch"]["person_role"] == "player"
    lea_id = lea.user["id"]
    co_id = co.user["id"]

    # a Co-Trainer makes a player Co-Trainer, but not a Trainer
    r = await co.put(f"{base}/{lea_id}/person-role", json={"role": "co_trainer"})
    assert r.status_code == 200, r.text
    assert r.json()["person_role"] == "co_trainer"
    assert r.json()["role"] == "coach"
    assert (
        await co.put(f"{base}/{lea_id}/person-role", json={"role": "trainer"})
    ).status_code == 403
    # the Trainer makes her Trainer: club admin
    r = await trainer.put(f"{base}/{lea_id}/person-role", json={"role": "trainer"})
    assert r.status_code == 200, r.text
    assert r.json()["person_role"] == "trainer"
    me = (await lea.get("/v1/me")).json()
    assert me["organizations"][0]["role"] == "org_admin"
    # a Co-Trainer cannot change or remove a Trainer
    r = await co.patch(f"{base}/{lea_id}", json={"role": "player"})
    assert r.status_code == 403
    assert (await co.delete(f"{base}/{lea_id}")).status_code == 403
    # back to Spieler: no longer club admin
    r = await trainer.put(f"{base}/{lea_id}/person-role", json={"role": "player"})
    assert r.status_code == 200, r.text
    assert r.json()["person_role"] == "player"
    assert (await lea.get("/v1/me")).json()["organizations"][0]["role"] == "member"
    # parents come by invitation with their child
    r = await trainer.put(f"{base}/{co_id}/person-role", json={"role": "parent"})
    assert r.status_code == 422


async def test_trainer_invitation_makes_club_admin(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    trainer = make_api()
    ids = await setup_club(trainer)
    second = await _member(
        make_api, outbox, trainer, ids, "zweit@hc-test.ch", "coach", org_role="org_admin"
    )
    assert second.user["organizations"][0]["role"] == "org_admin"
    members = (await trainer.get(f"/v1/orgs/{ids['org']}/teams/{ids['team']}/members")).json()
    assert {m["email"]: m["person_role"] for m in members}["zweit@hc-test.ch"] == "trainer"


async def test_invitation_hands_the_link_to_the_inviter(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    trainer = make_api()
    ids = await setup_club(trainer)
    r = await trainer.post(
        f"/v1/orgs/{ids['org']}/invitations",
        json={"email": "lea@hc-test.ch", "team_id": ids["team"], "team_role": "player"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["mailed"] is True
    assert body["link"].startswith("http://web.test/invite/")
    assert body["link"].rsplit("/", 1)[1] in outbox.outbox[-1].text
    # the list does not carry links
    listed = (await trainer.get(f"/v1/orgs/{ids['org']}/invitations")).json()
    assert "link" not in listed[0]


async def test_public_config_says_whether_mail_goes_out(make_api: Callable[[], Api]) -> None:
    api = make_api()
    cfg = (await api.get("/v1/public/config")).json()
    assert cfg["mail_enabled"] is True
    api.app.state.settings.mail_enabled = False
    try:
        assert (await api.get("/v1/public/config")).json()["mail_enabled"] is False
        # no passwordless account without a way in: the entry registers with a password
        r = await api.post("/v1/auth/start", json={"email": "neu@hc-test.ch", "locale": "de-CH"})
        assert r.status_code == 409
        assert r.json()["type"].endswith("mail-unavailable")
        assert (await api.register("neu@hc-test.ch")).status_code == 201
    finally:
        api.app.state.settings.mail_enabled = None


async def test_console_mailer_logs_no_links() -> None:
    mail = Email(
        to="lea@hc-test.ch",
        subject="Anmelden",
        text="Hallo\nhttps://app.test/auth/magic?token=SECRET123",
        template="magic_link",
    )
    with structlog.testing.capture_logs() as logs:
        await ConsoleEmailSender().send(mail)
        await ConsoleEmailSender(full=True).send(mail)
    quiet, full = logs
    assert "SECRET123" not in str(quiet)
    assert "lea@" not in str(quiet)
    assert quiet["to_domain"] == "hc-test.ch"
    assert quiet["template"] == "magic_link"
    assert "SECRET123" in full["text"]
