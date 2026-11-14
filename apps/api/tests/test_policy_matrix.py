"""Policy test matrix (BRIEF 3): every role against every endpoint, enforced server-side.

Allowed calls must succeed (2xx). Denied calls must return 403 or 404 (404 where the mere
existence of a resource must not leak). Outsiders (members of another club) always get 404.
"""

from __future__ import annotations

import itertools
import re
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import pytest

from handball_api.core.email import MemoryEmailSender
from handball_api.core.ratelimit import MemoryRateLimiter

from .conftest import Api
from .test_official_report import recorded  # noqa: F401

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
TRAINING = VIDEO_WORK | MANAGER

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
    # official league data (federation onboarding)
    ("GET official link", READERS, lambda a, w: a.get(w.t("/official"))),
    ("GET official suggestions", ORGANISE, lambda a, w: a.get(w.t("/official/suggestions"))),
    ("GET join requests", ORGANISE, lambda a, w: a.get(w.t("/join-requests"))),
    ("GET access requests", ADMIN, lambda a, w: a.get(f"/v1/orgs/{w.org}/access-requests")),
    ("GET verification", MEMBERS, lambda a, w: a.get(f"/v1/orgs/{w.org}/verification")),
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


async def _link_account(a: Api, w: World) -> Any:
    e = await w.new_entry()
    return await a.put(w.t(f"/players/{e['player_id']}/account"), json={"user_id": w.dummy_user})


async def _unlink_account(a: Api, w: World) -> Any:
    e = await w.new_entry()
    await w.admin.put(w.t(f"/players/{e['player_id']}/account"), json={"user_id": w.dummy_user})
    return await a.delete(w.t(f"/players/{e['player_id']}/account"))


async def _put_status(a: Api, w: World) -> Any:
    e = await w.new_entry()
    return await a.put(w.t(f"/players/{e['player_id']}/status"), json={"kind": "absent"})


async def _delete_status(a: Api, w: World) -> Any:
    e = await w.new_entry()
    await w.admin.put(w.t(f"/players/{e['player_id']}/status"), json={"kind": "injured"})
    return await a.delete(w.t(f"/players/{e['player_id']}/status"))


async def _get_assignment(a: Api, w: World) -> Any:
    r = await w.admin.post(
        w.t("/assignments"),
        json={"kind": "drill", "target_id": "finishing_wings", "title": "M", "notify_email": False},
    )
    assert r.status_code == 201, r.text
    return await a.get(f"/v1/orgs/{w.org}/assignments/{r.json()['id']}")


_SLOT = {"weekday": 2, "start_time": "19:00", "duration_min": 90}
_DRILL = {"name": "Matrix", "minutes": 10}


async def _new_slot(w: World) -> str:
    r = await w.admin.post(w.t(f"/seasons/{w.season}/training-slots"), json=_SLOT)
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


async def _put_slot(a: Api, w: World) -> Any:
    return await a.put(f"/v1/orgs/{w.org}/training-slots/{await _new_slot(w)}", json=_SLOT)


async def _delete_slot(a: Api, w: World) -> Any:
    return await a.delete(f"/v1/orgs/{w.org}/training-slots/{await _new_slot(w)}")


async def _generate(a: Api, w: World) -> Any:
    await _new_slot(w)
    day = f"2040-01-{_seq(w) % 28 + 1:02d}"
    return await a.post(
        w.t(f"/seasons/{w.season}/training-slots/generate"), json={"from": day, "to": day}
    )


async def _new_drill(w: World) -> str:
    r = await w.admin.post(w.t("/drills"), json=_DRILL)
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


async def _get_drill(a: Api, w: World) -> Any:
    return await a.get(f"/v1/orgs/{w.org}/drills/{await _new_drill(w)}")


async def _put_drill(a: Api, w: World) -> Any:
    return await a.put(f"/v1/orgs/{w.org}/drills/{await _new_drill(w)}", json=_DRILL)


async def _delete_drill(a: Api, w: World) -> Any:
    return await a.delete(f"/v1/orgs/{w.org}/drills/{await _new_drill(w)}")


async def _get_consents(a: Api, w: World) -> Any:
    e = await w.new_entry()
    return await a.get(w.t(f"/players/{e['player_id']}/consents"))


async def _get_season_line(a: Api, w: World) -> Any:
    e = await w.new_entry()
    return await a.get(w.t(f"/seasons/{w.season}/players/{e['player_id']}/line"))


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
            # another file each time: the same file twice in a match is refused (409)
            json={"filename": f"{uuid.uuid4().hex}.mp4", "size_bytes": 100},
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
    (
        "GET highlights",
        READERS,
        lambda a, w: a.get(f"/v1/orgs/{w.org}/matches/{w.match}/highlights"),
    ),
    ("GET match parts", READERS, lambda a, w: a.get(f"/v1/orgs/{w.org}/matches/{w.match}/parts")),
    (
        "GET match boundaries",
        READERS,
        lambda a, w: a.get(f"/v1/orgs/{w.org}/matches/{w.match}/boundaries"),
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
    ("GET assignment progress", VIDEO_WORK, _get_assignment),
    ("GET player statuses", TRAINING, lambda a, w: a.get(w.t("/player-statuses"))),
    ("PUT player status", TRAINING, _put_status),
    ("DELETE player status", TRAINING, _delete_status),
    ("GET assistant conversations", VIDEO_WORK, lambda a, w: a.get(w.t("/assistant"))),
    ("GET matrix templates", READERS, lambda a, w: a.get(w.t("/matrix/templates"))),
    ("GET sessions", READERS, lambda a, w: a.get(w.t("/sessions"))),
    (
        "GET training slots",
        READERS,
        lambda a, w: a.get(w.t(f"/seasons/{w.season}/training-slots")),
    ),
    (
        "POST training slot",
        TRAINING,
        lambda a, w: a.post(w.t(f"/seasons/{w.season}/training-slots"), json=_SLOT),
    ),
    ("PUT training slot", TRAINING, _put_slot),
    ("DELETE training slot", TRAINING, _delete_slot),
    ("POST generate sessions", TRAINING, _generate),
    ("GET drills", READERS, lambda a, w: a.get(w.t("/drills"))),
    ("POST drill", TRAINING, lambda a, w: a.post(w.t("/drills"), json=_DRILL)),
    ("GET drill", READERS, _get_drill),
    ("PUT drill", TRAINING, _put_drill),
    ("DELETE drill", TRAINING, _delete_drill),
    ("GET mark keys", READERS, lambda a, w: a.get(w.t("/mark-keys"))),
    (
        "POST mark session",
        VIDEO_WORK,
        lambda a, w: a.post(f"/v1/orgs/{w.org}/matches/{w.match}/mark-sessions", json={}),
    ),
    (
        "POST session",
        TRAINING,
        lambda a, w: a.post(w.t("/sessions"), json={"on_date": "2026-12-01"}),
    ),
    ("GET focus plans", READERS, lambda a, w: a.get(w.t("/focus"))),
    ("POST calendar link", TRAINING, lambda a, w: a.post(w.t("/calendar"))),
    (
        "POST matrix template",
        VIDEO_WORK,
        lambda a, w: a.post(
            w.t("/matrix/templates"),
            json={
                "name": f"T{uuid.uuid4().hex[:6]}",
                "config": {"rows": "match", "metrics": ["goals"]},
            },
        ),
    ),
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
    ("GET collections", VIDEO_WORK, lambda a, w: a.get(w.t("/collections"))),
    ("GET consent link", ORGANISE, lambda a, w: a.get(w.t("/consent-link"))),
    (
        "POST collection",
        VIDEO_WORK,
        lambda a, w: a.post(w.t("/collections"), json={"title": f"S{_seq(w)}"}),
    ),
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
    ("PUT player account", ORGANISE, _link_account),
    ("DELETE player account", ORGANISE, _unlink_account),
    ("GET consents", ORGANISE, _get_consents),
    (
        "GET consent overview",
        ORGANISE | {"analyst"},
        lambda a, w: a.get(w.t(f"/seasons/{w.season}/consents")),
    ),
    # players read only their own line (the matrix player has no roster entry)
    ("GET season line", TRAINING, _get_season_line),
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


@pytest.mark.usefixtures("recorded")
async def test_analysis_review_endpoints(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    """The newer endpoints of the match workspace (official report, goal candidates, court,
    track identities, referee kit) against every role: a player or parent cannot change them, a
    coach of another club gets 404 for each of them."""
    from handball_api.core.jobs import MemoryJobQueue

    from .test_goal_candidates import FOUND
    from .test_identity_sync import _finish, _ingest, _tracks
    from .test_matches import upload
    from .test_official_report import CH_URL

    w, clients = await build_world(make_api, outbox)
    admin = w.admin
    m = f"/v1/orgs/{w.org}/matches/{w.match}"
    r = await admin.post(f"{m}/official-report", json={"url": CH_URL})
    assert r.status_code == 200, r.text
    video = await upload(admin, {"org": w.org}, w.match, b"v" * 100)
    jobs: MemoryJobQueue = admin.app.state.jobs
    await _ingest(admin, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"], audio=False)
    court = {
        "homography": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "image_size": [1280, 720],
        "confidence": 0.8,
        "reprojection_px": 1.0,
        "source": "heuristic",
    }
    await _finish(
        admin,
        jobs.jobs[-1][2],
        {"calibration": court, "tracks": _tracks(), "goal_candidates": FOUND},
    )
    goal = next(g for g in (await admin.get(f"{m}/official-report/comparison")).json()["goals"])
    cand = (await admin.get(f"{m}/goal-candidates")).json()["candidates"][0]
    v = f"/v1/orgs/{w.org}/videos/{video['id']}"

    checks: list[tuple[str, set[str], Call]] = [
        ("GET comparison", READERS, lambda a, w: a.get(f"{m}/official-report/comparison")),
        (
            "PUT official review",
            STAFF,
            lambda a, w: a.put(
                f"{m}/official-report/review", json={"event_id": goal["event_id"], "status": None}
            ),
        ),
        (
            "POST official report",
            STAFF,
            lambda a, w: a.post(f"{m}/official-report", json={"url": CH_URL}),
        ),
        ("GET goal candidates", READERS, lambda a, w: a.get(f"{m}/goal-candidates")),
        (
            "PUT candidate review",
            STAFF,
            lambda a, w: a.put(f"{m}/goal-candidates/{cand['id']}/review", json={"status": None}),
        ),
        ("GET analysis", READERS, lambda a, w: a.get(f"{v}/analysis")),
        ("POST court confirm", MATCH_WRITE, lambda a, w: a.post(f"{v}/calibration/confirm")),
        (
            "PUT track identity",
            STAFF,
            lambda a, w: a.put(f"{v}/tracks/1/identity", json={"number": 7}),
        ),
        (
            "PATCH referee kit",
            MATCH_WRITE,
            lambda a, w: a.patch(m, json={"kit_referee": "#111111"}),
        ),
    ]
    failures: list[str] = []
    for name, allowed, call in checks:
        for role in ROLES:
            r = await call(clients[role], w)
            ok = 200 <= r.status_code < 300
            if role in allowed and not ok:
                failures.append(
                    f"{name:22} {role:16} expected 2xx, got {r.status_code} {r.text[:100]}"
                )
            if role not in allowed:
                expected = {404} if role == "outsider" else {403, 404}
                if r.status_code not in expected:
                    failures.append(
                        f"{name:22} {role:16} expected {sorted(expected)}, got {r.status_code}"
                    )
    assert not failures, "\n" + "\n".join(failures)
