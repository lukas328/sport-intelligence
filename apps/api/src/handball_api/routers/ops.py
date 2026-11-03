from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, UploadFile
from pydantic import Field

from handball_api.core.errors import ProblemError
from handball_api.models.enums import Plan
from handball_api.routers.deps import Authed, AuthedDep
from handball_api.schemas.common import ApiModel
from handball_api.services import invoices, monitoring
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


class PaidIn(ApiModel):
    note: str | None = Field(default=None, max_length=200)


class VoucherIn(ApiModel):
    code: str = Field(min_length=3, max_length=40, pattern="^[A-Za-z0-9-]+$")
    percent_off: int = Field(ge=1, le=100)
    valid_until: date | None = None
    max_uses: int | None = Field(default=None, ge=1)
    federation_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=200)


@router.get("/invoices", response_model=list[dict[str, Any]])
async def open_invoices(op: OperatorDep) -> list[dict[str, Any]]:
    await service._system(op.ctx, "invoice list")
    return await invoices.open_invoices(op.ctx)


@router.post("/invoices/{invoice_id}/paid", response_model=dict[str, Any])
async def mark_paid(invoice_id: uuid.UUID, data: PaidIn, op: OperatorDep) -> dict[str, Any]:
    await service._system(op.ctx, "mark invoice paid")
    inv = await invoices.mark_paid(op.ctx, invoice_id, data.note)
    return {"number": inv.number, "paid_at": inv.paid_at.isoformat() if inv.paid_at else None}


@router.post("/invoices/camt054", response_model=dict[str, list[dict[str, Any]]])
async def camt054(file: UploadFile, op: OperatorDep) -> dict[str, list[dict[str, Any]]]:
    """Bank file (ISO 20022 camt.054): payments with QR reference and amount are matched."""
    await service._system(op.ctx, "camt.054 matching")
    return await invoices.match_camt054(op.ctx, await file.read(5 * 1024 * 1024))


@router.get("/vouchers", response_model=list[dict[str, Any]])
async def vouchers(op: OperatorDep) -> list[dict[str, Any]]:
    await service._system(op.ctx, "voucher list")
    return await invoices.list_vouchers(op.ctx)


@router.post("/vouchers", response_model=dict[str, Any], status_code=201)
async def create_voucher(data: VoucherIn, op: OperatorDep) -> dict[str, Any]:
    await service._system(op.ctx, "voucher create")
    return await invoices.create_voucher(op.ctx, data.model_dump())


@router.get("/quality", response_model=dict[str, Any])
async def quality(op: OperatorDep) -> dict[str, Any]:
    """AI quality per week (confidence, correction rate), operations metrics and open alerts."""
    await service._system(op.ctx, "quality monitoring")
    weeks = await monitoring.quality_weeks(op.ctx)
    return {
        "weeks": weeks,
        "alert": monitoring.quality_alert(weeks),
        "metrics": await monitoring.ops_metrics(op.ctx),
        "alerts": await monitoring.alerts(op.ctx),
    }
