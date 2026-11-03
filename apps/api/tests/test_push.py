"""Push tokens and push jobs for the native apps (addendum 01, 5.5)."""

from __future__ import annotations

from collections.abc import Callable

import asyncpg
import pytest

from handball_api.core.db import enable_system_access, open_session
from handball_api.core.jobs import MemoryJobQueue
from handball_api.services import training
from handball_api.services.context import Ctx

from .conftest import Api, setup_club

pytestmark = pytest.mark.usefixtures("clean_db")


async def test_devices_and_push_jobs(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    assert (
        await api.post("/v1/me/devices", json={"token": "nope-token-x", "platform": "ios"})
    ).status_code == 422
    token = "ExponentPushToken[abc123]"
    assert (
        await api.post("/v1/me/devices", json={"token": token, "platform": "ios"})
    ).status_code == 204
    assert (
        await api.post("/v1/me/devices", json={"token": token, "platform": "ios"})
    ).status_code == 204
    assert await owner_conn.fetchval("SELECT count(*) FROM device_tokens") == 1

    # an assignment to the coach (as a player account) notifies and queues a push
    jobs: MemoryJobQueue = api.app.state.jobs
    before = len(jobs.jobs)
    user_id = await owner_conn.fetchval("SELECT id FROM users LIMIT 1")

    async with open_session() as db:
        ctx = Ctx(
            db=db,
            settings=api.app.state.settings,
            email=api.app.state.email,
            storage=api.app.state.storage,
            jobs=jobs,
        )
        await enable_system_access(db, reason="test")
        await training.notify(
            ctx, __import__("uuid").UUID(org), [user_id], "assignment", {}, f"/app/{org}"
        )
        await db.commit()
    push_jobs = [j for j in jobs.jobs[before:] if j[1] == "handball_worker.push.send"]
    assert len(push_jobs) == 1
    payload = push_jobs[0][3]["payload"]
    assert payload["tokens"] == [token] and payload["body"] == "Neue Aufgabe vom Trainerteam"
    assert payload["data"] == {"kind": "assignment", "link": f"/app/{org}"}

    # signing out on the phone removes the token
    assert (await api.delete(f"/v1/me/devices/{token}")).status_code == 204
    assert await owner_conn.fetchval("SELECT count(*) FROM device_tokens") == 0
