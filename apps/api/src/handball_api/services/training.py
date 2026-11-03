"""Assignments for players and in-app notifications (M7)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update

from handball_api.core.errors import ProblemError
from handball_api.core.logging import get_logger
from handball_api.models import (
    Assignment,
    AssignmentStatus,
    Match,
    Membership,
    Notification,
    Play,
    Playlist,
    Team,
    User,
)
from handball_api.models.enums import TeamRole
from handball_api.schemas.training import AssignmentCreate, AssignmentOut, NotificationList
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.mail_templates import render
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action

log = get_logger("handball_api.training")
RECEIVERS = (TeamRole.PLAYER, TeamRole.GOALKEEPER)


def _now() -> datetime:
    return datetime.now(UTC)


async def notify(
    ctx: Ctx,
    org_id: uuid.UUID,
    user_ids: list[uuid.UUID],
    kind: str,
    params: dict[str, Any],
    link: str | None,
) -> None:
    for uid in dict.fromkeys(user_ids):
        ctx.db.add(
            Notification(organization_id=org_id, user_id=uid, kind=kind, params=params, link=link)
        )


async def staff_of(ctx: Ctx, team_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        (
            await ctx.db.scalars(
                select(Membership.user_id).where(
                    Membership.team_id == team_id,
                    Membership.role.in_([TeamRole.COACH, TeamRole.ANALYST]),
                )
            )
        ).all()
    )


def _link(org_id: uuid.UUID, a: Assignment) -> str:
    base = f"/app/{org_id}"
    return {
        "playlist": f"{base}/playlists/{a.target_id}",
        "play": f"{base}/plays/{a.target_id}",
        "match": f"{base}/matches/{a.target_id}",
        "drill": f"{base}/drills#{a.target_id}",
    }.get(a.kind, f"{base}/assignments")


async def _check_target(ctx: Ctx, team: Team, kind: str, target_id: str) -> None:
    """The target must belong to the team; playlists and plays become visible to players."""
    if kind == "drill":
        return
    try:
        tid = uuid.UUID(target_id)
    except ValueError as exc:
        raise ProblemError(422, "validation", "Unknown target") from exc
    row: Playlist | Play | Match | None
    if kind == "playlist":
        row = await ctx.db.get(Playlist, tid)
    elif kind == "play":
        row = await ctx.db.get(Play, tid)
    else:
        row = await ctx.db.get(Match, tid)
    if row is None or row.team_id != team.id:
        raise ProblemError(422, "validation", "The target belongs to another team")
    if isinstance(row, Playlist | Play):
        row.shared_with_players = True


async def create_assignment(ctx: Ctx, team_id: uuid.UUID, data: AssignmentCreate) -> Assignment:
    team = await get_team(ctx, team_id, Action.ASSIGNMENT_WRITE)
    await _check_target(ctx, team, data.kind, data.target_id)
    members = dict(
        (
            await ctx.db.execute(
                select(Membership.user_id, Membership.role).where(
                    Membership.team_id == team.id, Membership.role.in_(RECEIVERS)
                )
            )
        ).all()
    )
    recipients = list(data.user_ids) or list(members)
    if any(uid not in members for uid in recipients):
        raise ProblemError(422, "validation", "Recipients must be players of the team")
    if not recipients:
        raise ProblemError(409, "no-recipients", "The team has no players with an account yet")
    a = Assignment(
        organization_id=team.organization_id,
        team_id=team.id,
        kind=data.kind,
        target_id=data.target_id,
        title=data.title,
        note=data.note,
        due_at=data.due_at,
        created_by_id=ctx.user_id,
    )
    ctx.db.add(a)
    await ctx.db.flush()
    for uid in recipients:
        ctx.db.add(
            AssignmentStatus(organization_id=team.organization_id, assignment_id=a.id, user_id=uid)
        )
    link = _link(team.organization_id, a)
    await notify(
        ctx,
        team.organization_id,
        recipients,
        "assignment",
        {"title": a.title, "team": team.name, "due_at": a.due_at.isoformat() if a.due_at else None},
        link,
    )
    if data.notify_email:
        coach = await ctx.db.get(User, ctx.user_id) if ctx.user_id else None
        users = (await ctx.db.scalars(select(User).where(User.id.in_(recipients)))).all()
        for u in users:
            due = f" Bis {a.due_at:%d.%m.%Y}." if a.due_at and u.locale == "de-CH" else ""
            if a.due_at and u.locale != "de-CH":
                due = f" {a.due_at:%Y-%m-%d}."
            try:
                await ctx.email.send(
                    render(
                        "assignment",
                        u.locale,
                        to=u.email,
                        name=u.name,
                        coach=coach.name if coach else team.name,
                        team=team.name,
                        title=a.title,
                        due=due,
                        link=f"{ctx.settings.web_base_url}{link}",
                    )
                )
            except Exception:
                log.warning("assignment_mail_failed", user_id=str(u.id))
    await audit.record(
        ctx,
        "assignment.created",
        target_type="assignment",
        target_id=a.id,
        data={"recipients": len(recipients)},
    )
    return a


async def _counts(ctx: Ctx, ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[int, int]]:
    if not ids:
        return {}
    rows = (
        await ctx.db.execute(
            select(
                AssignmentStatus.assignment_id,
                func.count(AssignmentStatus.id),
                func.count(AssignmentStatus.done_at),
            )
            .where(AssignmentStatus.assignment_id.in_(ids))
            .group_by(AssignmentStatus.assignment_id)
        )
    ).all()
    return {aid: (n, done) for aid, n, done in rows}


def _out(a: Assignment, counts: tuple[int, int], **extra: Any) -> AssignmentOut:
    return AssignmentOut(
        id=a.id,
        team_id=a.team_id,
        kind=a.kind,
        target_id=a.target_id,
        title=a.title,
        note=a.note,
        due_at=a.due_at,
        created_at=a.created_at,
        recipients=counts[0],
        done=counts[1],
        **extra,
    )


async def team_assignments(ctx: Ctx, team_id: uuid.UUID) -> list[AssignmentOut]:
    team = await get_team(ctx, team_id, Action.ASSIGNMENT_WRITE)
    rows = list(
        (
            await ctx.db.scalars(
                select(Assignment)
                .where(Assignment.team_id == team.id)
                .order_by(Assignment.created_at.desc())
                .limit(100)
            )
        ).all()
    )
    counts = await _counts(ctx, [a.id for a in rows])
    progress: dict[uuid.UUID, list[dict[str, Any]]] = {}
    if rows:
        for st, name in (
            await ctx.db.execute(
                select(AssignmentStatus, User.name)
                .join(User, User.id == AssignmentStatus.user_id)
                .where(AssignmentStatus.assignment_id.in_([a.id for a in rows]))
                .order_by(User.name)
            )
        ).all():
            progress.setdefault(st.assignment_id, []).append(
                {
                    "user_id": str(st.user_id),
                    "name": name,
                    "seen_at": st.seen_at,
                    "done_at": st.done_at,
                }
            )
    return [_out(a, counts.get(a.id, (0, 0)), progress=progress.get(a.id, [])) for a in rows]


async def my_assignments(ctx: Ctx) -> list[AssignmentOut]:
    rows = (
        await ctx.db.execute(
            select(Assignment, AssignmentStatus, Team.name)
            .join(AssignmentStatus, AssignmentStatus.assignment_id == Assignment.id)
            .join(Team, Team.id == Assignment.team_id)
            .where(AssignmentStatus.user_id == ctx.user_id)
            .order_by(AssignmentStatus.done_at.is_not(None), Assignment.due_at.asc().nulls_last())
            .limit(100)
        )
    ).all()
    counts = await _counts(ctx, [a.id for a, _, _ in rows])
    return [
        _out(a, counts.get(a.id, (0, 0)), seen_at=st.seen_at, done_at=st.done_at, team_name=team)
        for a, st, team in rows
    ]


async def set_status(ctx: Ctx, assignment_id: uuid.UUID, done: bool) -> AssignmentOut:
    st = await ctx.db.scalar(
        select(AssignmentStatus).where(
            AssignmentStatus.assignment_id == assignment_id, AssignmentStatus.user_id == ctx.user_id
        )
    )
    a = await ctx.db.get(Assignment, assignment_id)
    if st is None or a is None:
        raise ProblemError(404, "not-found", "Assignment not found")
    now = _now()
    st.seen_at = st.seen_at or now
    was_done = st.done_at is not None
    st.done_at = now if done else None
    if done and not was_done:
        me = await ctx.db.get(User, ctx.user_id)
        await notify(
            ctx,
            a.organization_id,
            await staff_of(ctx, a.team_id),
            "assignment_done",
            {"title": a.title, "name": me.name if me else ""},
            f"/app/{a.organization_id}/teams/{a.team_id}/assignments",
        )
    await ctx.db.flush()
    counts = await _counts(ctx, [a.id])
    return _out(a, counts.get(a.id, (0, 0)), seen_at=st.seen_at, done_at=st.done_at)


async def delete_assignment(ctx: Ctx, assignment_id: uuid.UUID) -> None:
    a = await ctx.db.get(Assignment, assignment_id)
    if a is None:
        raise ProblemError(404, "not-found", "Assignment not found")
    await get_team(ctx, a.team_id, Action.ASSIGNMENT_WRITE)
    await ctx.db.delete(a)


async def notifications(ctx: Ctx) -> NotificationList:
    base = Notification.user_id == ctx.user_id
    items = (
        await ctx.db.scalars(
            select(Notification).where(base).order_by(Notification.created_at.desc()).limit(50)
        )
    ).all()
    unread = await ctx.db.scalar(
        select(func.count(Notification.id)).where(base, Notification.read_at.is_(None))
    )
    return NotificationList.model_validate(
        {"unread": unread or 0, "items": [n for n in items]}, from_attributes=True
    )


async def mark_read(ctx: Ctx, ids: list[uuid.UUID]) -> None:
    stmt = update(Notification).where(
        Notification.user_id == ctx.user_id, Notification.read_at.is_(None)
    )
    if ids:
        stmt = stmt.where(Notification.id.in_(ids))
    await ctx.db.execute(stmt.values(read_at=_now()))
