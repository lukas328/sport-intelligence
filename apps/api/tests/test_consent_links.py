from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .conftest import Api, setup_club


async def roster(api: Api, ids: dict[str, Any], first: str, last: str, n: int, born: int) -> str:
    r = await api.post(
        f"/v1/orgs/{ids['org']}/teams/{ids['team']}/seasons/{ids['season']}/roster",
        json={"first_name": first, "last_name": last, "jersey_number": n, "birth_year": born},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["player_id"])


async def test_consent_without_an_account(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org, team = ids["org"], ids["team"]
    adult = await roster(api, ids, "Lena", "Brunner", 7, 1998)
    minor = await roster(api, ids, "Noah", "Keller", 11, 2012)
    base = f"/v1/orgs/{org}/teams/{team}/consent-link"
    assert (await api.get(base)).json() is None
    created = await api.post(base)
    assert created.status_code == 201, created.text
    token = created.json()["token"]

    anon = make_api()
    page = (await anon.get(f"/v1/consent/{token}")).json()
    assert (page["club"], page["team"], page["youth"]) == ("HC Test", "Herren 1", False)
    assert page["purposes"] == ["analysis", "highlights_internal", "highlights_public"]
    # first name, initial, number; no last name on a public page
    assert [p["label"] for p in page["players"]] == ["#7 Lena B.", "#11 Noah K."]
    assert "Brunner" not in str(page)

    url = f"/v1/consent/{token}"
    ok = await anon.post(
        url,
        json={
            "player_id": adult,
            "given_by": "self",
            "given_by_name": "Lena Brunner",
            "agreed": ["analysis", "highlights_internal"],
        },
    )
    assert ok.status_code == 200, ok.text
    # a minor needs a parent or guardian
    child = {"player_id": minor, "given_by_name": "Noah Keller", "agreed": ["analysis"]}
    refused = await anon.post(url, json={**child, "given_by": "self"})
    assert refused.status_code == 422
    parent = await anon.post(
        url, json={**child, "given_by": "parent", "given_by_name": "Sandra Keller"}
    )
    assert parent.status_code == 200, parent.text

    consents = (await api.get(f"/v1/orgs/{org}/teams/{team}/players/{adult}/consents")).json()
    assert {c["kind"] for c in consents if c["revoked_at"] is None} == {
        "analysis",
        "highlights_internal",
    }
    # answering again without a purpose withdraws it; the history stays
    await anon.post(
        url,
        json={
            "player_id": adult,
            "given_by": "self",
            "given_by_name": "Lena Brunner",
            "agreed": ["analysis"],
        },
    )
    consents = (await api.get(f"/v1/orgs/{org}/teams/{team}/players/{adult}/consents")).json()
    assert {c["kind"] for c in consents if c["revoked_at"] is None} == {"analysis"}
    assert len(consents) == 2
    assert (await api.get(base)).json()["answers"] == 4 - 1  # the refused one did not count

    # a new link replaces the old one; revoking ends it
    new = (await api.post(base)).json()["token"]
    assert (await anon.get(f"/v1/consent/{token}")).status_code == 404
    await api.delete(base)
    assert (await anon.get(f"/v1/consent/{new}")).status_code == 404


async def test_youth_teams_are_not_asked_for_public_purposes(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api, youth=True)
    kid = await roster(api, ids, "Mia", "Frei", 4, 2011)
    token = (await api.post(f"/v1/orgs/{ids['org']}/teams/{ids['team']}/consent-link")).json()[
        "token"
    ]
    anon = make_api()
    assert (await anon.get(f"/v1/consent/{token}")).json()["purposes"] == [
        "analysis",
        "highlights_internal",
    ]
    r = await anon.post(
        f"/v1/consent/{token}",
        json={
            "player_id": kid,
            "given_by": "parent",
            "given_by_name": "Eva Frei",
            "agreed": ["highlights_public"],
        },
    )
    assert r.status_code == 403
