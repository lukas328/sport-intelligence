"""Share links (M8): read-only public access to a play, a match report or a playlist.

Tokens are random, only their hash is stored; links expire (1 to 90 days), can be revoked and count
views.
Shared content never contains player names, only jersey numbers. Youth teams may only share plays
(addendum 01, youth protection).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from handball_api.core.db import disable_system_access, enable_system_access, set_tenant
from handball_api.core.errors import ProblemError
from handball_api.core.security import hash_token, new_token
from handball_api.models import (
    Clip,
    Event,
    HighlightReel,
    Match,
    Play,
    Playlist,
    PlaylistItem,
    RosterEntry,
    ShareLink,
    Team,
    VideoAsset,
)
from handball_api.models.enums import ConsentKind, ReelStatus
from handball_api.services import audit, billing, org_verification
from handball_api.services import events as events_service
from handball_api.services.context import Ctx
from handball_api.services.highlights import rank
from handball_api.services.matches import opponent_of, timeline_video
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action
from handball_api.services.roster import consented
from handball_api.services.videos import MEDIA_PATH, MEDIA_TYPES, media_prefix


def _now() -> datetime:
    return datetime.now(UTC)


async def _target(ctx: Ctx, team: Team, kind: str, target_id: uuid.UUID) -> str:
    if kind == "highlight":
        reel = await ctx.db.get(HighlightReel, target_id)
        if reel is None or reel.team_id != team.id or reel.status != ReelStatus.READY:
            raise ProblemError(404, "not-found", "Reel not found or not ready")
        # public only with highlights_public of every featured player (addendum 01, 4.3)
        featured = {
            s.player_id
            for s in rank(
                list(
                    (
                        await ctx.db.scalars(
                            select(Event).where(Event.id.in_([uuid.UUID(c) for c in reel.clip_ids]))
                        )
                    ).all()
                ),
                await ctx.db.get(Match, reel.match_id) if reel.match_id else None,  # type: ignore[arg-type]
                reel.player_id,
            )
            if s.player_id
        }
        ok = await consented(ctx, list(featured), ConsentKind.HIGHLIGHTS_PUBLIC)
        if featured - ok:
            raise ProblemError(
                403, "consent-missing", "Public sharing needs the public highlights consent"
            )
        return "Highlights"
    if kind == "play":
        play = await ctx.db.get(Play, target_id)
        if play is None or play.team_id != team.id:
            raise ProblemError(404, "not-found", "Play not found")
        return play.name
    if kind == "playlist":
        pl = await ctx.db.get(Playlist, target_id)
        if pl is None or pl.team_id != team.id:
            raise ProblemError(404, "not-found", "Playlist not found")
        return pl.title
    match = await ctx.db.get(Match, target_id)
    if match is None or match.team_id != team.id:
        raise ProblemError(404, "not-found", "Match not found")
    opp = await opponent_of(ctx, match)
    return f"{team.name} - {opp.name}" if opp else team.name


async def create(
    ctx: Ctx, team_id: uuid.UUID, kind: str, target_id: uuid.UUID, days: int
) -> tuple[ShareLink, str]:
    team = await get_team(ctx, team_id, Action.PLAYLIST_WRITE)
    await billing.require_feature(ctx, "share_links", team.organization_id)
    # a club claimed from the official data shares nothing publicly until it is verified
    await org_verification.require_verified(ctx, team.organization_id)
    if team.is_youth and kind != "play":
        # youth protection (addendum 01): no public video or player data of children
        raise ProblemError(
            403, "youth-protection", "Youth teams can only share plays, no matches or videos"
        )
    title = await _target(ctx, team, kind, target_id)
    token = new_token(24)
    link = ShareLink(
        organization_id=team.organization_id,
        team_id=team.id,
        kind=kind,
        target_id=target_id,
        token_hash=hash_token(token),
        title=title[:200],
        expires_at=_now() + timedelta(days=days),
        created_by_id=ctx.user_id,
    )
    ctx.db.add(link)
    await ctx.db.flush()
    await audit.record(ctx, "share_link.created", target_type="share_link", target_id=link.id)
    return link, token


async def list_links(ctx: Ctx, team_id: uuid.UUID) -> list[ShareLink]:
    team = await get_team(ctx, team_id, Action.PLAYLIST_WRITE)
    return list(
        (
            await ctx.db.scalars(
                select(ShareLink)
                .where(ShareLink.team_id == team.id)
                .order_by(ShareLink.created_at.desc())
            )
        ).all()
    )


async def revoke(ctx: Ctx, link_id: uuid.UUID) -> None:
    link = await ctx.db.get(ShareLink, link_id)
    if link is None:
        raise ProblemError(404, "not-found", "Link not found")
    await get_team(ctx, link.team_id, Action.PLAYLIST_WRITE)
    link.revoked_at = link.revoked_at or _now()
    await audit.record(ctx, "share_link.revoked", target_type="share_link", target_id=link.id)


# ---- public side ----------------------------------------------------------------------------


async def _resolve(ctx: Ctx, token: str) -> ShareLink:
    await enable_system_access(ctx.db, reason="share link lookup")
    link = await ctx.db.scalar(select(ShareLink).where(ShareLink.token_hash == hash_token(token)))
    await disable_system_access(ctx.db)
    if link is None or link.revoked_at is not None or link.expires_at <= _now():
        raise ProblemError(404, "not-found", "This link is no longer valid")
    await set_tenant(ctx.db, link.organization_id)
    return link


async def _numbers(ctx: Ctx, season_id: uuid.UUID) -> dict[str, int]:
    rows = (
        await ctx.db.execute(
            select(RosterEntry.player_id, RosterEntry.jersey_number).where(
                RosterEntry.season_id == season_id
            )
        )
    ).all()
    return {str(p): n for p, n in rows if n is not None}


async def _main_video(ctx: Ctx, match_id: uuid.UUID) -> VideoAsset | None:
    return await timeline_video(ctx, match_id, ready=True)


def _team_block(block: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in block.items() if k not in ("zones", "by_situation")}


async def public(ctx: Ctx, token: str) -> dict[str, Any]:
    link = await _resolve(ctx, token)
    link.views += 1
    team = await ctx.db.get(Team, link.team_id)
    base: dict[str, Any] = {
        "kind": link.kind,
        "title": link.title,
        "team": team.name if team else "",
        "expires_at": link.expires_at.isoformat(),
    }
    if link.kind == "play":
        play = await ctx.db.get(Play, link.target_id)
        if play is None:
            raise ProblemError(404, "not-found", "Not found")
        return {
            **base,
            "play": {
                "name": play.name,
                "category": play.category,
                "formation": play.formation,
                "description": play.description,
                "doc": play.doc,
            },
        }
    if link.kind == "match":
        match = await ctx.db.get(Match, link.target_id)
        if match is None:
            raise ProblemError(404, "not-found", "Not found")
        opp = await opponent_of(ctx, match)
        stats = await events_service.stats_for(ctx, match)
        numbers = await _numbers(ctx, match.season_id)
        players = [
            {
                "number": p.get("number") or numbers.get(str(p.get("player_id"))),
                **{k: p[k] for k in ("goals", "shots", "saves", "turnovers", "suspensions")},
            }
            for p in stats["players"].values()
            if p["side"] == "own" and not (team and team.is_youth)
        ]
        video = await _main_video(ctx, match.id)
        return {
            **base,
            "match": {
                "kickoff_at": match.kickoff_at.isoformat(),
                "is_home": match.is_home,
                "opponent": opp.name if opp else "",
                "score_own": match.score_own,
                "score_opponent": match.score_opponent,
                "halftime_own": match.halftime_own,
                "halftime_opponent": match.halftime_opponent,
                "own": {
                    k: v for k, v in stats["own"].items() if k not in ("zones", "by_situation")
                },
                "opponent_stats": {
                    k: v for k, v in stats["opponent"].items() if k not in ("zones", "by_situation")
                },
                "timeline": stats["timeline"]["score"],
                "players": sorted(players, key=lambda p: -p["goals"]),
                "video_id": str(video.id) if video else None,
            },
        }
    if link.kind == "highlight":
        reel = await ctx.db.get(HighlightReel, link.target_id)
        if reel is None or reel.status != ReelStatus.READY:
            raise ProblemError(404, "not-found", "Not found")
        return {**base, "highlight": {"format": reel.format, "scenes": len(reel.clip_ids)}}
    pl = await ctx.db.get(Playlist, link.target_id)
    if pl is None:
        raise ProblemError(404, "not-found", "Not found")
    rows = (
        await ctx.db.execute(
            select(Clip, Match.id)
            .join(PlaylistItem, PlaylistItem.clip_id == Clip.id)
            .join(Match, Match.id == Clip.match_id)
            .where(PlaylistItem.playlist_id == pl.id)
            .order_by(PlaylistItem.position)
        )
    ).all()
    clips = []
    for clip, match_id in rows:
        video = await _main_video(ctx, match_id)
        clips.append(
            {
                "id": str(clip.id),
                "title": clip.title,
                "start_ms": clip.start_ms,
                "end_ms": clip.end_ms,
                "video_id": str(video.id) if video else None,
            }
        )
    return {**base, "playlist": {"title": pl.title, "description": pl.description, "clips": clips}}


async def public_media(ctx: Ctx, token: str, video_id: uuid.UUID, path: str) -> tuple[bytes, str]:
    """Media of a shared match or of the clips of a shared playlist; nothing else."""
    link = await _resolve(ctx, token)
    video = await ctx.db.get(VideoAsset, video_id)
    if video is None or not MEDIA_PATH.match(path) or ".." in path:
        raise ProblemError(404, "not-found", "Not found")
    if path == "proxy.mp4" or path.startswith("original"):
        raise ProblemError(404, "not-found", "Not found")
    allowed = False
    if link.kind == "match":
        allowed = video.match_id == link.target_id
    elif link.kind == "playlist":
        allowed = (
            await ctx.db.scalar(
                select(Clip.id)
                .join(PlaylistItem, PlaylistItem.clip_id == Clip.id)
                .where(PlaylistItem.playlist_id == link.target_id, Clip.match_id == video.match_id)
                .limit(1)
            )
        ) is not None
    if not allowed:
        raise ProblemError(404, "not-found", "Not found")
    try:
        data, _ = await ctx.storage.get(ctx.settings.s3_bucket_videos, media_prefix(video) + path)
    except Exception as exc:
        raise ProblemError(404, "not-found", "Not found") from exc
    return data, MEDIA_TYPES[path.rsplit(".", 1)[1]]


async def public_reel(ctx: Ctx, token: str) -> bytes:
    link = await _resolve(ctx, token)
    if link.kind != "highlight":
        raise ProblemError(404, "not-found", "Not found")
    reel = await ctx.db.get(HighlightReel, link.target_id)
    if reel is None or reel.status != ReelStatus.READY or not reel.output_key:
        raise ProblemError(404, "not-found", "Not found")
    data, _ = await ctx.storage.get(ctx.settings.s3_bucket_artifacts, reel.output_key)
    return data
