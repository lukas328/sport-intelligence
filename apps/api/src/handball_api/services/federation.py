"""Federation and volume licences (addendum 01, 5.10).

Operators create a federation with plan, quota and contract end, and name its admins. Federation
admins invite clubs by e-mail; a club admin accepts the link, and the club then runs on the
federation's plan until the contract ends (billing status "federation", one joint invoice to the
federation instead of club invoices). The federation sees usage per member club and anonymised
figures aggregated over at least `MIN_CLUBS` clubs with data. It never sees videos, players or other
club content; clubs can leave at any time.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select

from handball_api.core.db import disable_system_access, enable_system_access
from handball_api.core.email import Email, try_send
from handball_api.core.errors import ProblemError
from handball_api.core.security import hash_token, new_token
from handball_api.models import (
    Event,
    Federation,
    FederationAdmin,
    FederationInvite,
    FederationMembership,
    Match,
    Organization,
    OrgMembership,
    ProcessingJob,
    Team,
    User,
)
from handball_api.models.enums import Plan
from handball_api.schemas.federation import FederationIn
from handball_api.services import audit, invoice_pdf
from handball_api.services.context import Ctx
from handball_api.services.invoices import creditor, price_cents, rf_reference
from handball_api.services.policies import Action, authorize

INVITE_DAYS = 30
MIN_CLUBS = 5  # aggregated figures only from this many member clubs with data (k-anonymity)


def _now() -> datetime:
    return datetime.now(UTC)


def _until(f: Federation) -> datetime:
    day = f.contract_until or (_now().date() + timedelta(days=365))
    return datetime.combine(day, time(23, 59), tzinfo=UTC)


# ---- operators ----------------------------------------------------------------------------------


async def create(ctx: Ctx, data: FederationIn) -> Federation:
    await enable_system_access(ctx.db, reason="federation create")
    f = Federation(
        name=data.name,
        contract_ref=data.contract_ref,
        contract_until=data.contract_until,
        seat_quota=data.seat_quota,
        plan=data.plan,
        billing_address=data.billing_address,
    )
    ctx.db.add(f)
    await ctx.db.flush()
    await disable_system_access(ctx.db)
    await audit.record(ctx, "federation.created", target_type="federation", target_id=f.id)
    return f


async def all_federations(ctx: Ctx) -> list[Federation]:
    return list((await ctx.db.scalars(select(Federation).order_by(Federation.name))).all())


async def add_admin(ctx: Ctx, federation_id: uuid.UUID, email: str) -> None:
    f = await ctx.db.get(Federation, federation_id)
    if f is None:
        raise ProblemError(404, "not-found", "Federation not found")
    user = await ctx.db.scalar(select(User).where(func.lower(User.email) == email.lower()))
    if user is None:
        raise ProblemError(404, "not-found", "No account with this e-mail; register first")
    await enable_system_access(ctx.db, reason="federation admin")
    exists = await ctx.db.scalar(
        select(FederationAdmin.id).where(
            FederationAdmin.federation_id == f.id, FederationAdmin.user_id == user.id
        )
    )
    if not exists:
        ctx.db.add(FederationAdmin(federation_id=f.id, user_id=user.id))
        await ctx.db.flush()
    await disable_system_access(ctx.db)


async def invoice(ctx: Ctx, federation_id: uuid.UUID, lang: str) -> tuple[bytes, str]:
    """Joint annual invoice: one line per active member club at the federation's plan price."""
    f = await ctx.db.get(Federation, federation_id)
    if f is None:
        raise ProblemError(404, "not-found", "Federation not found")
    members = await _members(ctx, f.id)
    if not members:
        raise ProblemError(409, "no-members", "The federation has no member clubs yet")
    unit = price_cents(ctx, Plan(f.plan), 0)
    issued = _now().date()
    number = f"F-{issued.year}-{str(f.id)[:8].upper()}"
    total = unit * len(members)
    inv = {
        "number": number,
        "recipient": {"name": f.name, **f.billing_address},
        "issued_on": issued,
        "due_date": issued + timedelta(days=ctx.settings.invoice_payment_days),
        "period_start": issued,
        "period_end": f.contract_until or issued + timedelta(days=364),
        "lines": [
            {"text": f"{f.plan.capitalize()}: {org.name}", "cents": unit} for org, _ in members
        ],
        "net_cents": total,
        "discount_cents": 0,
        "vat_cents": 0,
        "vat_rate_bp": 0,
        "total_cents": total,
        "reference": rf_reference(number),
        "voucher_code": None,
    }
    s = ctx.settings
    pdf = invoice_pdf.render(
        lang,
        creditor(ctx),
        s.invoice_iban,
        s.invoice_uid if s.invoice_vat_registered else None,
        inv,
        s.invoice_payment_days,
    )
    await audit.record(ctx, "federation.invoiced", target_type="federation", target_id=f.id)
    return pdf, f"{number}.pdf"


# ---- federation admins --------------------------------------------------------------------------


async def _admin_of(ctx: Ctx, federation_id: uuid.UUID) -> Federation:
    f = await ctx.db.get(Federation, federation_id)
    ok = f is not None and await ctx.db.scalar(
        select(FederationAdmin.id).where(
            FederationAdmin.federation_id == federation_id,
            FederationAdmin.user_id == ctx.user_id,
        )
    )
    if not ok or f is None:
        raise ProblemError(404, "not-found", "Federation not found")
    return f


async def mine(ctx: Ctx) -> list[Federation]:
    return list(
        (
            await ctx.db.scalars(
                select(Federation)
                .join(FederationAdmin, FederationAdmin.federation_id == Federation.id)
                .where(FederationAdmin.user_id == ctx.user_id)
                .order_by(Federation.name)
            )
        ).all()
    )


async def _members(
    ctx: Ctx, federation_id: uuid.UUID
) -> list[tuple[Organization, FederationMembership]]:
    await enable_system_access(ctx.db, reason="federation members")
    rows = (
        await ctx.db.execute(
            select(Organization, FederationMembership)
            .join(FederationMembership, FederationMembership.organization_id == Organization.id)
            .where(FederationMembership.federation_id == federation_id)
            .order_by(Organization.name)
        )
    ).all()
    await disable_system_access(ctx.db)
    return [(o, m) for o, m in rows]


async def _open_invites(ctx: Ctx, federation_id: uuid.UUID) -> list[FederationInvite]:
    await enable_system_access(ctx.db, reason="federation invites")
    rows = (
        await ctx.db.scalars(
            select(FederationInvite).where(
                FederationInvite.federation_id == federation_id,
                FederationInvite.accepted_at.is_(None),
                FederationInvite.expires_at > _now(),
            )
        )
    ).all()
    await disable_system_access(ctx.db)
    return list(rows)


async def invite(ctx: Ctx, federation_id: uuid.UUID, email: str) -> dict[str, Any]:
    f = await _admin_of(ctx, federation_id)
    used = len(await _members(ctx, f.id)) + len(await _open_invites(ctx, f.id))
    if used >= f.seat_quota:
        raise ProblemError(409, "quota-reached", "All licences of the quota are used or invited")
    token = new_token(24)
    await enable_system_access(ctx.db, reason="federation invite")
    inv = FederationInvite(
        federation_id=f.id,
        email=email.lower(),
        token_hash=hash_token(token),
        expires_at=_now() + timedelta(days=INVITE_DAYS),
    )
    ctx.db.add(inv)
    await ctx.db.flush()
    await disable_system_access(ctx.db)
    link = f"{ctx.settings.web_base_url.rstrip('/')}/federation/join?token={token}"
    # the invite stays valid when the mail fails (logged)
    await try_send(
        ctx.email,
        Email(
            to=email,
            subject=f"{f.name}: Lizenz für euren Verein / licence pour votre club / club licence",
            text=(
                f"{f.name} lädt euren Verein ein, Handball Intelligence mit dem "
                f"{f.plan.capitalize()}-Plan zu nutzen. Eine Vereinsadministratorin oder ein "
                f"Vereinsadministrator nimmt die Einladung hier an:\n{link}\n\n"
                f"{f.name} invite votre club à utiliser Handball Intelligence. "
                f"Accepter : {link}\n\n"
                f"{f.name} invites your club to use Handball Intelligence. Accept: {link}\n\n"
                "Der Verband sieht die Nutzung und anonymisierte Kennzahlen, aber keine Videos "
                "und keine Personen. / The federation sees usage and anonymised figures, never "
                "videos or people."
            ),
        ),
        "federation_invite",
        federation_id=str(f.id),
    )
    await audit.record(ctx, "federation.invited", target_type="federation", target_id=f.id)
    return {"email": inv.email, "expires_at": inv.expires_at}


async def remove_member(ctx: Ctx, federation_id: uuid.UUID, org_id: uuid.UUID) -> None:
    f = await _admin_of(ctx, federation_id)
    await _end(ctx, f.id, org_id)


async def _end(ctx: Ctx, federation_id: uuid.UUID, org_id: uuid.UUID) -> None:
    await enable_system_access(ctx.db, reason="federation membership end")
    m = await ctx.db.scalar(
        select(FederationMembership).where(
            FederationMembership.federation_id == federation_id,
            FederationMembership.organization_id == org_id,
        )
    )
    if m is None:
        await disable_system_access(ctx.db)
        raise ProblemError(404, "not-found", "Not a member")
    await ctx.db.delete(m)
    org = await ctx.db.get(Organization, org_id)
    if org is not None and org.subscription_status == "federation":
        org.plan, org.subscription_status, org.paid_until = Plan.FREE, None, None
    await ctx.db.flush()
    await disable_system_access(ctx.db)


def _month_ago() -> datetime:
    return _now() - timedelta(days=30)


async def overview(ctx: Ctx, federation_id: uuid.UUID) -> dict[str, Any]:
    """Usage per member club and aggregated, anonymised figures; no club content."""
    f = await _admin_of(ctx, federation_id)
    members = await _members(ctx, f.id)
    org_ids = [o.id for o, _ in members]
    await enable_system_access(ctx.db, reason="federation overview (counts only)")
    teams = dict(
        (
            await ctx.db.execute(
                select(Team.organization_id, func.count(Team.id))
                .where(Team.organization_id.in_(org_ids))
                .group_by(Team.organization_id)
            )
        ).all()
    )
    matches = dict(
        (
            await ctx.db.execute(
                select(Match.organization_id, func.count(Match.id))
                .where(Match.organization_id.in_(org_ids), Match.kind == "match")
                .group_by(Match.organization_id)
            )
        ).all()
    )
    users = dict(
        (
            await ctx.db.execute(
                select(OrgMembership.organization_id, func.count(OrgMembership.id))
                .where(OrgMembership.organization_id.in_(org_ids))
                .group_by(OrgMembership.organization_id)
            )
        ).all()
    )
    analyses = dict(
        (
            await ctx.db.execute(
                select(ProcessingJob.organization_id, func.count(ProcessingJob.id))
                .where(
                    ProcessingJob.organization_id.in_(org_ids),
                    ProcessingJob.kind == "analysis",
                    ProcessingJob.status == "succeeded",
                    ProcessingJob.created_at >= _month_ago(),
                )
                .group_by(ProcessingJob.organization_id)
            )
        ).all()
    )
    per_club = (
        await ctx.db.execute(
            select(
                Event.organization_id,
                func.count(func.distinct(Event.match_id)),
                func.count(Event.id).filter(Event.type == "shot", Event.side == "own"),
                func.count(Event.id).filter(
                    Event.type == "shot", Event.side == "own", Event.outcome == "goal"
                ),
            )
            .where(Event.organization_id.in_(org_ids))
            .group_by(Event.organization_id)
        )
    ).all()
    await disable_system_access(ctx.db)
    with_data = [(m, s, g) for _, m, s, g in per_club if m > 0]
    aggregate: dict[str, Any] = {"clubs_with_data": len(with_data), "min_clubs": MIN_CLUBS}
    if len(with_data) >= MIN_CLUBS:
        n_matches = sum(m for m, _, _ in with_data)
        shots = sum(s for _, s, _ in with_data)
        goals = sum(g for _, _, g in with_data)
        aggregate.update(
            matches_with_events=n_matches,
            goals_per_match=round(goals / n_matches, 1) if n_matches else None,
            shooting_pct=round(goals / shots, 3) if shots else None,
        )
    return {
        "federation": {
            "id": f.id,
            "name": f.name,
            "plan": f.plan,
            "seat_quota": f.seat_quota,
            "contract_until": f.contract_until,
        },
        "seats_used": len(members),
        "open_invites": len(await _open_invites(ctx, f.id)),
        "members": [
            {
                "organization_id": o.id,
                "name": o.name,
                "joined_at": m.joined_at,
                "teams": int(teams.get(o.id, 0)),
                "matches": int(matches.get(o.id, 0)),
                "members": int(users.get(o.id, 0)),
                "analyses_30d": int(analyses.get(o.id, 0)),
            }
            for o, m in members
        ],
        "aggregate": aggregate,
    }


# ---- clubs --------------------------------------------------------------------------------------


async def accept(ctx: Ctx, org_id: uuid.UUID, token: str) -> dict[str, Any]:
    authorize(ctx.require_actor(), Action.ORG_UPDATE, two_factor=ctx.two_factor)
    await enable_system_access(ctx.db, reason="federation accept")
    inv = await ctx.db.scalar(
        select(FederationInvite).where(FederationInvite.token_hash == hash_token(token))
    )
    if inv is None or inv.accepted_at is not None or inv.expires_at <= _now():
        await disable_system_access(ctx.db)
        raise ProblemError(404, "not-found", "This invitation is no longer valid")
    f = await ctx.db.get(Federation, inv.federation_id)
    assert f is not None
    members = await ctx.db.scalar(
        select(func.count(FederationMembership.id)).where(
            FederationMembership.federation_id == f.id
        )
    )
    already = await ctx.db.scalar(
        select(FederationMembership.id).where(FederationMembership.organization_id == org_id)
    )
    if already:
        await disable_system_access(ctx.db)
        raise ProblemError(409, "already-member", "The club already belongs to a federation")
    if (members or 0) >= f.seat_quota:
        await disable_system_access(ctx.db)
        raise ProblemError(409, "quota-reached", "The federation's quota is used up")
    ctx.db.add(
        FederationMembership(organization_id=org_id, federation_id=f.id, seats=1, joined_at=_now())
    )
    inv.accepted_at, inv.organization_id = _now(), org_id
    org = await ctx.db.get(Organization, org_id)
    assert org is not None
    org.plan = Plan(f.plan)
    org.subscription_status = "federation"
    org.paid_until = _until(f)
    await ctx.db.flush()
    await disable_system_access(ctx.db)
    await audit.record(ctx, "federation.joined", target_type="federation", target_id=f.id)
    return {"federation": f.name, "plan": f.plan, "until": org.paid_until}


async def status(ctx: Ctx, org_id: uuid.UUID) -> dict[str, Any] | None:
    authorize(ctx.require_actor(), Action.ORG_READ, two_factor=ctx.two_factor)
    m = await ctx.db.scalar(
        select(FederationMembership).where(FederationMembership.organization_id == org_id)
    )
    if m is None:
        return None
    f = await ctx.db.get(Federation, m.federation_id)
    assert f is not None
    return {
        "federation": f.name,
        "plan": f.plan,
        "joined_at": m.joined_at,
        "contract_until": f.contract_until,
    }


async def leave(ctx: Ctx, org_id: uuid.UUID) -> None:
    authorize(ctx.require_actor(), Action.ORG_UPDATE, two_factor=ctx.two_factor)
    m = await ctx.db.scalar(
        select(FederationMembership).where(FederationMembership.organization_id == org_id)
    )
    if m is None:
        raise ProblemError(404, "not-found", "Not a member")
    await _end(ctx, m.federation_id, org_id)
    await audit.record(ctx, "federation.left", target_type="organization", target_id=org_id)
