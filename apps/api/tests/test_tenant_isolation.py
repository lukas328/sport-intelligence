"""Cross-tenant suite (ADR 005): API level and database level (RLS as second line of defence)."""

from __future__ import annotations

from collections.abc import Callable

import asyncpg
import pytest

from .conftest import APP_PASSWORD, Api, _dsn, setup_club

pytestmark = pytest.mark.usefixtures("clean_db")


async def test_api_cannot_reach_other_org(make_api: Callable[[], Api]) -> None:
    a, b = make_api(), make_api()
    ida = await setup_club(a, "a@hc-test.ch")
    idb = await setup_club(b, "b@hc-test.ch")
    await b.post(
        f"/v1/orgs/{idb['org']}/teams/{idb['team']}/seasons/{idb['season']}/roster",
        json={"first_name": "Secret", "last_name": "Player", "jersey_number": 1},
    )
    # A uses B's ids directly
    for url in (
        f"/v1/orgs/{idb['org']}",
        f"/v1/orgs/{idb['org']}/teams",
        f"/v1/orgs/{idb['org']}/teams/{idb['team']}/seasons/{idb['season']}/roster",
    ):
        assert (await a.get(url)).status_code == 404, url
    # A mixes its own org with B's team id
    r = await a.get(f"/v1/orgs/{ida['org']}/teams/{idb['team']}/seasons/{idb['season']}/roster")
    assert r.status_code == 404
    r = await a.post(
        f"/v1/orgs/{ida['org']}/teams/{idb['team']}/seasons/{idb['season']}/roster",
        json={"first_name": "X", "last_name": "Y"},
    )
    assert r.status_code == 404
    r = await a.patch(f"/v1/orgs/{ida['org']}/teams/{idb['team']}", json={"name": "pwned"})
    assert r.status_code == 404
    assert (await b.get(f"/v1/orgs/{idb['org']}/teams/{idb['team']}")).json()["name"] == "Herren 1"


async def test_rls_blocks_reads_and_writes_without_tenant(
    make_api: Callable[[], Api], test_db: str
) -> None:
    a, b = make_api(), make_api()
    ida = await setup_club(a, "a@hc-test.ch")
    idb = await setup_club(b, "b@hc-test.ch")
    conn = await asyncpg.connect(_dsn(test_db, "handball_app", APP_PASSWORD))
    try:
        # no tenant context: nothing visible
        assert await conn.fetchval("SELECT count(*) FROM teams") == 0
        assert await conn.fetchval("SELECT count(*) FROM organizations") == 0
        async with conn.transaction():
            await conn.execute("SELECT set_config('app.current_org', $1, true)", ida["org"])
            assert await conn.fetchval("SELECT count(*) FROM teams") == 1
            assert (
                await conn.fetchval(
                    "SELECT count(*) FROM teams WHERE organization_id = $1", idb["org"]
                )
                == 0
            )
            # updating B's rows silently affects nothing
            res = await conn.execute("UPDATE teams SET name = 'x' WHERE id = $1", idb["team"])
            assert res == "UPDATE 0"
            # inserting into B is rejected
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await conn.execute(
                    "INSERT INTO teams (id, organization_id, name, is_youth, gender, settings,"
                    " created_at, updated_at)"
                    " VALUES (gen_random_uuid(), $1, 'evil', false, 'men', '{}', now(), now())",
                    idb["org"],
                )
        # the app role cannot change or delete audit entries
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("DELETE FROM audit_logs")
    finally:
        await conn.close()


async def test_audit_log_written(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    actions = [
        r["action"]
        for r in await owner_conn.fetch("SELECT action FROM audit_logs ORDER BY created_at, action")
    ]
    assert {"user.registered", "org.created", "team.created"} <= set(actions)
    org_rows = await owner_conn.fetchval(
        "SELECT count(*) FROM audit_logs WHERE organization_id = $1", ids["org"]
    )
    assert org_rows >= 2


async def test_every_tenant_table_has_forced_rls(owner_conn: asyncpg.Connection) -> None:
    """Every table with organization_id is protected by a forced RLS policy (addendum 01, P7)."""
    rows = await owner_conn.fetch(
        """
        SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity,
               (SELECT count(*) FROM pg_policy p WHERE p.polrelid = c.oid) AS policies
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'public'
        WHERE c.relkind = 'r'
          AND EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid = c.oid
                      AND a.attname = 'organization_id' AND NOT a.attisdropped)
        """
    )
    assert len(rows) > 40
    bad = [r["relname"] for r in rows if not (r["relrowsecurity"] and r["relforcerowsecurity"])]
    bad += [r["relname"] for r in rows if r["policies"] == 0]
    assert not bad, bad
