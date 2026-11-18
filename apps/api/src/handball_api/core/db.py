from __future__ import annotations

import os
import socket
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

import asyncpg
from sqlalchemy import DateTime, ForeignKey, MetaData, func, text
from sqlalchemy import exc as sa_exc
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class EntityMixin:
    """Every entity: UUID id, created_at, updated_at (BRIEF 5)."""

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TenantMixin:
    """Tenant-scoped entities carry organization_id; Postgres RLS uses it (ADR 005).

    Deleting an organisation cascades to all its tenant rows (BRIEF 12, deletion).
    """

    @declared_attr
    def organization_id(cls) -> Mapped[uuid.UUID]:  # noqa: N805
        return mapped_column(
            UUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        )


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def application_name() -> str:
    """Who holds a connection, as Postgres shows it (pg_stat_activity.application_name): the API
    process by replica and pid. Staging 17.11.: too many connections while the API ran on two
    replicas, and nothing told whose connections filled the slots."""
    return f"hb-api {socket.gethostname()} {os.getpid()}"[:63]


def init_engine(
    database_url: str, pool_size: int = 5, max_overflow: int = 5, pool_timeout_s: float = 10.0
) -> AsyncEngine:
    global _engine, _sessionmaker
    _engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout_s,
        connect_args={"server_settings": {"application_name": application_name()}},
    )
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


# The server refuses or drops the connection: too many connections (class 53), connection
# failure (class 08), shutting down or starting (57P01 to 57P03), the network.
_UNREACHABLE: tuple[type[BaseException], ...] = (
    asyncpg.exceptions.InsufficientResourcesError,
    asyncpg.exceptions.PostgresConnectionError,
    asyncpg.exceptions.AdminShutdownError,
    asyncpg.exceptions.CrashShutdownError,
    asyncpg.exceptions.CannotConnectNowError,
    OSError,
    TimeoutError,
)


# Two transactions waiting on each other (40P01) or a serialization failure (40001): the
# transaction is rolled back, and the same work done again a moment later usually succeeds.
_CONFLICT_STATES = ("40P01", "40001")
# A lock not granted within lock_timeout (55P03): only where a statement asked for a short wait.
_LOCK_STATES = (*_CONFLICT_STATES, "55P03")


def _sqlstate(exc: BaseException) -> str | None:
    cause: BaseException | None = exc.orig if isinstance(exc, sa_exc.DBAPIError) else exc
    for _ in range(4):  # the adapter's error, then asyncpg's beneath it
        if cause is None:
            return None
        state = getattr(cause, "sqlstate", None) or getattr(cause, "pgcode", None)
        if isinstance(state, str):
            return state
        cause = cause.__cause__
    return None


def transaction_conflict(exc: BaseException) -> bool:
    """True for a deadlock or serialization failure: no fault of the request, worth retrying."""
    return _sqlstate(exc) in _CONFLICT_STATES


def lock_contended(exc: BaseException) -> bool:
    """A conflict as above, or a lock not granted within a short lock_timeout."""
    return _sqlstate(exc) in _LOCK_STATES


def database_unavailable(exc: BaseException) -> bool:
    """True when a request failed because the database could not be reached (no free connection
    in the pool, the server refusing one, the connection lost), not because of the request."""
    if isinstance(exc, sa_exc.TimeoutError):  # the pool stayed full for pool_timeout
        return True
    if isinstance(exc, ConnectionError | socket.gaierror):  # connecting failed outright
        return True
    if not isinstance(exc, sa_exc.DBAPIError):
        return False
    if exc.connection_invalidated:
        return True
    cause: BaseException | None = exc.orig
    for _ in range(4):  # the driver's error, then asyncpg's beneath the adapter
        if cause is None:
            return False
        if isinstance(cause, _UNREACHABLE):
            return True
        cause = cause.__cause__
    return False


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("database engine not initialised")
    return _engine


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None


async def get_session() -> AsyncIterator[AsyncSession]:
    """Request-scoped session in one transaction: commit on success, rollback on error.

    Tenant context is transaction-local (``set_config(..., true)``), so it can never leak to
    another request through the connection pool.
    """
    if _sessionmaker is None:
        raise RuntimeError("database engine not initialised")
    async with _sessionmaker() as session, session.begin():
        yield session


@asynccontextmanager
async def open_session() -> AsyncIterator[AsyncSession]:
    """Short-lived session outside the request scope (e.g. before a long SSE stream)."""
    if _sessionmaker is None:
        raise RuntimeError("database engine not initialised")
    async with _sessionmaker() as session, session.begin():
        yield session


async def set_tenant(session: AsyncSession, organization_id: uuid.UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.current_org', :v, true)"), {"v": str(organization_id)}
    )


async def set_current_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.current_user', :v, true)"), {"v": str(user_id)}
    )


async def enable_system_access(session: AsyncSession, reason: str) -> None:
    """Explicit RLS bypass for system paths (org creation, invitation lookup by token).

    Every call site names a reason; it is logged by the caller via the audit log where relevant.
    """
    if not reason:
        raise ValueError("system access requires a reason")
    await session.execute(text("SELECT set_config('app.bypass_rls', 'on', true)"))


async def disable_system_access(session: AsyncSession) -> None:
    await session.execute(text("SELECT set_config('app.bypass_rls', 'off', true)"))
