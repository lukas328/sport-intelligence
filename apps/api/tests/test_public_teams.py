"""The public entry (UX test, second delivery): team search and preview without an account, the
passwordless start. handball.ch answers come from the recorded fixtures of test_official."""

from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import unquote

import asyncpg
import pytest

from handball_api.core.email import MemoryEmailSender
from handball_api.core.ratelimit import MemoryRateLimiter

from .conftest import Api
from .test_official import CLUB, TEAM, claim, coach, hch  # noqa: F401  (fixture)

pytestmark = pytest.mark.usefixtures("clean_db")


async def test_public_search_needs_no_account_and_shows_no_app_data(
    make_api: Callable[[], Api],
) -> None:
    anon = make_api()
    anon.app.state.rate_limiter = MemoryRateLimiter()
    r = await anon.get("/v1/public/teams", params={"q": "thalwil"})
    assert r.status_code == 200, r.text
    first = next(h for h in r.json() if h["official_id"] == TEAM)
    assert first["club"] == {"id": CLUB, "name": "TV Thalwil", "city": "Thalwil"}
    # only the federation's data and whether the team is in the app: no ids of the app
    assert set(first) == {"official_id", "name", "league", "group_name", "club", "in_app"}
    assert first["in_app"] is False
    r = await anon.get("/v1/public/teams", params={"q": "th"})
    assert r.status_code == 422


async def test_public_search_says_when_a_team_is_in_the_app(make_api: Callable[[], Api]) -> None:
    api = await coach(make_api)
    await claim(api)
    anon = make_api()
    anon.app.state.rate_limiter = MemoryRateLimiter()
    hit = next(
        h
        for h in (await anon.get("/v1/public/teams", params={"q": "thalwil"})).json()
        if h["official_id"] == TEAM
    )
    assert hit["in_app"] is True and "team_id" not in hit and "organization_id" not in hit


async def test_public_preview_from_the_federations_data(make_api: Callable[[], Api]) -> None:
    anon = make_api()
    anon.app.state.rate_limiter = MemoryRateLimiter()
    r = await anon.get(f"/v1/public/clubs/{CLUB}/teams/{TEAM}")
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["name"] == "TV Thalwil" and p["club"]["name"] == "TV Thalwil"
    assert p["played"] > 0 and p["last"] is not None
    assert p["rank"] is not None and any(row["own"] for row in p["table"])
    assert all(set(s) == {"name", "goals"} for s in p["scorers"])
    assert len(p["form"]) <= 5
    assert (await anon.get(f"/v1/public/clubs/{CLUB}/teams/1")).status_code == 404


async def test_public_endpoints_are_limited_per_ip(make_api: Callable[[], Api]) -> None:
    anon = make_api()
    anon.app.state.rate_limiter = MemoryRateLimiter()
    codes = [
        (await anon.get(f"/v1/public/clubs/{CLUB}/teams/{TEAM}")).status_code for _ in range(12)
    ]
    assert codes[:10] == [200] * 10 and codes[-1] == 429


async def test_start_makes_an_account_without_password_and_mails_a_link(
    make_api: Callable[[], Api], outbox: MemoryEmailSender, owner_conn: asyncpg.Connection
) -> None:
    anon = make_api()
    anon.app.state.rate_limiter = MemoryRateLimiter()
    nxt = f"/einstieg/speichern?club={CLUB}&team={TEAM}&farbe=rot"
    r = await anon.post(
        "/v1/auth/start", json={"email": "hans@example.org", "locale": "de-CH", "next": nxt}
    )
    assert r.status_code == 202, r.text
    row = await owner_conn.fetchrow(
        "SELECT password_hash, terms_accepted_at FROM users WHERE email = 'hans@example.org'"
    )
    assert row["password_hash"] is None and row["terms_accepted_at"] is not None
    link = re.search(r"/auth/magic\?token=([\w-]+)&next=(\S+)", outbox.outbox[-1].text)
    assert link and unquote(link.group(2)) == nxt
    # the link signs in
    r = await anon.post("/v1/auth/magic-link/consume", json={"token": link.group(1)})
    assert r.status_code == 200, r.text
    assert (await anon.get("/v1/me")).json()["email"] == "hans@example.org"
    # an address that has an account gets a link too, nothing else changes
    r = await anon.post("/v1/auth/start", json={"email": "hans@example.org"})
    assert r.status_code == 202
    # a path to another site is refused
    r = await anon.post("/v1/auth/start", json={"email": "x@example.org", "next": "//evil.test"})
    assert r.status_code == 422


def test_scorer_names_in_reading_order() -> None:
    from handball_api.services.public_teams import display_name

    assert display_name("KRAUSE Liam") == "Liam Krause"
    assert display_name("SIGG Jean-Claude") == "Jean-Claude Sigg"
    assert display_name("MÜLLER-HUBER Tim") == "Tim Müller-Huber"
    assert display_name("Anna Muster") == "Anna Muster"


async def test_public_config_gives_the_website_and_support_addresses(
    make_api: Callable[[], Api],
) -> None:
    """The upload guide and the legal links take the website's address from the configuration."""
    r = await make_api().get("/v1/public/config")
    assert r.status_code == 200
    assert r.json() == {
        "site_url": "https://handball-ai.ch",
        "support_email": "support@handball-ai.ch",
    }
