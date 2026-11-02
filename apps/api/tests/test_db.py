from __future__ import annotations

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
