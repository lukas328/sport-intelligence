from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.orm import Mapped, mapped_column

from handball_api.core import db


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
    checked = {"goal_candidates", "join_requests", "org_access_requests", "official_suggestions"}
    assert {(t, c) for t, c in missing if t in checked} == set()
    assert ("organizations", "claimed_by_id") not in missing
