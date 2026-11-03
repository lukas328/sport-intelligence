from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Request, Response
from pydantic import EmailStr, Field

from handball_api.models.enums import Plan
from handball_api.routers.deps import CtxDep, OrgDep
from handball_api.schemas.common import ApiModel
from handball_api.services import billing as service
from handball_api.services import invoices

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


# ---- annual subscription by invoice (addendum 01, 4.10) ----------------------------------------


class BillingContact(ApiModel):
    name: str = Field(min_length=1, max_length=120, description="club name on the invoice")
    attention: str | None = Field(default=None, max_length=120, description="e.g. the treasurer")
    street: str = Field(min_length=1, max_length=70)
    pcode: str = Field(min_length=3, max_length=16)
    city: str = Field(min_length=1, max_length=35)
    country: str = Field(default="CH", pattern="^[A-Z]{2}$")
    email: EmailStr
    locale: str = Field(default="de-CH", pattern="^(de-CH|fr|en)$")


class InvoiceOrder(ApiModel):
    plan: Plan
    goalkeeper_seats: int = Field(default=0, ge=0, le=20)
    voucher: str | None = Field(default=None, max_length=40)
    contact: BillingContact


class InvoiceOut(ApiModel):
    id: uuid.UUID
    number: str
    plan: str | None
    amount_cents: int
    net_cents: int
    discount_cents: int
    vat_cents: int
    issued_on: date
    due_date: date
    period_start: date | None
    period_end: date | None
    paid_at: datetime | None
    dunning_level: int
    reference: str | None


class AnnualPrice(ApiModel):
    net_cents: int
    months: int
    vat_rate_percent: float | None
    payment_days: int
    contact: dict[str, str]


@router.get("/v1/orgs/{org_id}/billing/annual", response_model=AnnualPrice)
async def annual_price(scope: OrgDep, plan: Plan, goalkeeper_seats: int = 0) -> AnnualPrice:
    """Price of the annual subscription by invoice and the stored billing contact."""
    s = scope.ctx.settings
    return AnnualPrice(
        net_cents=invoices.price_cents(scope.ctx, plan, max(0, min(goalkeeper_seats, 20)))
        if plan != Plan.FREE
        else 0,
        months=s.invoice_annual_months,
        vat_rate_percent=s.invoice_vat_rate_percent if s.invoice_vat_registered else None,
        payment_days=s.invoice_payment_days,
        contact=await invoices.treasurer_default(scope.ctx, scope.org),
    )


@router.post("/v1/orgs/{org_id}/billing/invoices", response_model=InvoiceOut, status_code=201)
async def order_invoice(data: InvoiceOrder, scope: OrgDep) -> object:
    """Annual subscription by invoice: the plan starts now, the QR bill goes to the treasurer."""
    return await invoices.order(
        scope.ctx,
        data.plan,
        data.goalkeeper_seats,
        data.voucher,
        data.contact.model_dump(exclude_none=True),
    )


@router.get("/v1/orgs/{org_id}/billing/invoices", response_model=list[InvoiceOut])
async def list_invoices(scope: OrgDep) -> list[object]:
    return list(await invoices.list_for_org(scope.ctx))


@router.get(
    "/v1/orgs/{org_id}/billing/invoices/{invoice_id}/pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def invoice_pdf(invoice_id: uuid.UUID, scope: OrgDep) -> Response:
    data, name = await invoices.pdf(scope.ctx, invoice_id)
    return Response(
        data,
        media_type="application/pdf",
        headers={"content-disposition": f'inline; filename="{name}"'},
    )
