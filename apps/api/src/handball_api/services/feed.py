"""Player feed "Deine Szenen" with self-assessment first (addendum 01, 4.7).

After every analysis (or on request of the coach) each player with an `analysis` consent and an
account gets up to five scenes: positive and negative mixed, ranked by involvement, importance and
variety. Youth teams always get at least one positive scene. Players see the coach's comments only
after their own self-assessment.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select

from handball_api.core.errors import ProblemError
from handball_api.models import (
    Clip,
    Event,
    Guardianship,
    Match,
    Player,
    PlayerFeedItem,
    RosterEntry,
    SelfAssessment,
    Team,
    VideoAsset,
)
from handball_api.models.enums import ClipSource, ConsentKind, VideoRole, VideoStatus
from handball_api.services import audit, training
from handball_api.services.context import Ctx
from handball_api.services.matches import get_match, opponent_of
from handball_api.services.policies import Action
from handball_api.services.roster import consented

SCENES = 5
PRE_MS = 6000
POST_MS = 3000


@dataclass
class Scene:
    event: Event
    reason: str
    positive: bool
    score: float


def classify(e: Event, player_id: uuid.UUID) -> tuple[str, bool, float] | None:
    """(reason, positive, base weight) of the player's part in an event, or None."""
    pid = str(player_id)
    if e.type == "shot" and e.side == "own" and e.player_id == player_id:
        return {
            "goal": ("goal", True, 3.0),
            "save": ("shot_saved", False, 1.5),
            "miss": ("shot_missed", False, 1.5),
            "post": ("shot_post", False, 1.2),
            "blocked": ("shot_blocked", False, 1.0),
        }.get(e.outcome or "", ("shot", False, 1.0))
    if e.type == "shot" and e.side == "own" and e.assist_player_id == player_id:
        return ("assist", True, 2.5) if e.outcome == "goal" else None
    if e.type == "shot" and e.side == "opponent":
        if (e.attributes or {}).get("goalkeeper_id") == pid:
            if e.outcome == "save":
                return ("save", True, 3.0)
            if e.outcome == "goal":
                return ("goal_against", False, 1.0)
        if (e.attributes or {}).get("blocked_by") == pid and e.outcome == "blocked":
            return ("block", True, 2.5)
        return None
    if e.player_id != player_id:
        return None
    return {
        "steal": ("steal", True, 2.5),
        "turnover": ("turnover", False, 2.0),
        "seven_meter_awarded": ("seven_m_won", True, 2.0),
        "suspension_2min": ("suspension", False, 2.0),
        "foul": ("foul", False, 1.0),
    }.get(e.type)


def _importance(e: Event, match: Match, close: set[uuid.UUID]) -> float:
    """Late in a period and in close phases (score difference ≤ 2) count more."""
    w = 1.0
    if e.clock_s is not None and match.period_s:
        in_period = e.clock_s - (e.period - 1) * match.period_s
        if in_period >= match.period_s * 0.8:
            w += 0.5
    if e.id in close:
        w += 0.5
    return w


def _close_events(events: list[Event]) -> set[uuid.UUID]:
    own = opp = 0
    close: set[uuid.UUID] = set()
    for e in events:
        if abs(own - opp) <= 2:
            close.add(e.id)
        if e.type == "shot" and e.outcome == "goal":
            if e.side == "own":
                own += 1
            else:
                opp += 1
    return close


def select_scenes(scenes: list[Scene], youth: bool, n: int = SCENES) -> list[Scene]:
    """Greedy pick: highest score, but repeats of a reason cost (variety) and the less represented
    side (positive or negative) gets a bonus (mix). Youth: at most two negative scenes and at least
    one positive one; without any positive scene a child gets no feed at all."""
    remaining = sorted(scenes, key=lambda s: -s.score)
    chosen: list[Scene] = []
    reasons: Counter[str] = Counter()
    max_neg = 2 if youth else 3
    while remaining and len(chosen) < n:
        neg = sum(1 for c in chosen if not c.positive)
        pos = len(chosen) - neg
        candidates = [s for s in remaining if s.positive or neg < max_neg]
        if not candidates:
            break

        def effective(s: Scene, neg: int = neg, pos: int = pos) -> float:
            mix = 1.3 if (s.positive and pos <= neg) or (not s.positive and neg < pos) else 1.0
            return s.score * 0.6 ** reasons[s.reason] * mix

        best = max(candidates, key=effective)
        chosen.append(best)
        remaining.remove(best)
        reasons[best.reason] += 1
    if youth and not any(c.positive for c in chosen):
        return []
    return chosen


async def generate(ctx: Ctx, match: Match, notify: bool = True) -> int:
    """(Re)builds the feed of all players of a match. Returns the number of players with scenes."""
    team = await ctx.db.get(Team, match.team_id)
    assert team is not None
    rows = (
        (
            await ctx.db.execute(
                select(Player)
                .join(RosterEntry, RosterEntry.player_id == Player.id)
                .where(RosterEntry.season_id == match.season_id)
            )
        )
        .scalars()
        .all()
    )
    allowed = await consented(ctx, [p.id for p in rows], ConsentKind.ANALYSIS)
    events = list(
        (
            await ctx.db.scalars(
                select(Event)
                .where(Event.match_id == match.id, Event.t_ms.is_not(None))
                .order_by(Event.t_ms)
            )
        ).all()
    )
    close = _close_events(events)
    # drop the previous automatic feed (coach comments on kept scenes are kept below)
    old = {
        (f.player_id, f.clip_id): f
        for f in (
            await ctx.db.scalars(select(PlayerFeedItem).where(PlayerFeedItem.match_id == match.id))
        ).all()
    }
    old_clips = {
        c.source_ref: c
        for c in (
            await ctx.db.scalars(
                select(Clip).where(Clip.match_id == match.id, Clip.source == ClipSource.EVENT)
            )
        ).all()
    }
    await ctx.db.execute(delete(PlayerFeedItem).where(PlayerFeedItem.match_id == match.id))
    recipients: list[uuid.UUID] = []
    players_with_feed = 0
    for p in rows:
        if p.id not in allowed:
            continue
        scenes = []
        for e in events:
            c = classify(e, p.id)
            if c:
                reason, positive, base = c
                scenes.append(Scene(e, reason, positive, base * _importance(e, match, close)))
        chosen = select_scenes(scenes, team.is_youth)
        if not chosen:
            continue
        players_with_feed += 1
        for rank, s in enumerate(chosen, start=1):
            clip = old_clips.get(s.event.id) or await _clip_for(ctx, match, s.event)
            prev = old.get((p.id, clip.id))
            ctx.db.add(
                PlayerFeedItem(
                    organization_id=match.organization_id,
                    player_id=p.id,
                    match_id=match.id,
                    clip_id=clip.id,
                    rank=rank,
                    reason=s.reason,
                    positive=s.positive,
                    coach_comment=prev.coach_comment if prev else None,
                    seen_at=prev.seen_at if prev else None,
                )
            )
        if p.user_id:
            recipients.append(p.user_id)
    await ctx.db.flush()
    if notify and recipients:
        await training.notify(
            ctx,
            match.organization_id,
            recipients,
            "feed_ready",
            {"match_id": str(match.id)},
            f"/app/{match.organization_id}/feed/{match.id}",
        )
    return players_with_feed


async def _clip_for(ctx: Ctx, match: Match, e: Event) -> Clip:
    assert e.t_ms is not None
    clip = Clip(
        organization_id=match.organization_id,
        match_id=match.id,
        start_ms=max(0, e.t_ms - PRE_MS),
        end_ms=e.t_ms + POST_MS,
        source=ClipSource.EVENT,
        source_ref=e.id,
    )
    ctx.db.add(clip)
    await ctx.db.flush()
    return clip


async def generate_now(ctx: Ctx, match_id: uuid.UUID) -> int:
    match = await get_match(ctx, match_id, Action.CLIP_WRITE)
    n = await generate(ctx, match)
    await audit.record(ctx, "feed.generated", target_type="match", target_id=match.id)
    return n


# ---- player side ---------------------------------------------------------------------------


async def _my_players(ctx: Ctx) -> dict[uuid.UUID, str]:
    """Player profiles I may see feeds of: my own, and my children's (parents)."""
    uid = ctx.user_id
    own = (await ctx.db.scalars(select(Player.id).where(Player.user_id == uid))).all()
    kids = (
        await ctx.db.scalars(select(Guardianship.player_id).where(Guardianship.user_id == uid))
    ).all()
    out = {k: "guardian" for k in kids}
    out.update({p: "self" for p in own})
    return out


async def my_feeds(ctx: Ctx) -> list[dict[str, Any]]:
    mine = await _my_players(ctx)
    if not mine:
        return []
    rows = (
        await ctx.db.execute(
            select(PlayerFeedItem.player_id, PlayerFeedItem.match_id, Match, Player.first_name)
            .join(Match, Match.id == PlayerFeedItem.match_id)
            .join(Player, Player.id == PlayerFeedItem.player_id)
            .where(PlayerFeedItem.player_id.in_(mine))
            .distinct()
        )
    ).all()
    done = {
        (a.player_id, a.match_id)
        for a in (
            await ctx.db.scalars(select(SelfAssessment).where(SelfAssessment.player_id.in_(mine)))
        ).all()
    }
    out = []
    for pid, mid, m, first in rows:
        opp = await opponent_of(ctx, m)
        out.append(
            {
                "player_id": pid,
                "player_first_name": first,
                "relation": mine[pid],
                "match_id": mid,
                "kickoff_at": m.kickoff_at,
                "opponent": opp.name if opp else None,
                "assessed": (pid, mid) in done,
            }
        )
    return sorted(out, key=lambda r: r["kickoff_at"], reverse=True)


async def _feed_player(ctx: Ctx, match_id: uuid.UUID, player_id: uuid.UUID | None) -> uuid.UUID:
    mine = await _my_players(ctx)
    if player_id is None:
        own = [p for p, rel in mine.items() if rel == "self"]
        player_id = own[0] if own else (next(iter(mine)) if mine else None)
    if player_id is None or player_id not in mine:
        raise ProblemError(404, "not-found", "No feed for you in this match")
    return player_id


async def player_feed(
    ctx: Ctx, match_id: uuid.UUID, player_id: uuid.UUID | None = None
) -> dict[str, Any]:
    pid = await _feed_player(ctx, match_id, player_id)
    match = await ctx.db.get(Match, match_id)
    if match is None:
        raise ProblemError(404, "not-found", "No feed for you in this match")
    team = await ctx.db.get(Team, match.team_id)
    assessment = await ctx.db.scalar(
        select(SelfAssessment).where(
            SelfAssessment.player_id == pid, SelfAssessment.match_id == match_id
        )
    )
    items = (
        await ctx.db.execute(
            select(PlayerFeedItem, Clip)
            .join(Clip, Clip.id == PlayerFeedItem.clip_id)
            .where(PlayerFeedItem.player_id == pid, PlayerFeedItem.match_id == match_id)
            .order_by(PlayerFeedItem.rank)
        )
    ).all()
    if not items:
        raise ProblemError(404, "not-found", "No feed for you in this match")
    now = datetime.now(UTC)
    for f, _ in items:
        f.seen_at = f.seen_at or now
    video_id = await ctx.db.scalar(
        select(VideoAsset.id).where(
            VideoAsset.match_id == match_id,
            VideoAsset.role == VideoRole.MAIN,
            VideoAsset.status == VideoStatus.READY,
        )
    )
    return {
        "match_id": match_id,
        "player_id": pid,
        "video_id": video_id,
        "youth": bool(team and team.is_youth),
        "self_assessment": _assessment_out(assessment),
        "items": [
            {
                "id": f.id,
                "rank": f.rank,
                "reason": f.reason,
                "positive": f.positive,
                "clip_id": c.id,
                "start_ms": c.start_ms,
                "end_ms": c.end_ms,
                "event_id": c.source_ref,
                # self-assessment first: the coach's view comes after the player's own
                "coach_comment": f.coach_comment if assessment else None,
            }
            for f, c in items
        ],
        "coach_comments_waiting": 0 if assessment else sum(1 for f, _ in items if f.coach_comment),
    }


def _assessment_out(a: SelfAssessment | None) -> dict[str, Any] | None:
    if a is None:
        return None
    return {"rating": a.rating, "text": a.text, "submitted_at": a.submitted_at}


async def assess(
    ctx: Ctx, match_id: uuid.UUID, rating: int, text: str | None, player_id: uuid.UUID | None
) -> dict[str, Any]:
    pid = await _feed_player(ctx, match_id, player_id)
    if (await _my_players(ctx))[pid] != "self":
        raise ProblemError(403, "forbidden", "Only the player assesses their own match")
    match = await ctx.db.get(Match, match_id)
    assert match is not None
    a = await ctx.db.scalar(
        select(SelfAssessment).where(
            SelfAssessment.player_id == pid, SelfAssessment.match_id == match_id
        )
    )
    now = datetime.now(UTC)
    if a is None:
        a = SelfAssessment(
            organization_id=match.organization_id,
            player_id=pid,
            match_id=match_id,
            rating=rating,
            text=text,
            submitted_at=now,
        )
        ctx.db.add(a)
    else:
        a.rating, a.text, a.submitted_at = rating, text, now
    await ctx.db.flush()
    return await player_feed(ctx, match_id, pid)


# ---- coach side ----------------------------------------------------------------------------


async def team_feed(ctx: Ctx, match_id: uuid.UUID) -> list[dict[str, Any]]:
    """Overview for the coach: scenes per player and the self-assessments."""
    match = await get_match(ctx, match_id, Action.CLIP_WRITE)
    rows = (
        await ctx.db.execute(
            select(PlayerFeedItem, Clip, Player)
            .join(Clip, Clip.id == PlayerFeedItem.clip_id)
            .join(Player, Player.id == PlayerFeedItem.player_id)
            .where(PlayerFeedItem.match_id == match.id)
            .order_by(Player.last_name, PlayerFeedItem.rank)
        )
    ).all()
    numbers = dict(
        (
            await ctx.db.execute(
                select(RosterEntry.player_id, RosterEntry.jersey_number).where(
                    RosterEntry.season_id == match.season_id
                )
            )
        ).all()
    )
    assessments = {
        a.player_id: a
        for a in (
            await ctx.db.scalars(select(SelfAssessment).where(SelfAssessment.match_id == match.id))
        ).all()
    }
    out: dict[uuid.UUID, dict[str, Any]] = {}
    for f, c, p in rows:
        entry = out.setdefault(
            p.id,
            {
                "player_id": p.id,
                "name": f"{p.first_name} {p.last_name}",
                "number": numbers.get(p.id),
                "self_assessment": _assessment_out(assessments.get(p.id)),
                "items": [],
            },
        )
        entry["items"].append(
            {
                "id": f.id,
                "rank": f.rank,
                "reason": f.reason,
                "positive": f.positive,
                "clip_id": c.id,
                "start_ms": c.start_ms,
                "end_ms": c.end_ms,
                "event_id": c.source_ref,
                "coach_comment": f.coach_comment,
                "seen": f.seen_at is not None,
            }
        )
    return list(out.values())


async def _item(ctx: Ctx, item_id: uuid.UUID) -> tuple[PlayerFeedItem, Match]:
    item = await ctx.db.get(PlayerFeedItem, item_id)
    if item is None:
        raise ProblemError(404, "not-found", "Scene not found")
    match = await get_match(ctx, item.match_id, Action.CLIP_WRITE)
    return item, match


async def comment(ctx: Ctx, item_id: uuid.UUID, text: str | None) -> None:
    item, _ = await _item(ctx, item_id)
    item.coach_comment = text or None


async def swap(ctx: Ctx, item_id: uuid.UUID, event_id: uuid.UUID) -> None:
    """The coach replaces a scene with another event of the same match."""
    item, match = await _item(ctx, item_id)
    e = await ctx.db.get(Event, event_id)
    if e is None or e.match_id != match.id or e.t_ms is None:
        raise ProblemError(422, "invalid-scene", "Choose an event of this match with video time")
    c = classify(e, item.player_id)
    clip = await ctx.db.scalar(
        select(Clip).where(Clip.source == ClipSource.EVENT, Clip.source_ref == e.id)
    ) or await _clip_for(ctx, match, e)
    item.clip_id = clip.id
    item.reason = c[0] if c else "coach_choice"
    item.positive = c[1] if c else True
    item.seen_at = None


async def guardian_sees_match(ctx: Ctx, match_id: uuid.UUID) -> bool:
    """True when the signed-in user is a parent of a player with scenes in this match."""
    if ctx.user_id is None:
        return False
    found = await ctx.db.scalar(
        select(PlayerFeedItem.id)
        .join(Guardianship, Guardianship.player_id == PlayerFeedItem.player_id)
        .where(PlayerFeedItem.match_id == match_id, Guardianship.user_id == ctx.user_id)
        .limit(1)
    )
    return found is not None
