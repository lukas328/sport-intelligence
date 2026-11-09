"""From a problem to training (addendum 01, 5.6).

An insight of a match becomes a training focus with one click: a session with drills for its
topic, a playlist with the evidence scenes and an assignment for the team. The metric behind the
insight is then followed over the next matches and shown as "before and after", labelled as an
observation, not as proof of the training's effect (P3).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.models import (
    Clip,
    Event,
    FocusPlan,
    Match,
    Playlist,
    PlaylistItem,
    RosterEntry,
    TrainingSession,
)
from handball_api.models.enums import ClipSource
from handball_api.schemas.focus import FocusIn
from handball_api.schemas.training import AssignmentCreate
from handball_api.services import audit
from handball_api.services import insights as insights_service
from handball_api.services import training as training_service
from handball_api.services.context import Ctx
from handball_api.services.events import _to_metric
from handball_api.services.matches import clip_window, get_match, in_video, video_duration_ms
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action
from handball_api.services.team_data import load
from handball_metrics.query import METRICS, Filter, compute
from handball_metrics.query import select as select_rows
from handball_metrics.stats import zone_of

BEFORE_MATCHES = 5
MIN_SAMPLE = 10  # below this, before/after is shown but marked as too small to read anything into
PRE_MS, POST_MS = 5000, 3000

# insight key -> metric followed afterwards, base filter, higher is better, training topics
FOLLOW: dict[str, tuple[str, dict[str, Any], bool, list[str]]] = {
    "shooting_below": ("shooting_pct", {"side": "own"}, True, ["finishing"]),
    "drought": ("shooting_pct", {"side": "own"}, True, ["finishing"]),
    "seven_m_low": ("seven_m_pct", {"side": "own"}, True, ["seven_m"]),
    "saves_below": ("save_pct", {"side": "opponent"}, True, ["goalkeeping"]),
    "keeper_bad": ("save_pct", {"side": "opponent"}, True, ["goalkeeping"]),
    "turnovers_high": ("turnovers", {"side": "own"}, False, ["passing"]),
    "fast_breaks_against": (
        "fast_break_goals",
        {"side": "opponent"},
        False,
        ["transition_defence"],
    ),
    "conceded_zone": ("goals", {"side": "opponent"}, False, ["goalkeeping"]),
    "zone_weak": ("shooting_pct", {"side": "own"}, True, ["finishing"]),
    "player_inefficient": ("shooting_pct", {"side": "own"}, True, ["finishing"]),
    "powerplay_weak": ("shooting_pct", {"side": "own"}, True, ["powerplay"]),
}


def _rule(key: str) -> str:
    rule = key.removeprefix("insights.")
    return "zone_weak" if rule.startswith("zone_") and rule.endswith("weak") else rule


def follow_for(
    key: str, params: dict[str, Any], number: int | None = None
) -> tuple[str, dict[str, Any], bool, list[str]] | None:
    """Metric, filter, direction and topics for an insight (None: nothing to follow)."""
    rule = _rule(key)
    if rule not in FOLLOW:
        return None
    metric, base, higher, topics = FOLLOW[rule]
    f = dict(base)
    zone = params.get("zone")
    if zone and rule in ("zone_weak", "conceded_zone"):
        f["zone"] = zone
        if rule == "zone_weak":
            topics = (
                ["wings"]
                if str(zone).startswith("wing")
                else ["pivot"]
                if str(zone).startswith("circle")
                else ["back_court"]
                if str(zone).startswith(("back", "half"))
                else topics
            )
    if rule == "player_inefficient":
        if number is None:
            return None
        f["number"] = number
    return metric, f, higher, topics


async def _insight(ctx: Ctx, match: Match, key: str, params: dict[str, Any]) -> dict[str, Any]:
    result = await insights_service.insights(ctx, match.id)
    for item in result["insights"]:
        if item.get("key") == key and (item.get("params") or {}) == params:
            return dict(item)
    raise ProblemError(422, "unknown-insight", "This insight is not part of the match")


def _matches_evidence(e: Event, evidence: dict[str, Any], numbers: dict[uuid.UUID, int]) -> bool:
    for k, v in evidence.items():
        if k == "zone":
            if zone_of(_to_metric(e)) != v:
                return False
        elif k == "player_id":
            if str(e.player_id) != str(v):
                return False
        elif k == "number":
            if (
                e.number if e.number is not None else numbers.get(e.player_id or uuid.uuid4())
            ) != v:
                return False
        elif getattr(e, k, None) != v:
            return False
    return True


async def create(ctx: Ctx, match_id: uuid.UUID, data: FocusIn) -> FocusPlan:
    match = await get_match(ctx, match_id, Action.TRAINING_WRITE)
    team = await get_team(ctx, match.team_id, Action.TRAINING_WRITE)
    item = await _insight(ctx, match, data.insight_key, data.params)
    numbers = {
        r.player_id: r.jersey_number
        for r in (
            await ctx.db.scalars(
                select(RosterEntry).where(RosterEntry.season_id == match.season_id)
            )
        ).all()
        if r.jersey_number is not None
    }
    number = data.params.get("number")
    if number is None and data.params.get("player_id"):
        try:
            number = numbers.get(uuid.UUID(str(data.params["player_id"])))
        except ValueError:
            number = None
    follow = follow_for(data.insight_key, data.params, number)
    plan = FocusPlan(
        organization_id=team.organization_id,
        team_id=team.id,
        match_id=match.id,
        insight_key=data.insight_key,
        params=data.params,
        focus=follow[3] if follow else [],
        metric=follow[0] if follow else None,
        filter=follow[1] if follow else {},
        higher_is_better=follow[2] if follow else True,
        created_by_id=ctx.user_id,
    )
    ctx.db.add(plan)
    title = data.title or data.insight_key.removeprefix("insights.")
    if data.session is not None:
        s = TrainingSession(
            organization_id=team.organization_id,
            team_id=team.id,
            on_date=data.session.on_date,
            starts_at=data.session.starts_at,
            title=title[:120],
            drills=[d.model_dump() for d in data.session.drills],
        )
        ctx.db.add(s)
        await ctx.db.flush()
        plan.session_id = s.id
    if data.playlist:
        events = (
            await ctx.db.scalars(
                select(Event).where(Event.match_id == match.id, Event.t_ms.is_not(None))
            )
        ).all()
        evidence = dict(item.get("evidence") or {})
        # events before or after the video (a clip of part of the game) have nothing to show
        duration = await video_duration_ms(ctx, match)
        hits = [
            e
            for e in events
            if in_video(e.t_ms, duration) and _matches_evidence(e, evidence, numbers)
        ][:40]
        pl = Playlist(
            organization_id=team.organization_id,
            team_id=team.id,
            title=title[:200],
            created_by_id=ctx.user_id,
            shared_with_players=True,
        )
        ctx.db.add(pl)
        await ctx.db.flush()
        for pos, e in enumerate(sorted(hits, key=lambda x: x.t_ms or 0)):
            assert e.t_ms is not None
            start, end = clip_window(e.t_ms, PRE_MS, POST_MS, duration)
            clip = Clip(
                organization_id=team.organization_id,
                match_id=match.id,
                start_ms=start,
                end_ms=end,
                title=title[:200],
                source=ClipSource.EVENT,
                source_ref=e.id,
                created_by_id=ctx.user_id,
            )
            ctx.db.add(clip)
            await ctx.db.flush()
            ctx.db.add(
                PlaylistItem(
                    organization_id=team.organization_id,
                    playlist_id=pl.id,
                    clip_id=clip.id,
                    position=pos,
                )
            )
        await ctx.db.flush()
        plan.playlist_id = pl.id
        if data.assignment:
            try:
                a = await training_service.create_assignment(
                    ctx,
                    team.id,
                    AssignmentCreate(
                        kind="playlist",
                        target_id=str(pl.id),
                        title=title[:200],
                        note=data.note,
                        user_ids=[],
                        notify_email=False,
                    ),
                )
                plan.assignment_id = a.id
            except ProblemError as exc:
                # no player has an account yet: the focus and playlist still help the staff
                if exc.code != "no-recipients":
                    raise
    await ctx.db.flush()
    await audit.record(ctx, "focus_plan.created", target_type="focus_plan", target_id=plan.id)
    return plan


async def plans(ctx: Ctx, team_id: uuid.UUID) -> list[dict[str, Any]]:
    team = await get_team(ctx, team_id, Action.TEAM_READ)
    items = (
        await ctx.db.scalars(
            select(FocusPlan)
            .where(FocusPlan.team_id == team.id)
            .order_by(FocusPlan.created_at.desc())
        )
    ).all()
    if not items:
        return []
    # the seasons since the oldest plan, and the one before (its "before" matches)
    data = await load(ctx, team, since=min(p.created_at for p in items).date())
    with_events = {r.match.id for r in data.rows}
    ordered = sorted(
        (m for m in data.matches.values() if m.id in with_events), key=lambda m: m.date
    )
    out = []
    for p in items:
        out.append({"plan": p, "followup": followup(p, ordered, data.rows)})
    return out


def followup(p: FocusPlan, ordered: list[Any], rows: list[Any]) -> dict[str, Any] | None:
    """Before (up to 5 matches before the plan) and after (matches since) for the plan's metric."""
    if not p.metric or p.metric not in METRICS:
        return None
    start = p.created_at.date().isoformat()
    before = [m.id for m in ordered if m.date < start][-BEFORE_MATCHES:]
    after = [m.id for m in ordered if m.date >= start]
    kind = METRICS[p.metric].kind

    def side(ids: list[str]) -> dict[str, Any]:
        f = Filter.from_dict({**p.filter, "match_ids": ids}) if ids else None
        v = compute(p.metric or "", select_rows(rows, f) if f else [])
        per_match = (
            round(v.value / len(ids), 2)
            if kind != "ratio" and v.value is not None and ids
            else None
        )
        return {
            "matches": len(ids),
            "value": v.value if ids else None,
            "per_match": per_match,
            "sample": v.denominator if kind == "ratio" else v.events,
        }

    b, a = side(before), side(after)
    comparable_b = b["value"] if kind == "ratio" else b["per_match"]
    comparable_a = a["value"] if kind == "ratio" else a["per_match"]
    trend = None
    if comparable_a is not None and comparable_b is not None:
        if comparable_a == comparable_b:
            trend = "same"
        else:
            better = (comparable_a > comparable_b) == p.higher_is_better
            trend = "better" if better else "worse"
    small = min(b["sample"] or 0, a["sample"] or 0) < MIN_SAMPLE
    return {
        "metric": p.metric,
        "before": b,
        "after": a,
        "trend": trend,
        "small_sample": small,
        "note": "observation, not proof of the training's effect",
    }


async def close(ctx: Ctx, plan_id: uuid.UUID) -> FocusPlan:
    p = await ctx.db.get(FocusPlan, plan_id)
    if p is None:
        raise ProblemError(404, "not-found", "Focus not found")
    await get_team(ctx, p.team_id, Action.TRAINING_WRITE)
    p.closed_at = datetime.now(UTC)
    return p
