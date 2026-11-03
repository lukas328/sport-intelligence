"""From a problem to training (addendum 01, 5.6)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter

from handball_api.models import FocusPlan
from handball_api.routers.deps import OrgDep
from handball_api.schemas.focus import FocusIn, FocusOut
from handball_api.services import focus as service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["training"])


def _out(p: FocusPlan, followup: dict[str, Any] | None = None) -> FocusOut:
    data = FocusOut.model_validate(p, from_attributes=True).model_dump()
    data["followup"] = followup
    return FocusOut.model_validate(data)


@router.post("/matches/{match_id}/focus", response_model=FocusOut, status_code=201)
async def create(match_id: uuid.UUID, body: FocusIn, scope: OrgDep) -> FocusOut:
    """Turns an insight into a session, an evidence playlist and optionally an assignment."""
    return _out(await service.create(scope.ctx, match_id, body))


@router.get("/teams/{team_id}/focus", response_model=list[FocusOut])
async def plans(team_id: uuid.UUID, scope: OrgDep) -> list[FocusOut]:
    """Training foci with before/after of their metric (observation, not proof)."""
    return [_out(x["plan"], x["followup"]) for x in await service.plans(scope.ctx, team_id)]


@router.post("/focus/{plan_id}/close", response_model=FocusOut)
async def close(plan_id: uuid.UUID, scope: OrgDep) -> FocusOut:
    return _out(await service.close(scope.ctx, plan_id))
