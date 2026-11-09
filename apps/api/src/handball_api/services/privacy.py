"""Privacy functions (BRIEF 9 / M9): personal data export, account deletion, club deletion.

- Export: everything the platform holds about the signed-in person, as JSON (Art. 15/20 GDPR,
  Swiss revDSG Art. 25/28).
- Account deletion: removes the person; their comments and corrections stay without author
  (database ON DELETE SET NULL), memberships and sessions are deleted. The last admin of a club with
  other members must hand over first.
- Club deletion: org admin, name confirmation, no running subscription. Deletes all rows (cascade)
  and every stored object under the club's prefix in both buckets.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select

from handball_api.core.db import disable_system_access, enable_system_access
from handball_api.core.errors import ProblemError
from handball_api.core.logging import get_logger
from handball_api.core.security import verify_password
from handball_api.models import (
    AssignmentStatus,
    AuditLog,
    AuthSession,
    Comment,
    Guardianship,
    Membership,
    Notification,
    Organization,
    OrgMembership,
    Player,
    Team,
    User,
)
from handball_api.models.enums import OrgRole
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.policies import Action, authorize

log = get_logger("handball_api.privacy")


def _iso(v: datetime | None) -> str | None:
    return v.isoformat() if v else None


async def export(ctx: Ctx, user: User) -> dict[str, Any]:
    """All personal data of the signed-in person across every club they belong to."""
    await enable_system_access(ctx.db, reason="personal data export (own data)")
    try:
        orgs = (
            await ctx.db.execute(
                select(Organization.id, Organization.name, OrgMembership.role)
                .join(OrgMembership, OrgMembership.organization_id == Organization.id)
                .where(OrgMembership.user_id == user.id)
            )
        ).all()
        teams = (
            await ctx.db.execute(
                select(Team.name, Membership.role, Team.organization_id)
                .join(Membership, Membership.team_id == Team.id)
                .where(Membership.user_id == user.id)
            )
        ).all()
        sessions = (
            await ctx.db.scalars(select(AuthSession).where(AuthSession.user_id == user.id))
        ).all()
        comments = (await ctx.db.scalars(select(Comment).where(Comment.author_id == user.id))).all()
        notes = (
            await ctx.db.scalars(select(Notification).where(Notification.user_id == user.id))
        ).all()
        statuses = (
            await ctx.db.scalars(
                select(AssignmentStatus).where(AssignmentStatus.user_id == user.id)
            )
        ).all()
        players = (await ctx.db.scalars(select(Player).where(Player.user_id == user.id))).all()
        children = (
            await ctx.db.scalars(
                select(Player)
                .join(Guardianship, Guardianship.player_id == Player.id)
                .where(Guardianship.user_id == user.id)
            )
        ).all()
        audits = (
            await ctx.db.scalars(
                select(AuditLog)
                .where(AuditLog.actor_user_id == user.id)
                .order_by(AuditLog.created_at.desc())
                .limit(1000)
            )
        ).all()
    finally:
        await disable_system_access(ctx.db)
    await audit.record(ctx, "privacy.export")
    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "account": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "locale": user.locale,
            "email_verified_at": _iso(user.email_verified_at),
            "two_factor": user.totp_secret_enc is not None,
            "created_at": _iso(user.created_at),
        },
        "organizations": [{"id": str(i), "name": n, "role": r.value} for i, n, r in orgs],
        "teams": [{"team": n, "role": r.value, "organization_id": str(o)} for n, r, o in teams],
        "player_profiles": [
            {
                "id": str(p.id),
                "first_name": p.first_name,
                "last_name": p.last_name,
                "birth_year": p.birth_year,
                "organization_id": str(p.organization_id),
            }
            for p in players
        ],
        "children": [
            {
                "id": str(p.id),
                "first_name": p.first_name,
                "last_name": p.last_name,
                "organization_id": str(p.organization_id),
            }
            for p in children
        ],
        "sessions": [
            {
                "created_at": _iso(s.created_at),
                "last_seen_at": _iso(s.last_seen_at),
                "user_agent": s.user_agent,
                "ip": str(s.ip) if s.ip else None,
            }
            for s in sessions
        ],
        "comments": [
            {
                "match_id": str(c.match_id),
                "t_ms": c.t_ms,
                "body": c.body,
                "created_at": _iso(c.created_at),
            }
            for c in comments
        ],
        "notifications": [
            {
                "kind": n.kind,
                "params": n.params,
                "created_at": _iso(n.created_at),
                "read_at": _iso(n.read_at),
            }
            for n in notes
        ],
        "assignments": [
            {
                "assignment_id": str(s.assignment_id),
                "seen_at": _iso(s.seen_at),
                "done_at": _iso(s.done_at),
            }
            for s in statuses
        ],
        "activity_log": [
            {"action": a.action, "at": _iso(a.created_at), "data": a.data} for a in audits
        ],
    }


async def delete_account(ctx: Ctx, user: User, password: str | None, confirm_email: str) -> None:
    if confirm_email.strip().lower() != user.email.lower():
        raise ProblemError(422, "confirmation-mismatch", "Type your e-mail address to confirm")
    if user.password_hash and not await asyncio.to_thread(
        verify_password, user.password_hash, password or ""
    ):
        raise ProblemError(403, "invalid-credentials", "Wrong password")
    await enable_system_access(ctx.db, reason="account deletion (own account)")
    try:
        admin_orgs = (
            await ctx.db.scalars(
                select(OrgMembership.organization_id).where(
                    OrgMembership.user_id == user.id, OrgMembership.role == OrgRole.ORG_ADMIN
                )
            )
        ).all()
        sole_orgs: list[uuid.UUID] = []
        for org_id in admin_orgs:
            admins = await ctx.db.scalar(
                select(func.count(OrgMembership.id)).where(
                    OrgMembership.organization_id == org_id,
                    OrgMembership.role == OrgRole.ORG_ADMIN,
                )
            )
            members = await ctx.db.scalar(
                select(func.count(OrgMembership.id)).where(OrgMembership.organization_id == org_id)
            )
            if (admins or 0) <= 1 and (members or 0) > 1:
                raise ProblemError(
                    409, "last-admin", "Make another member club admin before deleting the account"
                )
            if (members or 0) <= 1:
                sole_orgs.append(org_id)
        for org_id in sole_orgs:
            org = await ctx.db.get(Organization, org_id)
            if org is not None:
                await _delete_org(ctx, org)
        await audit.record(ctx, "privacy.account_deleted", actor_id=user.id)
        await ctx.db.execute(delete(User).where(User.id == user.id))
    finally:
        await disable_system_access(ctx.db)
    log.info("account_deleted", user_id=str(user.id), clubs_deleted=len(sole_orgs))


async def _delete_org(ctx: Ctx, org: Organization) -> int:
    if org.stripe_subscription_id and org.subscription_status in ("active", "trialing", "past_due"):
        raise ProblemError(409, "subscription-active", "Cancel the subscription first")
    prefix = f"{org.id}/"
    removed = 0
    for bucket in (ctx.settings.s3_bucket_videos, ctx.settings.s3_bucket_artifacts):
        removed += await ctx.storage.delete_prefix(bucket, prefix)
    await ctx.db.execute(delete(Organization).where(Organization.id == org.id))
    return removed


async def delete_org(ctx: Ctx, confirm_name: str) -> int:
    actor = ctx.require_actor()
    authorize(actor, Action.TEAM_DELETE, two_factor=ctx.two_factor)
    org = await ctx.db.get(Organization, actor.organization_id)
    if org is None:
        raise ProblemError(404, "not-found", "Organisation not found")
    if confirm_name.strip() != org.name:
        raise ProblemError(422, "confirmation-mismatch", "Type the club name to confirm")
    await audit.record(ctx, "privacy.org_deleted", org_id=None, data={"org": str(org.id)})
    await enable_system_access(ctx.db, reason="club deletion by its admin")
    try:
        removed = await _delete_org(ctx, org)
    finally:
        await disable_system_access(ctx.db)
    log.info("org_deleted", org_id=str(org.id), objects=removed)
    return removed
