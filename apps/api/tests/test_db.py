from __future__ import annotations

from collections.abc import AsyncIterator, MutableMapping
from typing import Any

import pytest
from fastapi import FastAPI
from sqlalchemy.orm import Mapped, mapped_column

from handball_api.core import db
from handball_api.routers.deps import DbDep


class _Thing(db.Base, db.EntityMixin, db.TenantMixin):
    __tablename__ = "_thing_test"
    name: Mapped[str] = mapped_column()


def test_entity_columns() -> None:
    cols = set(_Thing.__table__.columns.keys())
    assert {"id", "created_at", "updated_at", "organization_id", "name"} <= cols
    assert _Thing.__table__.primary_key.name == "pk__thing_test"  # type: ignore[attr-defined]


async def test_engine_lifecycle() -> None:
    with pytest.raises(RuntimeError):
        db.get_engine()
    engine = db.init_engine("postgresql+asyncpg://x:y@127.0.0.1:1/z")
    assert db.get_engine() is engine
    gen = db.get_session()
    session = await anext(gen)
    assert session is not None
    await gen.aclose()  # type: ignore[attr-defined]
    await db.dispose_engine()
    with pytest.raises(RuntimeError):
        db.get_engine()
    with pytest.raises(RuntimeError):
        await anext(db.get_session())


async def test_connections_carry_the_process_name(db_settings: Any) -> None:
    """pg_stat_activity tells whose connections fill the server's slots (staging 17.11.)."""
    name = db.application_name()
    assert name.startswith("hb-api ") and len(name) <= 63
    engine = db.init_engine(db_settings.database_url)
    try:
        async with engine.connect() as conn:
            shown = (
                await conn.exec_driver_sql("SELECT current_setting('application_name')")
            ).scalar()
        assert shown == name
    finally:
        await db.dispose_engine()


# foreign keys whose referenced row is deleted (ON DELETE) or that are looked up: each needs an
# index starting with the column, or the delete and the lookup read the whole table
_UNINDEXED_FKS = """
SELECT c.conrelid::regclass::text, a.attname
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
WHERE c.contype = 'f' AND array_length(c.conkey, 1) = 1
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i WHERE i.indrelid = c.conrelid AND i.indkey[0] = c.conkey[1]
  )
"""


async def test_foreign_keys_of_official_data_and_candidates_are_indexed(owner_conn: Any) -> None:
    missing = {(t, c) for t, c in await owner_conn.fetch(_UNINDEXED_FKS)}
    checked = {
        "goal_candidates",
        "join_requests",
        "org_access_requests",
        "official_suggestions",
        "player_statuses",
        "training_slots",
        "training_sessions",
        "club_drills",
    }
    assert {(t, c) for t, c in missing if t in checked} == set()
    assert ("organizations", "claimed_by_id") not in missing


# every table a match deletion reaches through ON DELETE CASCADE, and the foreign keys the
# database then follows (CASCADE or SET NULL)
_MATCH_CASCADE = """
WITH RECURSIVE fk AS (
  SELECT c.conrelid::regclass::text AS child, c.confrelid::regclass::text AS parent,
         a.attname AS col, c.confdeltype AS del,
         EXISTS (SELECT 1 FROM pg_index i
                 WHERE i.indrelid = c.conrelid AND i.indkey[0] = c.conkey[1]) AS indexed
  FROM pg_constraint c
  JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
  WHERE c.contype = 'f' AND array_length(c.conkey, 1) = 1
), tree AS (
  SELECT child, parent, col, del, indexed, 1 AS depth FROM fk WHERE parent = 'matches'
  UNION
  SELECT f.child, f.parent, f.col, f.del, f.indexed, t.depth + 1
  FROM fk f JOIN tree t ON f.parent = t.child AND t.del = 'c' WHERE t.depth < 5
)
SELECT DISTINCT child, col FROM tree WHERE del IN ('c', 'n') AND NOT indexed
"""


async def test_deleting_a_match_follows_only_indexed_foreign_keys(owner_conn: Any) -> None:
    """Deleting a match removes its clips, events, videos ... in one statement; for every row
    removed the database looks up the rows pointing at it. Without an index each lookup reads
    the whole table, and a big match (hundreds of clips and events) held its locks for long."""
    assert {(t, c) for t, c in await owner_conn.fetch(_MATCH_CASCADE)} == set()


async def test_request_transaction_commits_before_the_response_is_sent() -> None:
    """The browser often reads right after a write: the commit must happen before the
    response starts, not after it was sent (default scope of yield dependencies)."""
    order: list[str] = []

    async def fake_session() -> AsyncIterator[object]:
        yield object()
        order.append("commit")

    app = FastAPI()

    @app.post("/write")
    async def write(session: DbDep) -> dict[str, bool]:
        order.append("endpoint")
        return {"ok": True}

    app.dependency_overrides[db.get_session] = fake_session

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: MutableMapping[str, Any]) -> None:
        if message["type"] == "http.response.start":
            order.append("response")

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "path": "/write",
        "raw_path": b"/write",
        "query_string": b"",
        "headers": [],
        "scheme": "http",
        "server": ("test", 80),
        "client": ("test", 1),
        "root_path": "",
    }
    await app(scope, receive, send)
    assert order == ["endpoint", "commit", "response"]
