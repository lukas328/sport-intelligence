"""Internal endpoints for workers. Not under /v1, never proxied by the web origin."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Header

from handball_api.core.errors import ProblemError
from handball_api.core.security import constant_time_equals
from handball_api.routers.deps import CtxDep
from handball_api.schemas.matches import JobOut, JobUpdate
from handball_api.services import videos

router = APIRouter(prefix="/internal", include_in_schema=False)


@router.post("/jobs/{job_id}", response_model=JobOut)
async def job_update(
    job_id: uuid.UUID, data: JobUpdate, ctx: CtxDep, x_internal_token: Annotated[str, Header()] = ""
) -> JobOut:
    if not constant_time_equals(x_internal_token, ctx.settings.internal_token.get_secret_value()):
        raise ProblemError(403, "forbidden", "Invalid internal token")
    return JobOut.model_validate(await videos.apply_job_update(ctx, job_id, data))
