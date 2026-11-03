"""Lean training planning (addendum 01, 5.7): sessions from drills as PDF, attendance for sessions
and matches (players and parents reply, staff record), a subscribable calendar feed (ICS) and ICS
import of sessions. Spond and ClubCorner sit behind the TeamOpsAdapter (ADR 018)."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import select

from handball_api.core.db import disable_system_access, enable_system_access, set_tenant
from handball_api.core.errors import ProblemError
from handball_api.core.security import hash_token, new_token
from handball_api.integrations.team_ops import CalendarEntry, IcsTeamOps
from handball_api.models import (
    Attendance,
    Guardianship,
    Match,
    Opponent,
    Player,
    RosterEntry,
    Season,
    Team,
    TrainingSession,
)
from handball_api.models.enums import AttendanceStatus
from handball_api.schemas.sessions import (
    AttendanceRecord,
    MyReply,
    TrainingSessionIn,
)
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action
from handball_api.services.report_pdf import TEXTS, _esc, _styles

MAX_ICS_BYTES = 1024 * 1024


def _now() -> datetime:
    return datetime.now(UTC)


# ---- sessions -----------------------------------------------------------------------------------


async def list_sessions(
    ctx: Ctx, team_id: uuid.UUID, start: date | None = None, end: date | None = None
) -> list[TrainingSession]:
    await get_team(ctx, team_id, Action.TEAM_READ)
    stmt = select(TrainingSession).where(TrainingSession.team_id == team_id)
    if start:
        stmt = stmt.where(TrainingSession.on_date >= start)
    if end:
        stmt = stmt.where(TrainingSession.on_date <= end)
    return list((await ctx.db.scalars(stmt.order_by(TrainingSession.on_date))).all())


async def _session(ctx: Ctx, session_id: uuid.UUID, action: Action) -> TrainingSession:
    s = await ctx.db.get(TrainingSession, session_id)
    if s is None:
        raise ProblemError(404, "not-found", "Session not found")
    await get_team(ctx, s.team_id, action)
    return s


async def get_session(ctx: Ctx, session_id: uuid.UUID) -> TrainingSession:
    return await _session(ctx, session_id, Action.TEAM_READ)


def _apply(s: TrainingSession, data: TrainingSessionIn) -> None:
    s.on_date = data.on_date
    s.starts_at = data.starts_at
    s.title = data.title
    s.location = data.location
    s.notes = data.notes
    s.drills = [d.model_dump() for d in data.drills]


async def create_session(ctx: Ctx, team_id: uuid.UUID, data: TrainingSessionIn) -> TrainingSession:
    team = await get_team(ctx, team_id, Action.TRAINING_WRITE)
    s = TrainingSession(organization_id=team.organization_id, team_id=team.id, on_date=data.on_date)
    _apply(s, data)
    ctx.db.add(s)
    await ctx.db.flush()
    await audit.record(
        ctx, "training_session.created", target_type="training_session", target_id=s.id
    )
    return s


async def update_session(
    ctx: Ctx, session_id: uuid.UUID, data: TrainingSessionIn
) -> TrainingSession:
    s = await _session(ctx, session_id, Action.TRAINING_WRITE)
    _apply(s, data)
    return s


async def delete_session(ctx: Ctx, session_id: uuid.UUID) -> None:
    await ctx.db.delete(await _session(ctx, session_id, Action.TRAINING_WRITE))


def total_minutes(s: TrainingSession) -> int:
    return sum(int(d.get("minutes") or 0) for d in s.drills)


async def session_pdf(ctx: Ctx, session_id: uuid.UUID, lang: str) -> tuple[bytes, str]:
    s = await get_session(ctx, session_id)
    team = await ctx.db.get(Team, s.team_id)
    t = TEXTS.get(lang, TEXTS["de-CH"])["session"]
    st = _styles()
    when = s.on_date.strftime("%d.%m.%Y")
    if s.starts_at:
        when += s.starts_at.astimezone(_zurich()).strftime(", %H:%M")
    story: list[Any] = [
        Paragraph(_esc(s.title or t["title"]), st["h1"]),
        Paragraph(
            _esc(
                f"{team.name if team else ''} · {when}" + (f" · {s.location}" if s.location else "")
            ),
            st["muted"],
        ),
        Paragraph(_esc(t["total"].format(minutes=total_minutes(s))), st["base"]),
        Spacer(1, 4 * mm),
    ]
    if not s.drills:
        story.append(Paragraph(_esc(t["none"]), st["base"]))
    for i, d in enumerate(s.drills, start=1):
        block = [
            Paragraph(
                _esc(
                    f"{i}. {d.get('name') or d.get('drill_id')} ({d.get('minutes')} {t['minutes']})"
                ),
                st["h2"],
            )
        ]
        for key in ("setup", "coaching", "note"):
            if d.get(key):
                block.append(Paragraph(f"<b>{_esc(t[key])}:</b> {_esc(d[key])}", st["base"]))
        story.append(KeepTogether(block))
    if s.notes:
        story += [Paragraph(_esc(t["notes"]), st["h2"]), Paragraph(_esc(s.notes), st["base"])]
    buf = io.BytesIO()
    SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=s.title or t["title"],
    ).build(story)
    return buf.getvalue(), f"training-{s.on_date.isoformat()}.pdf"


def _zurich() -> Any:
    from zoneinfo import ZoneInfo

    return ZoneInfo("Europe/Zurich")


# ---- attendance ---------------------------------------------------------------------------------


async def _target(ctx: Ctx, kind: str, target_id: uuid.UUID) -> tuple[Team, uuid.UUID, date]:
    """Team, season and day of a session or match."""
    if kind == "session":
        s = await ctx.db.get(TrainingSession, target_id)
        if s is None:
            raise ProblemError(404, "not-found", "Session not found")
        team = await ctx.db.get(Team, s.team_id)
        assert team is not None
        season = await _season_for(ctx, team.id, s.on_date)
        return team, season, s.on_date
    m = await ctx.db.get(Match, target_id)
    if m is None:
        raise ProblemError(404, "not-found", "Match not found")
    team = await ctx.db.get(Team, m.team_id)
    assert team is not None
    return team, m.season_id, m.kickoff_at.date()


async def _season_for(ctx: Ctx, team_id: uuid.UUID, day: date) -> uuid.UUID:
    seasons = (await ctx.db.scalars(select(Season).where(Season.team_id == team_id))).all()
    for s in seasons:
        if s.starts_on <= day <= s.ends_on:
            return s.id
    if not seasons:
        raise ProblemError(422, "no-season", "The team has no season")
    return max(seasons, key=lambda s: s.starts_on).id


def _where(kind: str, target_id: uuid.UUID) -> Any:
    return (
        Attendance.session_id == target_id
        if kind == "session"
        else Attendance.match_id == target_id
    )


async def attendance(ctx: Ctx, kind: str, target_id: uuid.UUID) -> list[dict[str, Any]]:
    """The roster with reply and recorded status (staff)."""
    team, season, _ = await _target(ctx, kind, target_id)
    await get_team(ctx, team.id, Action.TRAINING_WRITE)
    roster = (
        await ctx.db.execute(
            select(Player, RosterEntry.jersey_number)
            .join(RosterEntry, RosterEntry.player_id == Player.id)
            .where(RosterEntry.season_id == season, RosterEntry.team_id == team.id)
            .order_by(RosterEntry.jersey_number.nulls_last(), Player.last_name)
        )
    ).all()
    rows = {
        a.player_id: a
        for a in (await ctx.db.scalars(select(Attendance).where(_where(kind, target_id)))).all()
    }
    out = []
    for p, number in roster:
        a = rows.get(p.id)
        out.append(
            {
                "player_id": p.id,
                "name": f"{p.first_name} {p.last_name}".strip(),
                "number": number,
                "response": a.response if a else None,
                "status": a.status if a else None,
                "reason": a.reason if a else None,
            }
        )
    return out


async def _row(
    ctx: Ctx, team: Team, kind: str, target_id: uuid.UUID, player_id: uuid.UUID
) -> Attendance:
    a = await ctx.db.scalar(
        select(Attendance).where(_where(kind, target_id), Attendance.player_id == player_id)
    )
    if a is None:
        a = Attendance(
            organization_id=team.organization_id,
            player_id=player_id,
            session_id=target_id if kind == "session" else None,
            match_id=target_id if kind == "match" else None,
        )
        ctx.db.add(a)
    return a


async def record(
    ctx: Ctx, kind: str, target_id: uuid.UUID, records: list[AttendanceRecord]
) -> list[dict[str, Any]]:
    team, season, _ = await _target(ctx, kind, target_id)
    await get_team(ctx, team.id, Action.TRAINING_WRITE)
    allowed = set(
        (
            await ctx.db.scalars(
                select(RosterEntry.player_id).where(
                    RosterEntry.season_id == season, RosterEntry.team_id == team.id
                )
            )
        ).all()
    )
    for r in records:
        if r.player_id not in allowed:
            raise ProblemError(422, "not-in-roster", "The player is not in this team's roster")
        a = await _row(ctx, team, kind, target_id, r.player_id)
        a.status = AttendanceStatus(r.status) if r.status else None
        a.reason = r.reason
    await ctx.db.flush()
    return await attendance(ctx, kind, target_id)


async def _my_players(ctx: Ctx) -> dict[uuid.UUID, str]:
    if ctx.user_id is None:
        raise ProblemError(401, "unauthenticated", "Sign in first")
    own = (await ctx.db.scalars(select(Player.id).where(Player.user_id == ctx.user_id))).all()
    kids = (
        await ctx.db.scalars(
            select(Guardianship.player_id).where(Guardianship.user_id == ctx.user_id)
        )
    ).all()
    out = {pid: "guardian" for pid in kids}
    out.update({pid: "self" for pid in own})
    return out


async def my_schedule(ctx: Ctx, days: int = 30) -> list[dict[str, Any]]:
    """Upcoming sessions and matches of the players I am or I am a parent of, with my replies."""
    mine = await _my_players(ctx)
    if not mine:
        return []
    today = _now().date()
    entries = (
        await ctx.db.execute(
            select(RosterEntry.player_id, RosterEntry.team_id, RosterEntry.season_id).where(
                RosterEntry.player_id.in_(list(mine))
            )
        )
    ).all()
    players = {
        p.id: p
        for p in (await ctx.db.scalars(select(Player).where(Player.id.in_(list(mine))))).all()
    }
    teams = {e.team_id for e in entries}
    team_names = {
        t.id: t.name for t in (await ctx.db.scalars(select(Team).where(Team.id.in_(teams)))).all()
    }
    sessions = (
        await ctx.db.scalars(
            select(TrainingSession).where(
                TrainingSession.team_id.in_(teams),
                TrainingSession.on_date >= today,
                TrainingSession.on_date <= today + timedelta(days=days),
            )
        )
    ).all()
    matches = (
        await ctx.db.scalars(
            select(Match).where(
                Match.team_id.in_(teams),
                Match.kickoff_at >= datetime.combine(today, datetime.min.time(), UTC),
                Match.kickoff_at
                <= datetime.combine(today + timedelta(days=days), datetime.min.time(), UTC),
            )
        )
    ).all()
    opponents = {
        o.id: o.name
        for o in (
            await ctx.db.scalars(
                select(Opponent).where(
                    Opponent.id.in_([m.opponent_id for m in matches if m.opponent_id])
                )
            )
        ).all()
    }
    replies = {
        (a.session_id or a.match_id, a.player_id): a
        for a in (
            await ctx.db.scalars(select(Attendance).where(Attendance.player_id.in_(list(mine))))
        ).all()
    }
    out: list[dict[str, Any]] = []
    for e in entries:
        p = players[e.player_id]
        for s in sessions:
            if s.team_id == e.team_id:
                a = replies.get((s.id, p.id))
                out.append(
                    _item(
                        "session",
                        s.id,
                        s.title,
                        team_names[s.team_id],
                        s.on_date,
                        s.starts_at,
                        p,
                        mine[p.id],
                        a,
                    )
                )
        for m in matches:
            if m.team_id == e.team_id and m.season_id == e.season_id:
                a = replies.get((m.id, p.id))
                title = opponents.get(m.opponent_id) if m.opponent_id else None
                out.append(
                    _item(
                        "match",
                        m.id,
                        title,
                        team_names[m.team_id],
                        m.kickoff_at.date(),
                        m.kickoff_at,
                        p,
                        mine[p.id],
                        a,
                    )
                )
    out.sort(
        key=lambda i: (
            i["on_date"],
            i["starts_at"].isoformat() if i["starts_at"] else "",
            i["player_name"],
        )
    )
    return out


def _item(
    kind: str,
    target_id: uuid.UUID,
    title: str | None,
    team: str,
    on_date: date,
    starts_at: datetime | None,
    p: Player,
    relation: str,
    a: Attendance | None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "id": target_id,
        "title": title,
        "team": team,
        "on_date": on_date,
        "starts_at": starts_at,
        "player_id": p.id,
        "player_name": p.first_name,
        "relation": relation,
        "response": a.response if a else None,
    }


async def reply(ctx: Ctx, data: MyReply) -> dict[str, Any]:
    mine = await _my_players(ctx)
    if data.player_id not in mine:
        raise ProblemError(403, "forbidden", "You can only reply for yourself or your children")
    team, season, day = await _target(ctx, data.kind, data.id)
    in_roster = await ctx.db.scalar(
        select(RosterEntry.id).where(
            RosterEntry.player_id == data.player_id,
            RosterEntry.team_id == team.id,
            RosterEntry.season_id == season,
        )
    )
    if not in_roster:
        raise ProblemError(403, "forbidden", "Not in this team")
    if day < _now().date():
        raise ProblemError(422, "in-the-past", "Replies are only possible before the date")
    a = await _row(ctx, team, data.kind, data.id, data.player_id)
    a.response = data.response
    a.responded_at = _now()
    if data.reason is not None:
        a.reason = data.reason
    await ctx.db.flush()
    return {"response": a.response}


# ---- calendar -----------------------------------------------------------------------------------


async def new_calendar_token(ctx: Ctx, team_id: uuid.UUID) -> str:
    team = await get_team(ctx, team_id, Action.TRAINING_WRITE)
    token = new_token(24)
    team.calendar_token_hash = hash_token(token)
    await audit.record(ctx, "team.calendar_token", target_type="team", target_id=team.id)
    return token


async def revoke_calendar(ctx: Ctx, team_id: uuid.UUID) -> None:
    team = await get_team(ctx, team_id, Action.TRAINING_WRITE)
    team.calendar_token_hash = None


async def calendar_ics(ctx: Ctx, token: str) -> str:
    """Public feed for calendar apps (no session): matches and sessions of one team."""
    await enable_system_access(ctx.db, reason="calendar feed lookup")
    team = await ctx.db.scalar(select(Team).where(Team.calendar_token_hash == hash_token(token)))
    await disable_system_access(ctx.db)
    if team is None:
        raise ProblemError(404, "not-found", "This calendar link is no longer valid")
    await set_tenant(ctx.db, team.organization_id)
    since = _now() - timedelta(days=60)
    matches = (
        await ctx.db.scalars(
            select(Match).where(Match.team_id == team.id, Match.kickoff_at >= since)
        )
    ).all()
    opponents = {
        o.id: o.name
        for o in (
            await ctx.db.scalars(
                select(Opponent).where(
                    Opponent.id.in_([m.opponent_id for m in matches if m.opponent_id])
                )
            )
        ).all()
    }
    entries = [
        CalendarEntry(
            uid=f"match-{m.id}@handball-ai",
            title=_match_title(team.name, opponents.get(m.opponent_id) if m.opponent_id else None),
            starts_at=m.kickoff_at,
            ends_at=m.kickoff_at + timedelta(seconds=m.period_s * m.periods + 900),
            location=m.venue,
        )
        for m in matches
    ]
    sessions = (
        await ctx.db.scalars(
            select(TrainingSession).where(
                TrainingSession.team_id == team.id, TrainingSession.on_date >= since.date()
            )
        )
    ).all()
    for s in sessions:
        minutes = total_minutes(s) or 90
        start: datetime | date = s.starts_at or s.on_date
        entries.append(
            CalendarEntry(
                uid=f"session-{s.id}@handball-ai",
                title=f"{team.name}: {s.title or 'Training'}",
                starts_at=start,
                ends_at=s.starts_at + timedelta(minutes=minutes) if s.starts_at else None,
                location=s.location,
            )
        )
    return IcsTeamOps().export_events(entries, team.name)


def _match_title(team: str, opponent: str | None) -> str:
    return f"{team} - {opponent}" if opponent else team


async def import_ics(ctx: Ctx, team_id: uuid.UUID, data: bytes) -> dict[str, int]:
    """Sessions from an ICS file (e.g. exported from Spond or a club calendar); known UIDs are
    updated, not duplicated."""
    team = await get_team(ctx, team_id, Action.TRAINING_WRITE)
    if len(data) > MAX_ICS_BYTES:
        raise ProblemError(413, "file-too-large", "The calendar file is larger than 1 MB")
    try:
        entries = IcsTeamOps().import_events(data.decode("utf-8", errors="replace"))
    except ValueError as exc:
        raise ProblemError(422, "invalid-format", "Not a readable calendar file") from exc
    existing = {
        s.external_ref: s
        for s in (
            await ctx.db.scalars(
                select(TrainingSession).where(
                    TrainingSession.team_id == team.id, TrainingSession.external_ref.is_not(None)
                )
            )
        ).all()
    }
    created = updated = 0
    for e in entries[:500]:
        day = e.starts_at.date() if isinstance(e.starts_at, datetime) else e.starts_at
        starts = e.starts_at if isinstance(e.starts_at, datetime) else None
        s = existing.get(e.uid)
        if s is None:
            s = TrainingSession(
                organization_id=team.organization_id,
                team_id=team.id,
                on_date=day,
                external_ref=e.uid[:200],
            )
            ctx.db.add(s)
            created += 1
        else:
            updated += 1
        s.on_date, s.starts_at = day, starts
        s.title = (e.title or "")[:120] or None
        s.location = (e.location or "")[:160] or None
    await ctx.db.flush()
    return {"created": created, "updated": updated}
