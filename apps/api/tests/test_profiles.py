"""Public player profile (addendum 01, 5.8): opt-in, consent, youth protection, revocation."""

from __future__ import annotations

import uuid
from collections.abc import Callable

import asyncpg
import pytest

from handball_api.core.storage import MemoryStorage

from .conftest import Api, setup_club
from .test_matches import new_match

pytestmark = pytest.mark.usefixtures("clean_db")


async def test_profile_opt_in_public_view_and_revocation(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org, team, season = ids["org"], ids["team"], ids["season"]
    roster = f"/v1/orgs/{org}/teams/{team}/seasons/{season}/roster"
    lena = (
        await api.post(
            roster,
            json={
                "first_name": "Lena",
                "last_name": "Muster",
                "jersey_number": 7,
                "birth_year": 1999,
            },
        )
    ).json()["player_id"]
    tim = (
        await api.post(
            roster,
            json={
                "first_name": "Tim",
                "last_name": "Junior",
                "jersey_number": 9,
                "birth_year": 2010,
            },
        )
    ).json()["player_id"]
    user_id = await owner_conn.fetchval("SELECT id FROM users LIMIT 1")
    await owner_conn.execute("UPDATE players SET user_id = $1 WHERE id = $2::uuid", user_id, lena)
    await owner_conn.execute(
        "INSERT INTO guardianships (id, organization_id, user_id, player_id) "
        "VALUES (gen_random_uuid(), $1::uuid, $2, $3::uuid)",
        org,
        user_id,
        tim,
    )
    mine = (await api.get(f"/v1/orgs/{org}/me/profiles")).json()
    assert {(p["name"], p["relation"], p["blocked"]) for p in mine} == {
        ("Lena Muster", "self", "consent-missing"),
        ("Tim Junior", "guardian", "consent-missing"),
    }
    url = f"/v1/orgs/{org}/players/{lena}/profile"
    body = {
        "active": True,
        "bio": "Rückraum links, Linkshänderin.",
        "stats": ["goals", "shooting_pct", "nope"],
    }
    r = await api.put(url, json=body)
    assert r.status_code == 403 and r.json()["type"].endswith("consent-missing")
    # a draft (not public) can be prepared before the consent
    assert (await api.put(url, json={**body, "active": False})).status_code == 200

    assert (
        await api.post(f"/v1/orgs/{org}/me/consents/{lena}", json={"kind": "public_profile"})
    ).status_code == 201
    saved = (await api.put(url, json=body)).json()
    assert (
        saved["active"] and saved["stats"] == ["goals", "shooting_pct"] and not saved["indexable"]
    )
    slug = saved["slug"]
    assert slug.startswith("lena-muster-")

    # season figures from her events, and a reel of her
    m = await new_match(api, ids)
    for outcome in ("goal", "goal", "save"):
        await api.post(
            f"/v1/orgs/{org}/matches/{m['id']}/events",
            json={"type": "shot", "side": "own", "outcome": outcome, "player_id": lena},
        )
    reel_id = uuid.uuid4()
    await owner_conn.execute(
        "INSERT INTO highlight_reels (id, organization_id, team_id, match_id, player_id, format, "
        "status, output_key, consent, clip_ids) VALUES ($1, $2::uuid, $3::uuid, $4::uuid, "
        "$5::uuid, '9x16', 'ready', 'reels/lena.mp4', '{}', '[]')",
        reel_id,
        org,
        team,
        m["id"],
        lena,
    )
    storage: MemoryStorage = api.app.state.storage
    await storage.put(
        api.app.state.settings.s3_bucket_artifacts, "reels/lena.mp4", b"MP4DATA", "video/mp4"
    )
    saved = (await api.put(url, json={**body, "reel_ids": [str(reel_id)]})).json()
    other_reel = await api.put(url, json={**body, "reel_ids": [str(uuid.uuid4())]})
    assert other_reel.status_code == 422

    anon = make_api()
    pub = await anon.get(f"/v1/public/profiles/{slug}")
    assert pub.status_code == 200 and pub.headers["x-robots-tag"].startswith("noindex")
    data = pub.json()
    assert (
        data["name"] == "Lena Muster" and data["club"] == "HC Test" and data["team"] == "Herren 1"
    )
    assert data["stats"] == {"goals": 2, "shooting_pct": 0.667}
    assert data["reels"] == [str(reel_id)]
    video = await anon.get(f"/v1/public/profiles/{slug}/reels/{reel_id}")
    assert video.status_code == 200 and video.content == b"MP4DATA"
    assert (await anon.get(f"/v1/public/profiles/{slug}/reels/{uuid.uuid4()}")).status_code == 404
    assert await owner_conn.fetchval("SELECT views FROM public_profiles") == 1
    indexable = await api.put(url, json={**body, "reel_ids": [str(reel_id)], "indexable": True})
    assert indexable.json()["indexable"]
    assert "x-robots-tag" not in (await anon.get(f"/v1/public/profiles/{slug}")).headers

    # the minor in an adult team: possible with the parent's consent (5.8)
    assert (
        await api.post(f"/v1/orgs/{org}/me/consents/{tim}", json={"kind": "public_profile"})
    ).status_code == 201
    assert (
        await api.put(f"/v1/orgs/{org}/players/{tim}/profile", json={"active": True})
    ).status_code == 200

    # revoking the consent takes the profile offline at once
    assert (
        await api.delete(f"/v1/orgs/{org}/me/consents/{lena}/public_profile")
    ).status_code == 204
    assert (await anon.get(f"/v1/public/profiles/{slug}")).status_code == 404
    assert (await anon.get(f"/v1/public/profiles/{slug}/reels/{reel_id}")).status_code == 404

    # nobody else manages the profile; deleting it removes the link
    other = make_api()
    await setup_club(other, email="other@hc-test.ch")
    assert (await other.put(url, json=body)).status_code in (403, 404)
    assert (await api.delete(url)).status_code == 204
    assert (
        await owner_conn.fetchval(
            "SELECT count(*) FROM public_profiles WHERE player_id = $1::uuid", lena
        )
        == 0
    )


async def test_youth_team_has_no_public_profile(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api, youth=True)
    org, team, season = ids["org"], ids["team"], ids["season"]
    ben = (
        await api.post(
            f"/v1/orgs/{org}/teams/{team}/seasons/{season}/roster",
            json={"first_name": "Ben", "last_name": "U15", "birth_year": 2012},
        )
    ).json()["player_id"]
    user_id = await owner_conn.fetchval("SELECT id FROM users LIMIT 1")
    await owner_conn.execute(
        "INSERT INTO guardianships (id, organization_id, user_id, player_id) "
        "VALUES (gen_random_uuid(), $1::uuid, $2, $3::uuid)",
        org,
        user_id,
        ben,
    )
    mine = (await api.get(f"/v1/orgs/{org}/me/profiles")).json()
    assert mine[0]["blocked"] == "youth-protection"
    r = await api.post(f"/v1/orgs/{org}/me/consents/{ben}", json={"kind": "public_profile"})
    assert r.status_code == 403
    r = await api.put(f"/v1/orgs/{org}/players/{ben}/profile", json={"active": True})
    assert r.status_code == 403 and r.json()["type"].endswith("youth-protection")
