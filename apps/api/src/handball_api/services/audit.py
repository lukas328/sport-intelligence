from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import insert

from handball_api.models import AuditLog
from handball_api.services.context import Ctx


async def record(
    ctx: Ctx,
    action: str,
    *,
    org_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    data: dict[str, Any] | None = None,
    actor_id: uuid.UUID | None = None,
) -> None:
    """Append an audit entry. Plain INSERT without RETURNING: the app role may append to
    audit_logs but only read entries of the current organisation (RLS)."""
    await ctx.db.execute(
        insert(AuditLog).values(
            id=uuid.uuid4(),
            organization_id=org_id or (ctx.actor.organization_id if ctx.actor else None),
            actor_user_id=actor_id or ctx.user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            data=data or {},
            ip=ctx.ip,
        )
    )
