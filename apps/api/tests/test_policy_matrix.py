"""Policy test matrix (BRIEF 3): every role against every endpoint, enforced server-side.

Allowed calls must succeed (2xx). Denied calls must return 403 or 404 (404 where the mere
existence of a resource must not leak). Outsiders (members of another club) always get 404.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import pytest

from handball_api.core.email import MemoryEmailSender
from handball_api.core.ratelimit import MemoryRateLimiter

from .conftest import Api

pytestmark = pytest.mark.usefixtures("clean_db")

TEAM_ROLES = (
    "coach",
    "analyst",
    "player",
    "goalkeeper",
    "guest",
    "goalkeeper_coach",
    "athletic_coach",
    "team_manager",
    "parent",
)
ROLES = ("org_admin", *TEAM_ROLES, "outsider")
ADMIN = {"org_admin"}
ASSISTANTS = {"goalkeeper_coach", "athletic_coach"}
MANAGER = {"team_manager"}
STAFF = ADMIN | {"coach", "analyst"}
READERS = STAFF | {"player", "goalkeeper"} | ASSISTANTS | MANAGER
# parents only see their own children (guardianships), not the team
MEMBERS = READERS | {"guest", "parent"}
COACHES = ADMIN | {"coach"}
ORGANISE = COACHES | MANAGER
SEASON = STAFF | MANAGER
TEAM_MEMBERS = STAFF | ASSISTANTS | MANAGER
MATCH_WRITE = STAFF | MANAGER
VIDEO_WORK = STAFF | ASSISTANTS

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


@dataclass
class World:
    admin: Api
    org: str
    team: str
    season: str
    dummy_user: str
    counter: itertools.count[int]
    match: str = ""
    opponent: str = ""

    def t(self, path: str = "") -> str:
        return f"/v1/orgs/{self.org}/teams/{self.team}{path}"

    async def new_entry(self) -> dict[str, Any]:
        n = next(self.counter)
        r = await self.admin.post(
            self.t(f"/seasons/{self.season}/roster"),
            json={"first_name": "P", "last_name": str(n)},
        )
        assert r.status_code == 201, r.text
        data: dict[str, Any] = r.json()
        return data


Call = Callable[[Api, World], Awaitable[Any]]


def _seq(w: World) -> int:
    return next(w.counter)


async def _new_team(w: World) -> str:
    r = await w.admin.post(
        f"/v1/orgs/{w.org}/teams",
        json={"name": f"T{_seq(w)}", "gender": "men", "join_as_coach": False},
    )
    return str(r.json()["id"])


ENDPOINTS: list[tuple[str, set[str], Call]] = [
    ("GET org", MEMBERS, lambda a, w: a.get(f"/v1/orgs/{w.org}")),
    ("PATCH org", ADMIN, lambda a, w: a.patch(f"/v1/orgs/{w.org}", json={"name": "HC Matrix"})),
    (
        "PUT logo",
        ADMIN,
        lambda a, w: a.put(f"/v1/orgs/{w.org}/logo", files={"file": ("l.png", PNG, "image/png")}),
    ),
    ("GET org members", ADMIN, lambda a, w: a.get(f"/v1/orgs/{w.org}/members")),
    (
        "PATCH org member role",
        ADMIN,
        lambda a, w: a.patch(
            f"/v1/orgs/{w.org}/members/{w.dummy_user}", json={"org_role": "member"}
        ),
    ),
    ("GET my consents", MEMBERS, lambda a, w: a.get(f"/v1/orgs/{w.org}/me/consents")),
    ("GET teams", MEMBERS, lambda a, w: a.get(f"/v1/orgs/{w.org}/teams")),
    (
        "POST team",
        ADMIN,
        lambda a, w: a.post(
            f"/v1/orgs/{w.org}/teams", json={"name": f"N{_seq(w)}", "gender": "women"}
        ),
    ),
    ("GET team", READERS, lambda a, w: a.get(w.t())),
    ("PATCH team", COACHES, lambda a, w: a.patch(w.t(), json={"league": "2. Liga"})),
    ("GET seasons", READERS, lambda a, w: a.get(w.t("/seasons"))),
    (
        "POST season",
        SEASON,
        lambda a, w: a.post(
            w.t("/seasons"),
            json={"label": f"S{_seq(w)}", "starts_on": "2040-07-01", "ends_on": "2041-06-30"},
        ),
    ),
    ("GET team members", TEAM_MEMBERS, lambda a, w: a.get(w.t("/members"))),
    (
        "PATCH team member",
        COACHES,
        lambda a, w: a.patch(w.t(f"/members/{w.dummy_user}"), json={"role": "player"}),
    ),
    ("GET roster", READERS, lambda a, w: a.get(w.t(f"/seasons/{w.season}/roster"))),
    (
        "POST roster",
        ORGANISE,
        lambda a, w: a.post(
            w.t(f"/seasons/{w.season}/roster"),
            json={"first_name": "X", "last_name": f"Y{_seq(w)}"},
        ),
    ),
    (
        "POST roster import",
        ORGANISE,
        lambda a, w: a.post(
            w.t(f"/seasons/{w.season}/roster/import"),
            files={"file": ("k.csv", b"Vorname;Nachname\nA;B\n", "text/csv")},
        ),
    ),
    (
        "POST invitation (team)",
        ORGANISE,
        lambda a, w: a.post(
            f"/v1/orgs/{w.org}/invitations",
            json={"email": f"i{_seq(w)}@hc-test.ch", "team_id": w.team, "team_role": "player"},
        ),
    ),
    (
        "POST invitation (org admin)",
        ADMIN,
        lambda a, w: a.post(
            f"/v1/orgs/{w.org}/invitations",
            json={"email": f"j{_seq(w)}@hc-test.ch", "org_role": "org_admin"},
        ),
    ),
    ("GET invitations", ADMIN, lambda a, w: a.get(f"/v1/orgs/{w.org}/invitations")),
]


async def _patch_entry(a: Api, w: World) -> Any:
    e = await w.new_entry()
    return await a.patch(w.t(f"/roster/{e['id']}"), json={"last_name": "Z"})


async def _delete_entry(a: Api, w: World) -> Any:
    e = await w.new_entry()
    return await a.delete(w.t(f"/roster/{e['id']}"))


async def _get_consents(a: Api, w: World) -> Any:
    e = await w.new_entry()
    return await a.get(w.t(f"/players/{e['player_id']}/consents"))


async def _post_consent(a: Api, w: World) -> Any:
    e = await w.new_entry()
    return await a.post(
        w.t(f"/players/{e['player_id']}/consents"),
        json={
            "kind": "analysis",
            "given_by": "self",
            "given_by_name": "P",
            "given_at": "2026-10-01T10:00:00Z",
        },
    )


async def _delete_team(a: Api, w: World) -> Any:
    tid = await _new_team(w)
    return await a.delete(f"/v1/orgs/{w.org}/teams/{tid}")


ENDPOINTS += [
    ("GET opponents", READERS, lambda a, w: a.get(f"/v1/orgs/{w.org}/opponents")),
    (
        "POST opponent",
        MATCH_WRITE,
        lambda a, w: a.post(f"/v1/orgs/{w.org}/opponents", json={"name": f"O{_seq(w)}"}),
    ),
    (
        "GET opponent players",
        READERS,
        lambda a, w: a.get(f"/v1/orgs/{w.org}/opponents/{w.opponent}/players"),
    ),
    (
        "PUT opponent players",
        MATCH_WRITE,
        lambda a, w: a.put(
            f"/v1/orgs/{w.org}/opponents/{w.opponent}/players", json=[{"number": 7}]
        ),
    ),
    ("GET matches", READERS, lambda a, w: a.get(w.t("/matches"))),
    (
        "POST match",
        MATCH_WRITE,
        lambda a, w: a.post(
            w.t("/matches"),
            json={"opponent_name": "Gegner", "kickoff_at": "2026-11-07T18:00:00+01:00"},
        ),
    ),
    ("GET match", READERS, lambda a, w: a.get(f"/v1/orgs/{w.org}/matches/{w.match}")),
    (
        "PATCH match",
        MATCH_WRITE,
        lambda a, w: a.patch(f"/v1/orgs/{w.org}/matches/{w.match}", json={"venue": "Halle"}),
    ),
    (
        "POST video upload",
        MATCH_WRITE,
        lambda a, w: a.post(
            f"/v1/orgs/{w.org}/matches/{w.match}/videos",
            json={"filename": "a.mp4", "size_bytes": 100},
        ),
    ),
    ("GET clips", READERS, lambda a, w: a.get(f"/v1/orgs/{w.org}/matches/{w.match}/clips")),
    (
        "POST clip",
        VIDEO_WORK,
        lambda a, w: a.post(
            f"/v1/orgs/{w.org}/clips", json={"match_id": w.match, "start_ms": 0, "end_ms": 1000}
        ),
    ),
    ("GET playlists", READERS, lambda a, w: a.get(w.t("/playlists"))),
    ("POST playlist", VIDEO_WORK, lambda a, w: a.post(w.t("/playlists"), json={"title": "P"})),
    ("GET comments", READERS, lambda a, w: a.get(f"/v1/orgs/{w.org}/matches/{w.match}/comments")),
    (
        "POST comment",
        READERS,
        lambda a, w: a.post(
            f"/v1/orgs/{w.org}/matches/{w.match}/comments", json={"t_ms": 1, "body": "x"}
        ),
    ),
    (
        "GET annotations",
        READERS,
        lambda a, w: a.get(f"/v1/orgs/{w.org}/matches/{w.match}/annotations"),
    ),
    (
        "POST annotation",
        VIDEO_WORK,
        lambda a, w: a.post(
            f"/v1/orgs/{w.org}/matches/{w.match}/annotations",
            json={"t_ms": 1, "shapes": [{"kind": "circle", "points": [[0.5, 0.5], [0.6, 0.6]]}]},
        ),
    ),
    ("GET events", READERS, lambda a, w: a.get(f"/v1/orgs/{w.org}/matches/{w.match}/events")),
    (
        "POST event",
        STAFF,
        lambda a, w: a.post(
            f"/v1/orgs/{w.org}/matches/{w.match}/events",
            json={"type": "shot", "side": "own", "outcome": "goal", "t_ms": 1000},
        ),
    ),
    (
        "GET shot export",
        VIDEO_WORK,
        lambda a, w: a.get(f"/v1/orgs/{w.org}/matches/{w.match}/exports/shots"),
    ),
    ("GET stats", READERS, lambda a, w: a.get(f"/v1/orgs/{w.org}/matches/{w.match}/stats")),
    (
        "PUT kickoff",
        STAFF,
        lambda a, w: a.put(
            f"/v1/orgs/{w.org}/matches/{w.match}/kickoff", json={"period": 1, "t_ms": 0}
        ),
    ),
    ("GET physical", READERS, lambda a, w: a.get(f"/v1/orgs/{w.org}/matches/{w.match}/physical")),
    ("GET plays", READERS, lambda a, w: a.get(w.t("/plays"))),
    ("GET team assignments", VIDEO_WORK, lambda a, w: a.get(w.t("/assignments"))),
    ("GET presentations", READERS, lambda a, w: a.get(w.t("/presentations"))),
    (
        "POST presentation",
        VIDEO_WORK,
        lambda a, w: a.post(w.t("/presentations"), json={"title": f"P{_seq(w)}"}),
    ),
    ("GET tag sets", VIDEO_WORK, lambda a, w: a.get(w.t("/tag-sets"))),
    (
        "POST tag set",
        VIDEO_WORK,
        lambda a, w: a.post(w.t("/tag-sets"), json={"name": f"Set {_seq(w)}"}),
    ),
    ("POST search", VIDEO_WORK, lambda a, w: a.post(w.t("/search"), json={})),
    ("GET saved filters", VIDEO_WORK, lambda a, w: a.get(w.t("/saved-filters"))),
    (
        "GET match tag links",
        VIDEO_WORK,
        lambda a, w: a.get(f"/v1/orgs/{w.org}/matches/{w.match}/tag-links"),
    ),
    ("GET share links", VIDEO_WORK, lambda a, w: a.get(w.t("/share-links"))),
    ("GET my assignments", MEMBERS, lambda a, w: a.get(f"/v1/orgs/{w.org}/me/assignments")),
    ("GET notifications", MEMBERS, lambda a, w: a.get(f"/v1/orgs/{w.org}/me/notifications")),
    (
        "GET insights",
        READERS,
        lambda a, w: a.get(f"/v1/orgs/{w.org}/matches/{w.match}/insights"),
    ),
    ("GET season stats", READERS, lambda a, w: a.get(w.t(f"/seasons/{w.season}/stats"))),
    (
        "POST play",
        STAFF,
        lambda a, w: a.post(
            w.t("/plays"),
            json={
                "name": "Matrix",
                "category": "attack",
                "doc": {
                    "formatVersion": 1,
                    "court": "half",
                    "frames": [{"tokens": [], "duration_ms": 1000}],
                },
            },
        ),
    ),
    ("PATCH roster entry", ORGANISE, _patch_entry),
    ("DELETE roster entry", ORGANISE, _delete_entry),
    ("GET consents", ORGANISE, _get_consents),
    ("POST consent", ORGANISE, _post_consent),
    ("DELETE team", ADMIN, _delete_team),
]


async def build_world(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> tuple[World, dict[str, Api]]:
    admin = make_api()
    await admin.register("admin@hc-test.ch")
    org = (await admin.post("/v1/orgs", json={"name": "HC Matrix"})).json()["id"]
    team = (
        await admin.post(
            f"/v1/orgs/{org}/teams",
            json={"name": "Herren", "gender": "men", "join_as_coach": False},
        )
    ).json()
    w = World(admin, org, team["id"], team["current_season"]["id"], "", itertools.count(1))
    clients: dict[str, Api] = {"org_admin": admin}
    child = await w.new_entry()
    for role in (*TEAM_ROLES, "dummy"):
        body = {
            "email": f"{role}@hc-test.ch",
            "team_id": w.team,
            "team_role": "player" if role == "dummy" else role,
        }
        if role == "parent":
            body["player_id"] = child["player_id"]
        r = await admin.post(f"/v1/orgs/{org}/invitations", json=body)
        assert r.status_code == 201, r.text
        token = re.search(r"/invite/([\w-]+)", outbox.outbox[-1].text)
        assert token
        api = make_api()
        api.app.state.rate_limiter = MemoryRateLimiter()  # many sign-ups from one test IP
        assert (
            await api.register(f"{role}@hc-test.ch", invitation_token=token.group(1))
        ).status_code == 201
        if role == "dummy":
            w.dummy_user = api.user["id"]
        else:
            clients[role] = api
    created = (
        await admin.post(
            w.t("/matches"),
            json={"opponent_name": "Matrix Gegner", "kickoff_at": "2026-11-07T18:00:00+01:00"},
        )
    ).json()
    w.match, w.opponent = created["id"], created["opponent"]["id"]
    outsider = make_api()
    outsider.app.state.rate_limiter = MemoryRateLimiter()
    await outsider.register("outsider@hc-test.ch")
    await outsider.post("/v1/orgs", json={"name": "Other Club"})
    clients["outsider"] = outsider
    return w, clients


async def test_policy_matrix(make_api: Callable[[], Api], outbox: MemoryEmailSender) -> None:
    w, clients = await build_world(make_api, outbox)
    failures: list[str] = []
    for name, allowed, call in ENDPOINTS:
        for role in ROLES:
            r = await call(clients[role], w)
            ok = 200 <= r.status_code < 300
            if role in allowed and not ok:
                failures.append(
                    f"{name:28} {role:16} expected 2xx, got {r.status_code} {r.text[:120]}"
                )
            if role not in allowed:
                expected = {404} if role == "outsider" else {403, 404}
                if r.status_code not in expected:
                    failures.append(
                        f"{name:28} {role:16} expected {sorted(expected)}, got {r.status_code}"
                    )
    assert not failures, "\n" + "\n".join(failures)
    assert len(ENDPOINTS) * len(ROLES) >= 150


async def test_unauthenticated_gets_401(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    w, _ = await build_world(make_api, outbox)
    anon = make_api()
    for name, _allowed, call in ENDPOINTS:
        if name in {
            "PATCH roster entry",
            "DELETE roster entry",
            "GET consents",
            "POST consent",
            "DELETE team",
        }:
            continue
        r = await call(anon, w)
        assert r.status_code == 401, (name, r.status_code)
