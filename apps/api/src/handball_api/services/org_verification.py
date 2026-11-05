"""Verification of clubs claimed from the official data (docs/plans/federation-onboarding.md).

An organisation linked to an official club starts `unverified` and becomes `verified` by one of:
- mail_domain: a club admin with a confirmed e-mail address at the club's domain (website or club
  address in the official data; public mail providers do not count);
- second_official: a second person with a club role (club admin or coach), not the one who
  claimed the club, confirms;
- federation: the club holds a federation licence (services/federation.py);
- operator: we checked it (backoffice).
Organisations without an official link keep `none` and work as before.

Unverified clubs use everything else, but share nothing publicly (share links, public profiles)
and see no names of other teams' players (official reports keep the numbers only).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.models import FederationMembership, Membership, Organization, OrgMembership, User
from handball_api.models.enums import OrgRole, TeamRole
from handball_api.services import audit
from handball_api.services.context import Ctx

NONE, UNVERIFIED, VERIFIED = "none", "unverified", "verified"
METHODS = ("mail_domain", "second_official", "federation", "operator")
# domains anyone can get an address at: no proof of a club role
PUBLIC_MAIL = frozenset(
    {
        "bluewin.ch",
        "gmx.ch",
        "gmx.net",
        "gmx.de",
        "gmail.com",
        "googlemail.com",
        "hotmail.com",
        "hotmail.ch",
        "outlook.com",
        "live.com",
        "icloud.com",
        "me.com",
        "yahoo.com",
        "yahoo.de",
        "sunrise.ch",
        "hispeed.ch",
        "swissonline.ch",
        "protonmail.com",
        "proton.me",
        "web.de",
        "t-online.de",
    }
)


def club_domains(domains: list[str]) -> list[str]:
    return [d for d in dict.fromkeys(d.lower() for d in domains) if d not in PUBLIC_MAIL]


def _matches(email: str, domains: list[str]) -> bool:
    host = email.rsplit("@", 1)[-1].lower()
    return any(host == d or host.endswith("." + d) for d in domains)


async def _verify(
    ctx: Ctx, org: Organization, via: str, data: dict[str, Any] | None = None
) -> None:
    org.verification, org.verified_via, org.verified_at = VERIFIED, via, datetime.now(UTC)
    await audit.record(
        ctx,
        "org.verified",
        org_id=org.id,
        target_type="organization",
        target_id=org.id,
        data={"via": via, **(data or {})},
    )


async def evaluate(ctx: Ctx, org: Organization) -> bool:
    """Checks the automatic ways (federation licence, mail domain). True when verified or when
    the organisation has no official link."""
    if org.verification != UNVERIFIED:
        return True
    licence = await ctx.db.scalar(
        select(FederationMembership.id).where(FederationMembership.organization_id == org.id)
    )
    if licence is not None:
        await _verify(ctx, org, "federation")
        return True
    domains = club_domains(org.official_domains)
    if domains:
        admins = await ctx.db.execute(
            select(User.id, User.email)
            .join(OrgMembership, OrgMembership.user_id == User.id)
            .where(
                OrgMembership.organization_id == org.id,
                OrgMembership.role == OrgRole.ORG_ADMIN,
                User.email_verified_at.is_not(None),
            )
        )
        for uid, email in admins:
            if _matches(email, domains):
                await _verify(ctx, org, "mail_domain", {"user_id": str(uid)})
                return True
    return False


async def is_unverified(ctx: Ctx, org_id: uuid.UUID) -> bool:
    org = await ctx.db.get(Organization, org_id)
    return org is not None and not await evaluate(ctx, org)


async def require_verified(ctx: Ctx, org_id: uuid.UUID) -> None:
    """Gate for public sharing and other teams' player data."""
    if await is_unverified(ctx, org_id):
        raise ProblemError(
            403,
            "org-unverified",
            "The club is not verified yet: public sharing and other teams' player data are off",
        )


async def confirm(ctx: Ctx, org: Organization, user: User) -> None:
    """A second person with a club role confirms the club (club admin or coach of a team)."""
    actor = ctx.require_actor()
    if org.verification != UNVERIFIED:
        raise ProblemError(409, "not-unverified", "The club needs no confirmation")
    coach = any(r == TeamRole.COACH for r in actor.team_roles.values())
    if not (actor.is_org_admin or coach):
        raise ProblemError(403, "forbidden", "Only a club admin or a coach of the club confirms")
    if user.id == org.claimed_by_id:
        raise ProblemError(403, "second-person-required", "A second person has to confirm")
    if user.email_verified_at is None:
        raise ProblemError(403, "email-unverified", "Confirm your e-mail address first")
    await _verify(ctx, org, "second_official", {"user_id": str(user.id)})


async def operator_set(ctx: Ctx, org_id: uuid.UUID, verified: bool) -> Organization:
    org = await ctx.db.get(Organization, org_id)
    if org is None:
        raise ProblemError(404, "not-found", "Organisation not found")
    if verified:
        await _verify(ctx, org, "operator")
    else:
        org.verification = UNVERIFIED if org.official_club_id else NONE
        org.verified_via = org.verified_at = None
        await audit.record(
            ctx, "org.unverified", org_id=org.id, target_type="organization", target_id=org.id
        )
    return org


async def team_coaches(ctx: Ctx, org_id: uuid.UUID) -> list[uuid.UUID]:
    rows = await ctx.db.scalars(
        select(Membership.user_id).where(
            Membership.organization_id == org_id, Membership.role == TeamRole.COACH
        )
    )
    return list(rows.all())


def status(org: Organization) -> dict[str, Any]:
    return {
        "verification": org.verification,
        "verified_via": org.verified_via,
        "verified_at": org.verified_at,
        "official_provider": org.official_provider,
        "official_club_id": org.official_club_id,
        "club_domains": club_domains(org.official_domains),
        "methods": list(METHODS),
    }
