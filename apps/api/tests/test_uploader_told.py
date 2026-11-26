"""Whoever uploads a video waits for its analysis and is told when it is done (the bell and a
mail), also without a role in the team as coach or analyst; once, while still in the club. The
uploader is kept with the video and set to NULL when the account goes. Invented club and people."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable

import asyncpg
import pytest

from handball_api.core.email import MemoryEmailSender

from .conftest import Api, setup_club
from .test_identity_sync import _finish, _tracks
from .test_matches import new_match, upload
from .test_training import add_member
from .test_video_parts import ANALYSIS, HALF, _ingest, _job_of

pytestmark = pytest.mark.usefixtures("clean_db")

DONE = re.compile(r"Muster gegen .* sind da|Analyse gegen .* fertig")


def _done_to(outbox: MemoryEmailSender, to: str) -> int:
    return sum(1 for m in outbox.outbox if m.to == to and DONE.search(m.subject))


async def _analysed_by_player(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> tuple[Api, Api, dict[str, str], str]:
    coach = make_api()
    ids = await setup_club(coach)
    lina = await add_member(
        make_api, coach, ids, outbox, "lina@hc-test.ch", "player", "Lina Muster"
    )
    m = await new_match(coach, ids)
    video = await upload(lina, ids, m["id"], b"a" * 100, name="spiel.mp4")
    await _ingest(coach, video["id"], HALF, "2026-11-07T18:00:00Z")
    return coach, lina, ids, video["id"]


async def test_the_uploader_is_told_once_besides_the_staff(
    make_api: Callable[[], Api], outbox: MemoryEmailSender, owner_conn: asyncpg.Connection
) -> None:
    coach, lina, ids, video = await _analysed_by_player(make_api, outbox)
    stored = await owner_conn.fetchval(
        "SELECT u.email FROM video_assets v JOIN users u ON u.id = v.uploaded_by_id "
        "WHERE v.id = $1",
        uuid.UUID(video),
    )
    assert stored == "lina@hc-test.ch"
    await _finish(coach, _job_of(coach, video, ANALYSIS)[0], {"tracks": _tracks()})
    assert _done_to(outbox, "lina@hc-test.ch") == 1  # the player who uploaded
    assert _done_to(outbox, "coach@hc-test.ch") == 1  # the coach, once
    bell = (await lina.get(f"/v1/orgs/{ids['org']}/me/notifications")).json()
    kinds = [n["kind"] for n in bell["items"]]
    assert any(k.startswith("analysis_") for k in kinds)


async def test_the_coach_who_uploads_hears_once(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    m = await new_match(coach, ids)
    video = await upload(coach, ids, m["id"], b"a" * 100, name="spiel.mp4")
    await _ingest(coach, video["id"], HALF, "2026-11-07T18:00:00Z")
    await _finish(coach, _job_of(coach, video["id"], ANALYSIS)[0], {"tracks": _tracks()})
    assert _done_to(outbox, "coach@hc-test.ch") == 1


async def test_an_uploader_who_left_the_club_is_not_told(
    make_api: Callable[[], Api], outbox: MemoryEmailSender, owner_conn: asyncpg.Connection
) -> None:
    coach, _, _, video = await _analysed_by_player(make_api, outbox)
    await owner_conn.execute(
        "DELETE FROM org_memberships WHERE user_id = (SELECT id FROM users WHERE email = $1)",
        "lina@hc-test.ch",
    )
    await owner_conn.execute(
        "DELETE FROM memberships WHERE user_id = (SELECT id FROM users WHERE email = $1)",
        "lina@hc-test.ch",
    )
    await _finish(coach, _job_of(coach, video, ANALYSIS)[0], {"tracks": _tracks()})
    assert _done_to(outbox, "lina@hc-test.ch") == 0
    assert _done_to(outbox, "coach@hc-test.ch") == 1


async def test_the_uploader_goes_with_the_account(
    make_api: Callable[[], Api], outbox: MemoryEmailSender, owner_conn: asyncpg.Connection
) -> None:
    _, lina, _, video = await _analysed_by_player(make_api, outbox)
    r = await lina.post(
        "/v1/me/delete", json={"confirm_email": "lina@hc-test.ch", "password": "correct-horse-1"}
    )
    assert r.status_code == 204
    left = await owner_conn.fetchval(
        "SELECT uploaded_by_id FROM video_assets WHERE id = $1", uuid.UUID(video)
    )
    assert left is None
