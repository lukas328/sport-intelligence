"""Automatic highlights (addendum 01, 4.3).

Rule-based selection: scenes of our team (goals, saves, steals, blocks, assists) with confidence of
at least 0.6, ranked by importance (late in a period, close score, fast break) with variety (each
repeat of a type counts less). Team reels aim at 60 to 120 s, player reels at what the player has.
Consent: a scene whose featured player has no `highlights_internal` consent is left out; public
sharing needs `highlights_public` of every featured player and is never possible for youth teams.
Opponent players are never featured or named. Rendering (16:9, 9:16 with a crop that follows the
play, intro card, name strip, burned-in spotlight) runs in the worker.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.models import (
    CameraCalibration,
    Event,
    Guardianship,
    HighlightReel,
    Match,
    Organization,
    Player,
    RosterEntry,
    Team,
    Track,
)
from handball_api.models.enums import ConsentKind, ReelFormat, ReelStatus
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.feed import _close_events, _importance, in_video
from handball_api.services.matches import (
    get_match,
    opponent_of,
    timeline_duration_ms,
    timeline_video,
)
from handball_api.services.policies import Action, can
from handball_api.services.roster import consented
from handball_api.services.videos import media_prefix

MIN_CONFIDENCE = 0.6
PRE_MS, POST_MS = 6000, 2500
TEAM_MIN_S, TEAM_MAX_S = 60, 120
FUNC = "handball_worker.reels.run_highlight_reel"
WEIGHT = {"goal": 3.0, "save": 2.5, "steal": 2.0, "block": 2.0, "assist": 2.2}


@dataclass
class Scene:
    event: Event
    kind: str
    player_id: uuid.UUID | None
    score: float


def scene_kind(e: Event) -> tuple[str, uuid.UUID | None] | None:
    """(kind, featured player) of an event of our team, or None."""
    attrs = e.attributes or {}
    if e.type == "shot" and e.side == "own" and e.outcome == "goal":
        return "goal", e.player_id
    if e.type == "shot" and e.side == "opponent" and e.outcome == "save":
        gk = attrs.get("goalkeeper_id")
        return "save", uuid.UUID(str(gk)) if gk else None
    if e.type == "shot" and e.side == "opponent" and e.outcome == "blocked":
        b = attrs.get("blocked_by")
        return "block", uuid.UUID(str(b)) if b else None
    if e.type == "steal" and e.side == "own":
        return "steal", e.player_id
    return None


def rank(events: list[Event], match: Match, player: uuid.UUID | None = None) -> list[Scene]:
    close = _close_events(events)
    out: list[Scene] = []
    for e in events:
        if e.t_ms is None or e.confidence < MIN_CONFIDENCE:
            continue
        found = scene_kind(e)
        if found is None:
            continue
        kind, who = found
        if player is not None and who != player:
            if kind == "goal" and e.assist_player_id == player:
                kind, who = "assist", player
            else:
                continue
        base = WEIGHT[kind] + (0.5 if (e.shot_type == "fast_break") else 0)
        out.append(Scene(e, kind, who, base * _importance(e, match, close)))
    return out


def pick(scenes: list[Scene], max_s: int) -> list[Scene]:
    """Greedy by score with a variety penalty, up to max_s; reel order is chronological."""
    remaining = sorted(scenes, key=lambda s: -s.score)
    chosen: list[Scene] = []
    kinds: Counter[str] = Counter()
    clip_s = (PRE_MS + POST_MS) / 1000
    while remaining and (len(chosen) + 1) * clip_s <= max_s:
        best = max(remaining, key=lambda s: s.score * 0.7 ** kinds[s.kind])
        chosen.append(best)
        remaining.remove(best)
        kinds[best.kind] += 1
    return sorted(chosen, key=lambda s: s.event.t_ms or 0)


async def _names(ctx: Ctx, match: Match) -> dict[uuid.UUID, str]:
    rows = (
        await ctx.db.execute(
            select(Player.id, Player.first_name, RosterEntry.jersey_number)
            .join(RosterEntry, RosterEntry.player_id == Player.id)
            .where(RosterEntry.season_id == match.season_id)
        )
    ).all()
    return {pid: (f"#{n} {first}" if n is not None else first) for pid, first, n in rows}


async def build(
    ctx: Ctx, match: Match, fmt: ReelFormat, player_id: uuid.UUID | None = None
) -> HighlightReel | None:
    """Selects the scenes, records the consent check and queues the rendering."""
    video = await timeline_video(ctx, match.id, ready=True)
    if video is None or not video.proxy_key:
        return None
    events = list(
        (
            await ctx.db.scalars(
                select(Event).where(Event.match_id == match.id).order_by(Event.t_ms.nulls_last())
            )
        ).all()
    )
    duration = await timeline_duration_ms(ctx, match.id)
    scenes = rank([e for e in events if in_video(e, duration)], match, player_id)
    featured = {s.player_id for s in scenes if s.player_id}
    allowed = await consented(ctx, list(featured), ConsentKind.HIGHLIGHTS_INTERNAL)
    excluded = sorted(str(p) for p in featured - allowed)
    scenes = [s for s in scenes if s.player_id is None or s.player_id in allowed]
    if player_id is not None and player_id not in allowed:
        scenes = []
    chosen = pick(scenes, TEAM_MAX_S)
    if len(chosen) < 3:
        return None
    team = await ctx.db.get(Team, match.team_id)
    org = await ctx.db.get(Organization, match.organization_id)
    opp = await opponent_of(ctx, match)
    names = await _names(ctx, match)
    assert team is not None and org is not None
    reel = HighlightReel(
        organization_id=match.organization_id,
        team_id=match.team_id,
        match_id=match.id,
        player_id=player_id,
        format=fmt,
        status=ReelStatus.QUEUED,
        consent={
            "checked_at": datetime.now(UTC).isoformat(),
            "purpose": ConsentKind.HIGHLIGHTS_INTERNAL.value,
            "excluded_players": excluded,
        },
        clip_ids=[str(s.event.id) for s in chosen],
    )
    ctx.db.add(reel)
    await ctx.db.flush()
    cal = await ctx.db.scalar(
        select(CameraCalibration)
        .where(CameraCalibration.video_asset_id == video.id)
        .order_by(CameraCalibration.created_at.desc())
        .limit(1)
    )
    tracks = (await ctx.db.scalars(select(Track).where(Track.video_asset_id == video.id))).all()
    player_tracks = [t.track_no for t in tracks if t.team and t.team != "referee"]
    spot = {t.player_id: t.track_no for t in tracks if t.player_id}
    analysis = video.analysis or {}
    home, away = (
        (team.name, opp.name if opp else "")
        if match.is_home
        else (opp.name if opp else "", team.name)
    )
    score = (
        (
            f"{match.score_own}:{match.score_opponent}"
            if match.is_home
            else f"{match.score_opponent}:{match.score_own}"
        )
        if match.score_own is not None and match.score_opponent is not None
        else ""
    )
    title = [org.name, f"{home} - {away}".strip(" -"), score]
    if player_id is not None:
        title.insert(1, names.get(player_id, ""))
    await ctx.enqueue(
        "default",
        FUNC,
        f"reel-{reel.id}",
        {
            "payload": {
                "reel_id": str(reel.id),
                "format": fmt.value,
                "bucket_videos": ctx.settings.s3_bucket_videos,
                "bucket_artifacts": ctx.settings.s3_bucket_artifacts,
                "proxy_key": video.proxy_key,
                "out_key": f"{match.organization_id}/highlights/{reel.id}.mp4",
                "logo_key": org.logo_key,
                "colour": org.primary_color,
                "intro": [x for x in title if x],
                "chunks_prefix": media_prefix(video) + "analysis/",
                "chunk_ms": analysis.get("chunk_ms"),
                "homography": cal.homography if cal else None,
                "image_size": cal.image_size if cal else None,
                "player_tracks": player_tracks,
                "clips": [
                    {
                        "in_ms": max(0, (s.event.t_ms or 0) - PRE_MS),
                        "out_ms": (s.event.t_ms or 0) + POST_MS
                        if duration is None
                        else min(duration, (s.event.t_ms or 0) + POST_MS),
                        "label": names.get(s.player_id, "") if s.player_id else "",
                        "spotlight_track": spot.get(s.player_id) if s.player_id else None,
                    }
                    for s in chosen
                ],
            }
        },
    )
    return reel


async def auto(ctx: Ctx, match: Match) -> int:
    """After an analysis: team reels (16:9 and 9:16) and a 9:16 reel per consenting player."""
    if match.kind != "match":
        return 0
    created = 0
    for fmt in (ReelFormat.LANDSCAPE, ReelFormat.PORTRAIT):
        created += 1 if await build(ctx, match, fmt) else 0
    events = (await ctx.db.scalars(select(Event).where(Event.match_id == match.id))).all()
    players = {s.player_id for s in rank(list(events), match) if s.player_id}
    for pid in sorted(players, key=str):
        created += 1 if await build(ctx, match, ReelFormat.PORTRAIT, pid) else 0
    return created


async def create(
    ctx: Ctx, match_id: uuid.UUID, fmt: ReelFormat, player_id: uuid.UUID | None
) -> HighlightReel:
    match = await get_match(ctx, match_id, Action.CLIP_WRITE)
    reel = await build(ctx, match, fmt, player_id)
    if reel is None:
        raise ProblemError(
            422, "not-enough-scenes", "Not enough confident scenes with consent for a reel"
        )
    await audit.record(ctx, "highlights.created", target_type="match", target_id=match.id)
    return reel


async def _mine(ctx: Ctx) -> set[uuid.UUID]:
    own = (await ctx.db.scalars(select(Player.id).where(Player.user_id == ctx.user_id))).all()
    kids = (
        await ctx.db.scalars(
            select(Guardianship.player_id).where(Guardianship.user_id == ctx.user_id)
        )
    ).all()
    return set(own) | set(kids)


async def visible(ctx: Ctx, reel: HighlightReel) -> bool:
    actor = ctx.require_actor()
    if can(actor, Action.PLAYLIST_READ_ALL, reel.team_id):
        return True
    if reel.player_id is not None:
        return reel.player_id in await _mine(ctx)
    return actor.is_org_admin or (
        actor.team_role(reel.team_id) is not None and can(actor, Action.TEAM_READ, reel.team_id)
    )


async def list_for_match(ctx: Ctx, match_id: uuid.UUID) -> list[HighlightReel]:
    try:
        match = await get_match(ctx, match_id)
    except ProblemError:
        mine = await _mine(ctx)
        reels = (
            await ctx.db.scalars(
                select(HighlightReel).where(
                    HighlightReel.match_id == match_id, HighlightReel.player_id.in_(mine)
                )
            )
        ).all()
        if not reels:
            raise
        return list(reels)
    rows = (
        await ctx.db.scalars(
            select(HighlightReel)
            .where(HighlightReel.match_id == match.id)
            .order_by(HighlightReel.created_at.desc())
        )
    ).all()
    return [r for r in rows if await visible(ctx, r)]


async def video(ctx: Ctx, reel_id: uuid.UUID) -> bytes:
    reel = await ctx.db.get(HighlightReel, reel_id)
    if reel is None or not await visible(ctx, reel):
        raise ProblemError(404, "not-found", "Reel not found")
    if reel.status != ReelStatus.READY or not reel.output_key:
        raise ProblemError(409, "not-ready", "The reel is not ready yet")
    data, _ = await ctx.storage.get(ctx.settings.s3_bucket_artifacts, reel.output_key)
    return data


async def done(
    ctx: Ctx, reel_id: uuid.UUID, status: str, key: str | None, error: str | None
) -> None:
    reel = await ctx.db.get(HighlightReel, reel_id)
    if reel is None:
        raise ProblemError(404, "not-found", "Reel not found")
    reel.status = ReelStatus(status)
    reel.output_key = key
    if error:
        reel.consent = {**reel.consent, "error": error[:300]}
