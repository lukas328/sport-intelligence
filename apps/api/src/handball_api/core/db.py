from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, MetaData, func, text
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


def init_engine(database_url: str) -> AsyncEngine:
    global _engine, _sessionmaker
    _engine = create_async_engine(database_url, pool_pre_ping=True, pool_size=10)
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


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
