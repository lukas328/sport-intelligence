"""Which database errors count as a conflict worth retrying (deadlock, serialization) or as a
lock not granted in time."""

from __future__ import annotations

from sqlalchemy.exc import DBAPIError

from handball_api.core.db import database_unavailable, lock_contended, transaction_conflict


class _PgError(Exception):
    def __init__(self, sqlstate: str) -> None:
        super().__init__(sqlstate)
        self.sqlstate = sqlstate


def _wrapped(sqlstate: str) -> DBAPIError:
    """As SQLAlchemy raises it: the adapter's error whose cause is asyncpg's."""
    adapter = Exception("deadlock detected")
    adapter.__cause__ = _PgError(sqlstate)
    return DBAPIError("DELETE FROM stats_cache", {}, adapter)


def test_deadlock_and_serialization_are_conflicts() -> None:
    for state in ("40P01", "40001"):
        assert transaction_conflict(_wrapped(state))
        assert lock_contended(_wrapped(state))
        assert not database_unavailable(_wrapped(state))


def test_a_lock_timeout_is_contended_but_no_conflict() -> None:
    assert lock_contended(_wrapped("55P03"))
    assert not transaction_conflict(_wrapped("55P03"))


def test_other_errors_are_neither() -> None:
    for exc in (_wrapped("23505"), _wrapped("42P01"), ValueError("x")):
        assert not transaction_conflict(exc)
        assert not lock_contended(exc)
