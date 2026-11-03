from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import Field

from handball_api.models.enums import Plan
from handball_api.routers.deps import CtxDep, OrgDep
from handball_api.schemas.common import ApiModel
from handball_api.services import billing as service

router = APIRouter(tags=["billing"])


class CheckoutIn(ApiModel):
    plan: Plan
    goalkeeper_seats: int = Field(default=0, ge=0, le=20)


class UrlOut(ApiModel):
    url: str


@router.get("/v1/orgs/{org_id}/billing", response_model=dict[str, Any])
async def overview(scope: OrgDep) -> dict[str, Any]:
    """Plan, limits, usage and the plan catalogue."""
    return await service.overview(scope.ctx)


@router.post("/v1/orgs/{org_id}/billing/checkout", response_model=UrlOut)
async def checkout(data: CheckoutIn, scope: OrgDep, request: Request) -> UrlOut:
    """Stripe Checkout for a paid plan (30-day trial on the first subscription)."""
    url = await service.checkout(
        scope.ctx, request.app.state.billing, data.plan, data.goalkeeper_seats
    )
    return UrlOut(url=url)


@router.post("/v1/orgs/{org_id}/billing/portal", response_model=UrlOut)
async def portal(scope: OrgDep, request: Request) -> UrlOut:
    """Stripe customer portal: payment method, invoices, plan changes, cancellation."""
    return UrlOut(url=await service.portal(scope.ctx, request.app.state.billing))


@router.post("/v1/stripe/webhook", response_model=dict[str, str], include_in_schema=False)
async def webhook(request: Request, ctx: CtxDep) -> dict[str, str]:
    payload = await request.body()
    return await service.handle_webhook(ctx, payload, request.headers.get("stripe-signature"))
