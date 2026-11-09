from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from handball_api.core.config import Settings
from handball_api.core.email import EmailSender
from handball_api.core.jobs import EventBus, JobQueue
from handball_api.core.storage import ObjectStorage
from handball_api.core.text import TextGenerator
from handball_api.services.policies import Actor, TwoFactorPolicy


@dataclass
class Ctx:
    """Everything a service needs for one request. Built by router dependencies."""

    db: AsyncSession
    settings: Settings
    email: EmailSender
    storage: ObjectStorage
    jobs: JobQueue | None = None
    events: EventBus | None = None
    text: TextGenerator | None = None
    ip: str | None = None
    user_id: uuid.UUID | None = None
    actor: Actor | None = None

    @property
    def two_factor(self) -> TwoFactorPolicy:
        return TwoFactorPolicy(
            self.settings.org_admin_2fa_required, self.settings.org_admin_2fa_grace_days
        )

    def require_jobs(self) -> JobQueue:
        if self.jobs is None:
            raise RuntimeError("job queue missing")
        return self.jobs

    async def enqueue(
        self,
        queue: str,
        func: str,
        job_id: str,
        kwargs: dict[str, Any],
        timeout_s: int | None = None,
    ) -> None:
        """Enqueue a worker job without blocking the event loop (the RQ client is synchronous)."""
        await asyncio.to_thread(self.require_jobs().enqueue, queue, func, job_id, kwargs, timeout_s)

    def require_events(self) -> EventBus:
        if self.events is None:
            raise RuntimeError("event bus missing")
        return self.events

    def require_actor(self) -> Actor:
        if self.actor is None:
            raise RuntimeError("organisation context missing")
        return self.actor
