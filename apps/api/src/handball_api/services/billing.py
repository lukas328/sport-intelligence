"""Plans, usage, limits and Stripe billing (BRIEF 13, M8).

Enforcement is switched by `HB_BILLING_ENFORCE` (off in development and CI, on in production).
Without it every organisation gets every feature, so self-hosted and test setups are not limited.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import stripe
from sqlalchemy import func, select

from handball_api.core.config import Settings
from handball_api.core.db import disable_system_access, enable_system_access
from handball_api.core.errors import ProblemError
from handball_api.core.logging import get_logger
from handball_api.models import (
    Match,
    Organization,
    OrgMembership,
    ProcessingJob,
    StripeEvent,
    Team,
    User,
    VideoAsset,
)
from handball_api.models.enums import JobStatus, OrgRole, Plan
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.plans import FEATURES, GOALKEEPER_ADDON_CHF, PLANS, PlanSpec
from handball_api.services.policies import Action, authorize

log = get_logger("handball_api.billing")
ACTIVE = ("active", "trialing", "past_due")
GB = 1024**3


def _now() -> datetime:
    return datetime.now(UTC)


# ---- plan and features ----------------------------------------------------------------------


def effective_plan(org: Organization) -> Plan:
    """The plan whose limits apply now: a lapsed subscription falls back to Free."""
    if org.plan == Plan.FREE:
        return Plan.FREE
    if org.subscription_status in ACTIVE:
        return org.plan
    # annual subscription by invoice: usable until paid_until (payment term plus dunning period)
    # annual invoice or a federation licence (5.10): valid until paid_until
    if org.subscription_status in ("invoice_open", "invoice_paid", "federation") and (
        org.paid_until and org.paid_until > _now()
    ):
        return org.plan
    if org.trial_ends_at and org.trial_ends_at > _now():
        return org.plan
    return Plan.FREE


def spec(org: Organization) -> PlanSpec:
    return PLANS[effective_plan(org)]


def has_feature(settings: Settings, org: Organization, feature: str) -> bool:
    return not settings.billing_enforce or feature in spec(org).features


async def _org(ctx: Ctx, org_id: uuid.UUID | None = None) -> Organization:
    oid = org_id or ctx.require_actor().organization_id
    org = await ctx.db.get(Organization, oid)
    if org is None:
        raise ProblemError(404, "not-found", "Organisation not found")
    return org


async def require_feature(ctx: Ctx, feature: str, org_id: uuid.UUID | None = None) -> None:
    org = await _org(ctx, org_id)
    if not has_feature(ctx.settings, org, feature):
        raise ProblemError(
            402, "plan-required", f"The feature '{feature}' is not part of the current plan"
        )


# ---- usage and limits -----------------------------------------------------------------------


async def usage(ctx: Ctx, org: Organization) -> dict[str, Any]:
    month = _now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    teams = await ctx.db.scalar(select(func.count(Team.id)).where(Team.organization_id == org.id))
    storage = await ctx.db.scalar(
        select(func.coalesce(func.sum(VideoAsset.size_bytes), 0)).where(
            VideoAsset.organization_id == org.id
        )
    )
    gpu_seconds = await ctx.db.scalar(
        select(func.coalesce(func.sum(ProcessingJob.gpu_seconds), 0)).where(
            ProcessingJob.organization_id == org.id,
            ProcessingJob.created_at >= month,
            ProcessingJob.status != JobStatus.FAILED,  # failed runs are not charged
        )
    )
    per_season = (
        await ctx.db.execute(
            select(Match.team_id, Match.season_id, func.count(Match.id))
            .where(
                Match.organization_id == org.id,
                Match.is_demo.is_(False),
                Match.quota_credit.is_(False),
            )
            .group_by(Match.team_id, Match.season_id)
        )
    ).all()
    return {
        "teams": int(teams or 0),
        "storage_bytes": int(storage or 0),
        "gpu_minutes": round(float(gpu_seconds or 0) / 60, 1),
        "max_matches_per_season": max((int(n) for _, _, n in per_season), default=0),
    }


async def _limit_check(ctx: Ctx, org_id: uuid.UUID) -> tuple[Organization, PlanSpec] | None:
    if not ctx.settings.billing_enforce:
        return None
    org = await _org(ctx, org_id)
    return org, spec(org)


def _limit(code: str, detail: str) -> ProblemError:
    return ProblemError(402, f"plan-limit-{code}", detail)


async def check_new_team(ctx: Ctx, org_id: uuid.UUID) -> None:
    check = await _limit_check(ctx, org_id)
    if check is None:
        return
    org, s = check
    if (await usage(ctx, org))["teams"] >= s.teams:
        raise _limit("teams", f"The plan allows {s.teams} team(s)")


async def check_new_match(
    ctx: Ctx, org_id: uuid.UUID, team_id: uuid.UUID, season_id: uuid.UUID
) -> None:
    check = await _limit_check(ctx, org_id)
    if check is None or check[1].matches_per_season is None:
        return
    count = await ctx.db.scalar(
        select(func.count(Match.id)).where(
            Match.team_id == team_id,
            Match.season_id == season_id,
            Match.is_demo.is_(False),
            Match.quota_credit.is_(False),  # failed analyses are credited (addendum 01, 4.11)
        )
    )
    if (count or 0) >= check[1].matches_per_season:
        raise _limit("matches", f"The plan allows {check[1].matches_per_season} matches per season")


async def check_upload(ctx: Ctx, org_id: uuid.UUID, size_bytes: int) -> None:
    check = await _limit_check(ctx, org_id)
    if check is None:
        return
    org, s = check
    if (await usage(ctx, org))["storage_bytes"] + size_bytes > s.storage_gb * GB:
        raise _limit("storage", f"The plan includes {s.storage_gb} GB of video storage")


async def analysis_allowed(ctx: Ctx, org_id: uuid.UUID) -> bool:
    """Tracking needs the feature and GPU minutes left this month (the video stays usable)."""
    if not ctx.settings.billing_enforce:
        return True
    org = await _org(ctx, org_id)
    s = spec(org)
    return "tracking" in s.features and (await usage(ctx, org))["gpu_minutes"] < s.gpu_minutes_month


# ---- overview for the settings page ---------------------------------------------------------


async def overview(ctx: Ctx) -> dict[str, Any]:
    org = await _org(ctx)
    authorize(ctx.require_actor(), Action.ORG_READ)
    s = spec(org)
    return {
        "plan": org.plan.value,
        "effective_plan": effective_plan(org).value,
        "status": org.subscription_status,
        "trial_ends_at": org.trial_ends_at,
        "current_period_end": org.current_period_end,
        "paid_until": org.paid_until,
        "goalkeeper_seats": org.goalkeeper_seats,
        "enforced": ctx.settings.billing_enforce,
        "checkout_available": ctx.settings.stripe_secret_key is not None,
        "limits": {
            "teams": s.teams,
            "matches_per_season": s.matches_per_season,
            "storage_gb": s.storage_gb,
            "gpu_minutes_month": s.gpu_minutes_month,
        },
        "features": sorted(s.features) if ctx.settings.billing_enforce else list(FEATURES),
        "usage": await usage(ctx, org),
        "plans": [
            {
                "plan": p.plan.value,
                "price_chf_month": p.price_chf_month,
                "teams": p.teams,
                "matches_per_season": p.matches_per_season,
                "storage_gb": p.storage_gb,
                "gpu_minutes_month": p.gpu_minutes_month,
                "features": sorted(p.features),
                "trial_days": p.trial_days,
            }
            for p in PLANS.values()
        ],
        "goalkeeper_addon_chf": GOALKEEPER_ADDON_CHF,
    }


# ---- Stripe ---------------------------------------------------------------------------------


class BillingGateway(Protocol):
    async def create_customer(self, name: str, email: str, org_id: str) -> str: ...

    async def checkout_url(
        self,
        customer: str,
        items: list[tuple[str, int]],
        trial_days: int,
        success_url: str,
        cancel_url: str,
        org_id: str,
    ) -> str: ...

    async def portal_url(self, customer: str, return_url: str) -> str: ...


class StripeGateway:
    def __init__(self, secret_key: str) -> None:
        self.client = stripe.StripeClient(secret_key)

    async def create_customer(self, name: str, email: str, org_id: str) -> str:
        c = await self.client.v1.customers.create_async(
            params={"name": name, "email": email, "metadata": {"org_id": org_id}}
        )
        return str(c.id)

    async def checkout_url(
        self,
        customer: str,
        items: list[tuple[str, int]],
        trial_days: int,
        success_url: str,
        cancel_url: str,
        org_id: str,
    ) -> str:
        params: dict[str, Any] = {
            "mode": "subscription",
            "customer": customer,
            "client_reference_id": org_id,
            "line_items": [{"price": p, "quantity": q} for p, q in items],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "allow_promotion_codes": True,
            "subscription_data": {"metadata": {"org_id": org_id}},
        }
        if trial_days:
            params["subscription_data"]["trial_period_days"] = trial_days
        session = await self.client.v1.checkout.sessions.create_async(params=params)  # type: ignore[arg-type]
        return str(session.url)

    async def portal_url(self, customer: str, return_url: str) -> str:
        session = await self.client.v1.billing_portal.sessions.create_async(
            params={"customer": customer, "return_url": return_url}
        )
        return str(session.url)


def _price(settings: Settings, plan: Plan) -> str:
    price = {Plan.TEAM: settings.stripe_price_team, Plan.CLUB: settings.stripe_price_club}.get(plan)
    if not price:
        raise ProblemError(503, "billing-unavailable", "Billing is not configured")
    return price


async def checkout(ctx: Ctx, gateway: BillingGateway | None, plan: Plan, goalkeepers: int) -> str:
    actor = ctx.require_actor()
    authorize(actor, Action.ORG_UPDATE, two_factor=ctx.two_factor)
    if gateway is None:
        raise ProblemError(503, "billing-unavailable", "Billing is not configured")
    if plan == Plan.FREE:
        raise ProblemError(422, "validation", "Choose a paid plan")
    org = await _org(ctx)
    items = [(_price(ctx.settings, plan), 1)]
    if goalkeepers:
        if not ctx.settings.stripe_price_goalkeeper:
            raise ProblemError(
                503, "billing-unavailable", "The goalkeeper add-on is not configured"
            )
        items.append((ctx.settings.stripe_price_goalkeeper, goalkeepers))
    if not org.stripe_customer_id:
        user = await ctx.db.get(User, ctx.user_id)
        org.stripe_customer_id = await gateway.create_customer(
            org.name, user.email if user else "", str(org.id)
        )
    base = f"{ctx.settings.web_base_url}/app/{org.id}/settings"
    url = await gateway.checkout_url(
        org.stripe_customer_id,
        items,
        0 if org.trial_used else PLANS[plan].trial_days,
        f"{base}?billing=success#billing",
        f"{base}?billing=cancel#billing",
        str(org.id),
    )
    await audit.record(ctx, "billing.checkout_started", data={"plan": plan.value})
    return url


async def portal(ctx: Ctx, gateway: BillingGateway | None) -> str:
    authorize(ctx.require_actor(), Action.ORG_UPDATE, two_factor=ctx.two_factor)
    org = await _org(ctx)
    if gateway is None or not org.stripe_customer_id:
        raise ProblemError(409, "no-subscription", "There is no billing account yet")
    return await gateway.portal_url(
        org.stripe_customer_id, f"{ctx.settings.web_base_url}/app/{org.id}/settings#billing"
    )


def _plan_for(settings: Settings, price_ids: list[str]) -> Plan | None:
    if settings.stripe_price_club and settings.stripe_price_club in price_ids:
        return Plan.CLUB
    if settings.stripe_price_team and settings.stripe_price_team in price_ids:
        return Plan.TEAM
    return None


def _ts(v: Any) -> datetime | None:
    return datetime.fromtimestamp(int(v), UTC) if v else None


async def handle_webhook(ctx: Ctx, payload: bytes, signature: str | None) -> dict[str, str]:
    """Verified, idempotent processing of Stripe events (each event id once)."""
    secret = ctx.settings.stripe_webhook_secret
    if secret is None:
        raise ProblemError(503, "billing-unavailable", "Billing is not configured")
    try:
        event = stripe.Webhook.construct_event(payload, signature, secret.get_secret_value())
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise ProblemError(400, "invalid-signature", "Invalid webhook signature") from exc
    await enable_system_access(ctx.db, reason="stripe webhook")
    try:
        if await ctx.db.get(StripeEvent, event.id) is not None:
            return {"status": "duplicate"}
        ctx.db.add(StripeEvent(id=event.id, type=event.type))
        # plain dicts from the verified payload (StripeObject is not a dict)
        obj = json.loads(payload)["data"]["object"]
        if event.type == "checkout.session.completed":
            await _on_checkout(ctx, obj)
        elif event.type in (
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            await _on_subscription(ctx, obj, deleted=event.type.endswith("deleted"))
        elif event.type == "invoice.payment_failed":
            org = await _by_customer(ctx, obj.get("customer"))
            if org is not None:
                org.subscription_status = "past_due"
                await _notify_admins(ctx, org, "payment_failed")
        await ctx.db.flush()
        log.info("stripe_event", id=event.id, type=event.type)
        return {"status": "processed"}
    finally:
        await disable_system_access(ctx.db)


async def _by_customer(ctx: Ctx, customer: Any) -> Organization | None:
    if not customer:
        return None
    return await ctx.db.scalar(
        select(Organization).where(Organization.stripe_customer_id == str(customer))
    )


async def _on_checkout(ctx: Ctx, obj: Any) -> None:
    ref = obj.get("client_reference_id")
    try:
        org = await ctx.db.get(Organization, uuid.UUID(str(ref))) if ref else None
    except ValueError:
        org = None
    if org is None:
        return
    org.stripe_customer_id = str(obj.get("customer") or org.stripe_customer_id)
    if obj.get("subscription"):
        org.stripe_subscription_id = str(obj.get("subscription"))


async def _on_subscription(ctx: Ctx, sub: Any, deleted: bool) -> None:
    org = await _by_customer(ctx, sub.get("customer"))
    if org is None:
        return
    items = (sub.get("items") or {}).get("data") or []
    prices = [str((i.get("price") or {}).get("id")) for i in items]
    plan = _plan_for(ctx.settings, prices)
    if deleted:
        org.plan = Plan.FREE
        org.subscription_status = "canceled"
        org.goalkeeper_seats = 0
        await _notify_admins(ctx, org, "subscription_canceled")
        return
    org.stripe_subscription_id = str(sub.get("id"))
    if plan is not None:
        org.plan = plan
    org.subscription_status = str(sub.get("status"))
    org.trial_ends_at = _ts(sub.get("trial_end"))
    if org.trial_ends_at:
        org.trial_used = True
    period = sub.get("current_period_end") or (
        items[0].get("current_period_end") if items else None
    )
    org.current_period_end = _ts(period)
    gk = ctx.settings.stripe_price_goalkeeper
    org.goalkeeper_seats = sum(
        int(i.get("quantity") or 0) for i in items if gk and (i.get("price") or {}).get("id") == gk
    )


async def _notify_admins(ctx: Ctx, org: Organization, kind: str) -> None:
    from handball_api.services import training  # local import: training imports this module's peers

    admins = (
        await ctx.db.scalars(
            select(OrgMembership.user_id).where(
                OrgMembership.organization_id == org.id, OrgMembership.role == OrgRole.ORG_ADMIN
            )
        )
    ).all()
    await training.notify(ctx, org.id, list(admins), kind, {}, f"/app/{org.id}/settings#billing")


def trial_until(days: int) -> datetime:
    return _now() + timedelta(days=days)
