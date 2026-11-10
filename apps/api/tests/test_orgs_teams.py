from __future__ import annotations

from collections.abc import Callable

import pytest

from .conftest import Api, setup_club

pytestmark = pytest.mark.usefixtures("clean_db")

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


async def test_create_org_makes_creator_admin(make_api: Callable[[], Api]) -> None:
    api = make_api()
    await api.register("admin@hc-test.ch")
    r = await api.post("/v1/orgs", json={"name": "  HC Wädenswil ", "primary_color": "#AABBCC"})
    assert r.status_code == 201
    org = r.json()
    assert org["name"] == "HC Wädenswil"
    assert org["primary_color"] == "#aabbcc"
    assert org["my_role"] == "org_admin"
    assert org["plan"] == "free"
    assert org["data_region"] == "ch"
    me = (await api.get("/v1/me")).json()
    assert me["organizations"] == [{"id": org["id"], "name": "HC Wädenswil", "role": "org_admin"}]


async def test_org_validation(make_api: Callable[[], Api]) -> None:
    api = make_api()
    await api.register("v@hc-test.ch")
    assert (
        await api.post("/v1/orgs", json={"name": "X", "primary_color": "red"})
    ).status_code == 422
    assert (await api.post("/v1/orgs", json={"name": ""})).status_code == 422


async def test_club_colours(make_api: Callable[[], Api]) -> None:
    """The club's first and second colour (the kit; the opponent's colours are per match)."""
    api = make_api()
    ids = await setup_club(api)
    org = f"/v1/orgs/{ids['org']}"
    r = await api.patch(org, json={"primary_color": "#c8102e", "secondary_color": "#ffffff"})
    assert r.status_code == 200, r.text
    assert (r.json()["primary_color"], r.json()["secondary_color"]) == ("#c8102e", "#ffffff")
    assert (await api.patch(org, json={"secondary_color": "white"})).status_code == 422


async def test_update_org_and_logo(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    r = await api.patch(f"/v1/orgs/{org}", json={"name": "HC Neu"})
    assert r.json()["name"] == "HC Neu"
    assert (await api.get(f"/v1/orgs/{org}/logo")).status_code == 404
    bad = await api.put(
        f"/v1/orgs/{org}/logo", files={"file": ("x.svg", b"<svg/>", "image/svg+xml")}
    )
    assert bad.status_code == 415
    big = await api.put(
        f"/v1/orgs/{org}/logo", files={"file": ("x.png", PNG + b"0" * 1_000_001, "image/png")}
    )
    assert big.status_code == 413
    ok = await api.put(f"/v1/orgs/{org}/logo", files={"file": ("x.png", PNG, "image/png")})
    assert ok.json()["has_logo"] is True
    logo = await api.get(f"/v1/orgs/{org}/logo")
    assert logo.headers["content-type"] == "image/png"
    assert logo.content == PNG
    # replacing deletes the old object
    await api.put(f"/v1/orgs/{org}/logo", files={"file": ("y.png", PNG + b"1", "image/png")})
    assert len(api.app.state.storage.objects) == 1


async def test_team_creation_defaults(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    team = ids["team_obj"]
    assert team["my_role"] == "coach"
    assert team["settings"] == {"players_see_team_stats": True, "team_features": False}
    assert team["current_season"]["label"].count("/") == 1
    youth = (
        await api.post(
            f"/v1/orgs/{ids['org']}/teams",
            json={"name": "U15", "gender": "mixed", "is_youth": True, "join_as_coach": False},
        )
    ).json()
    assert youth["settings"] == {"players_see_team_stats": False, "team_features": False}
    assert youth["my_role"] is None
    teams = (await api.get(f"/v1/orgs/{ids['org']}/teams")).json()
    assert [t["name"] for t in teams] == ["Herren 1", "U15"]


async def test_team_list_has_constant_query_count(
    make_api: Callable[[], Api], query_counter: list[str]
) -> None:
    api = make_api()
    ids = await setup_club(api)
    query_counter.clear()
    await api.get(f"/v1/orgs/{ids['org']}/teams")
    one = len(query_counter)
    for i in range(4):
        await api.post(f"/v1/orgs/{ids['org']}/teams", json={"name": f"T{i}", "gender": "women"})
    query_counter.clear()
    assert len((await api.get(f"/v1/orgs/{ids['org']}/teams")).json()) == 5
    assert len(query_counter) == one


async def test_update_and_delete_team(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    base = f"/v1/orgs/{ids['org']}/teams/{ids['team']}"
    r = await api.patch(
        base, json={"league": "3. Liga", "settings": {"players_see_team_stats": False}}
    )
    assert r.json()["league"] == "3. Liga"
    assert r.json()["settings"]["players_see_team_stats"] is False
    assert (await api.delete(base)).status_code == 204
    assert (await api.get(base)).status_code == 404


async def test_team_features_setting(make_api: Callable[[], Api]) -> None:
    """'Teamfunktionen' is off by default, also for teams stored before the setting existed, and
    switching it leaves the other settings alone."""
    api = make_api()
    ids = await setup_club(api)
    base = f"/v1/orgs/{ids['org']}/teams/{ids['team']}"
    assert (await api.get(base)).json()["settings"]["team_features"] is False
    r = await api.patch(base, json={"settings": {"team_features": True}})
    assert r.status_code == 200, r.text
    assert r.json()["settings"] == {"players_see_team_stats": True, "team_features": True}
    r = await api.patch(base, json={"settings": {"players_see_team_stats": False}})
    assert r.json()["settings"] == {"players_see_team_stats": False, "team_features": True}
    r = await api.patch(base, json={"settings": {"team_features": False}})
    assert r.json()["settings"]["team_features"] is False


def test_team_features_default_for_existing_teams() -> None:
    from handball_api.models.tenancy import Team

    assert Team(settings={"players_see_team_stats": True}).team_features is False
    assert Team(settings={"team_features": True}).team_features is True


async def test_seasons(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    base = f"/v1/orgs/{ids['org']}/teams/{ids['team']}/seasons"
    r = await api.post(
        base, json={"label": "2030/31", "starts_on": "2030-07-01", "ends_on": "2031-06-30"}
    )
    assert r.status_code == 201
    dup = await api.post(
        base, json={"label": "2030/31", "starts_on": "2030-07-01", "ends_on": "2031-06-30"}
    )
    assert dup.status_code == 409
    bad = await api.post(
        base, json={"label": "x", "starts_on": "2030-07-01", "ends_on": "2030-01-01"}
    )
    assert bad.status_code == 422
    assert len((await api.get(base)).json()) == 2


async def test_org_members(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    members = (await api.get(f"/v1/orgs/{ids['org']}/members")).json()
    assert members[0]["org_role"] == "org_admin"
    assert members[0]["team_roles"] == {ids["team"]: "coach"}


async def test_two_factor_required_after_grace(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    settings = api.app.state.settings
    settings.org_admin_2fa_grace_days = -1
    try:
        r = await api.patch(f"/v1/orgs/{ids['org']}", json={"name": "Y"})
        assert r.status_code == 403
        assert r.json()["type"].endswith(":two-factor-required")
        assert (await api.get(f"/v1/orgs/{ids['org']}")).json()["two_factor_required"] is True
        # reading is still allowed
        assert (await api.get(f"/v1/orgs/{ids['org']}/teams")).status_code == 200
    finally:
        settings.org_admin_2fa_grace_days = 14
