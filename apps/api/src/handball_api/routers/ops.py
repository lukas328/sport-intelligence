from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import Field

from handball_api.core.errors import ProblemError
from handball_api.models.enums import Plan
from handball_api.routers.deps import Authed, AuthedDep
from handball_api.schemas.common import ApiModel
from handball_api.services import ops as service


async def operator(auth: AuthedDep) -> Authed:
    if not service.is_operator(auth.ctx, auth.user):
        raise ProblemError(404, "not-found", "Not found")  # the backoffice is invisible to others
    return auth


OperatorDep = Annotated[Authed, Depends(operator)]
router = APIRouter(prefix="/v1/ops", tags=["ops"])


class TrialIn(ApiModel):
    plan: Plan
    days: int = Field(ge=1, le=90)


@router.get("/me", response_model=dict[str, bool])
async def me(op: OperatorDep) -> dict[str, bool]:
    return {"operator": True}


@router.get("/overview", response_model=dict[str, Any])
async def overview(op: OperatorDep) -> dict[str, Any]:
    return await service.overview(op.ctx)


@router.get("/organizations", response_model=list[dict[str, Any]])
async def organizations(
    op: OperatorDep, q: Annotated[str | None, Query(max_length=80)] = None
) -> list[dict[str, Any]]:
    return await service.organizations(op.ctx, q)


@router.get("/jobs/failed", response_model=list[dict[str, Any]])
async def failed_jobs(op: OperatorDep) -> list[dict[str, Any]]:
    return await service.failed_jobs(op.ctx)


@router.post("/jobs/{job_id}/retry", response_model=dict[str, str])
async def retry(job_id: uuid.UUID, op: OperatorDep) -> dict[str, str]:
    return await service.retry_job(op.ctx, job_id)


@router.post("/organizations/{org_id}/trial", response_model=dict[str, Any])
async def trial(org_id: uuid.UUID, data: TrialIn, op: OperatorDep) -> dict[str, Any]:
    return await service.extend_trial(op.ctx, org_id, data.plan, data.days)
