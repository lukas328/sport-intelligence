"""Clips, playlists, comments and drawings on match videos (BRIEF 11.5)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from handball_api.core.errors import ProblemError
from handball_api.models import (
    Annotation,
    Clip,
    Comment,
    Match,
    Opponent,
    Playlist,
    PlaylistItem,
    User,
    VideoAsset,
)
from handball_api.models.enums import VideoRole, VideoStatus
from handball_api.schemas.matches import (
    AnnotationCreate,
    ClipCreate,
    ClipOut,
    CommentCreate,
    CommentOut,
    PlaylistCreate,
    PlaylistDetail,
    PlaylistItemCreate,
    PlaylistItemOut,
    PlaylistOut,
    PlaylistUpdate,
)
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.matches import get_match
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action, can

# ---- clips ---------------------------------------------------------------------------------


async def create_clip(ctx: Ctx, data: ClipCreate) -> Clip:
    match = await get_match(ctx, data.match_id, Action.CLIP_WRITE)
    clip = Clip(
        organization_id=match.organization_id,
        match_id=match.id,
        start_ms=data.start_ms,
        end_ms=data.end_ms,
        title=data.title,
        created_by_id=ctx.user_id,
    )
    ctx.db.add(clip)
    await ctx.db.flush()
    return clip


async def list_clips(ctx: Ctx, match_id: uuid.UUID) -> list[Clip]:
    await get_match(ctx, match_id)
    rows = await ctx.db.scalars(
        select(Clip).where(Clip.match_id == match_id).order_by(Clip.start_ms)
    )
    return list(rows.all())


async def delete_clip(ctx: Ctx, clip_id: uuid.UUID) -> None:
    clip = await ctx.db.get(Clip, clip_id)
    if clip is None:
        raise ProblemError(404, "not-found", "Clip not found")
    await get_match(ctx, clip.match_id, Action.CLIP_WRITE)
    await ctx.db.delete(clip)


# ---- playlists -----------------------------------------------------------------------------


async def _playlist(ctx: Ctx, playlist_id: uuid.UUID, write: bool = False) -> Playlist:
    pl = await ctx.db.get(Playlist, playlist_id)
    if pl is None:
        raise ProblemError(404, "not-found", "Playlist not found")
    await get_team(ctx, pl.team_id, Action.PLAYLIST_WRITE if write else Action.TEAM_READ)
    if (
        not write
        and not pl.shared_with_players
        and not can(ctx.require_actor(), Action.PLAYLIST_READ_ALL, pl.team_id)
    ):
        raise ProblemError(404, "not-found", "Playlist not found")
    return pl


async def list_playlists(ctx: Ctx, team_id: uuid.UUID) -> list[PlaylistOut]:
    await get_team(ctx, team_id, Action.TEAM_READ)
    q = (
        select(Playlist, func.count(PlaylistItem.id))
        .outerjoin(PlaylistItem, PlaylistItem.playlist_id == Playlist.id)
        .where(Playlist.team_id == team_id)
        .group_by(Playlist.id)
        .order_by(Playlist.created_at.desc())
    )
    if not can(ctx.require_actor(), Action.PLAYLIST_READ_ALL, team_id):
        q = q.where(Playlist.shared_with_players.is_(True))
    return [
        PlaylistOut(
            id=p.id,
            team_id=p.team_id,
            title=p.title,
            description=p.description,
            shared_with_players=p.shared_with_players,
            item_count=n,
            created_at=p.created_at,
        )
        for p, n in (await ctx.db.execute(q)).all()
    ]


async def create_playlist(ctx: Ctx, team_id: uuid.UUID, data: PlaylistCreate) -> Playlist:
    team = await get_team(ctx, team_id, Action.PLAYLIST_WRITE)
    pl = Playlist(
        organization_id=team.organization_id,
        team_id=team.id,
        created_by_id=ctx.user_id,
        **data.model_dump(),
    )
    ctx.db.add(pl)
    await ctx.db.flush()
    return pl


async def update_playlist(ctx: Ctx, playlist_id: uuid.UUID, data: PlaylistUpdate) -> Playlist:
    pl = await _playlist(ctx, playlist_id, write=True)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(pl, k, v)
    return pl


async def delete_playlist(ctx: Ctx, playlist_id: uuid.UUID) -> None:
    pl = await _playlist(ctx, playlist_id, write=True)
    await ctx.db.delete(pl)


async def playlist_detail(ctx: Ctx, playlist_id: uuid.UUID) -> PlaylistDetail:
    pl = await _playlist(ctx, playlist_id)
    rows = (
        await ctx.db.execute(
            select(PlaylistItem, Clip, Opponent.name, Match.kickoff_at)
            .join(Clip, Clip.id == PlaylistItem.clip_id)
            .join(Match, Match.id == Clip.match_id)
            .outerjoin(Opponent, Opponent.id == Match.opponent_id)
            .where(PlaylistItem.playlist_id == pl.id)
            .order_by(PlaylistItem.position)
        )
    ).all()
    match_ids = {clip.match_id for _, clip, _, _ in rows}
    videos = (
        {
            mid: vid
            for mid, vid in (
                await ctx.db.execute(
                    select(VideoAsset.match_id, VideoAsset.id).where(
                        VideoAsset.match_id.in_(match_ids),
                        VideoAsset.role == VideoRole.MAIN,
                        VideoAsset.status == VideoStatus.READY,
                    )
                )
            ).all()
        }
        if match_ids
        else {}
    )
    items = [
        PlaylistItemOut(
            video_id=videos.get(clip.match_id),
            id=item.id,
            position=item.position,
            note=item.note,
            clip=ClipOut.model_validate(clip),
            match_label=f"{opp} ({kickoff:%d.%m.%Y})",
        )
        for item, clip, opp, kickoff in rows
    ]
    return PlaylistDetail(
        id=pl.id,
        team_id=pl.team_id,
        title=pl.title,
        description=pl.description,
        shared_with_players=pl.shared_with_players,
        item_count=len(items),
        created_at=pl.created_at,
        items=items,
    )


async def add_item(ctx: Ctx, playlist_id: uuid.UUID, data: PlaylistItemCreate) -> PlaylistItem:
    pl = await _playlist(ctx, playlist_id, write=True)
    if data.clip is not None:
        clip = await create_clip(ctx, data.clip)
    else:
        found = await ctx.db.get(Clip, data.clip_id)
        if found is None:
            raise ProblemError(404, "not-found", "Clip not found")
        clip = found
    match = await get_match(ctx, clip.match_id)
    if match.team_id != pl.team_id:
        raise ProblemError(422, "clip-other-team", "Clips must belong to the playlist's team")
    position = (
        await ctx.db.scalar(
            select(func.coalesce(func.max(PlaylistItem.position), 0)).where(
                PlaylistItem.playlist_id == pl.id
            )
        )
    ) or 0
    item = PlaylistItem(
        organization_id=pl.organization_id,
        playlist_id=pl.id,
        clip_id=clip.id,
        position=position + 1,
        note=data.note,
    )
    ctx.db.add(item)
    await ctx.db.flush()
    return item


async def remove_item(ctx: Ctx, playlist_id: uuid.UUID, item_id: uuid.UUID) -> None:
    await _playlist(ctx, playlist_id, write=True)
    item = await ctx.db.get(PlaylistItem, item_id)
    if item is None or item.playlist_id != playlist_id:
        raise ProblemError(404, "not-found", "Item not found")
    await ctx.db.delete(item)


async def reorder(ctx: Ctx, playlist_id: uuid.UUID, item_ids: list[uuid.UUID]) -> None:
    await _playlist(ctx, playlist_id, write=True)
    items = {
        i.id: i
        for i in (
            await ctx.db.scalars(
                select(PlaylistItem).where(PlaylistItem.playlist_id == playlist_id)
            )
        ).all()
    }
    if set(item_ids) != set(items) or len(item_ids) != len(items):
        raise ProblemError(422, "invalid-order", "Give every item of the playlist exactly once")
    for pos, iid in enumerate(item_ids, start=1):
        items[iid].position = pos


# ---- comments ------------------------------------------------------------------------------


async def list_comments(ctx: Ctx, match_id: uuid.UUID) -> list[CommentOut]:
    match = await get_match(ctx, match_id)
    moderate = can(ctx.require_actor(), Action.COMMENT_MODERATE, match.team_id)
    rows = (
        await ctx.db.execute(
            select(Comment, User.name)
            .outerjoin(User, User.id == Comment.author_id)
            .where(Comment.match_id == match_id)
            .order_by(Comment.t_ms, Comment.created_at)
        )
    ).all()
    return [
        CommentOut(
            id=c.id,
            t_ms=c.t_ms,
            body=c.body,
            author_id=c.author_id,
            author_name=name,
            created_at=c.created_at,
            can_delete=moderate or c.author_id == ctx.user_id,
        )
        for c, name in rows
    ]


async def add_comment(ctx: Ctx, match_id: uuid.UUID, data: CommentCreate) -> Comment:
    match = await get_match(ctx, match_id, Action.COMMENT_WRITE)
    c = Comment(
        organization_id=match.organization_id,
        match_id=match.id,
        author_id=ctx.user_id,
        t_ms=data.t_ms,
        body=data.body.strip(),
    )
    ctx.db.add(c)
    await ctx.db.flush()
    return c


async def delete_comment(ctx: Ctx, comment_id: uuid.UUID) -> None:
    c = await ctx.db.get(Comment, comment_id)
    if c is None:
        raise ProblemError(404, "not-found", "Comment not found")
    match = await get_match(ctx, c.match_id)
    if c.author_id != ctx.user_id and not can(
        ctx.require_actor(), Action.COMMENT_MODERATE, match.team_id
    ):
        raise ProblemError(403, "forbidden", "Only the author or staff can delete a comment")
    await ctx.db.delete(c)


# ---- annotations ---------------------------------------------------------------------------


async def list_annotations(ctx: Ctx, match_id: uuid.UUID) -> list[Annotation]:
    await get_match(ctx, match_id)
    rows = await ctx.db.scalars(
        select(Annotation).where(Annotation.match_id == match_id).order_by(Annotation.t_ms)
    )
    return list(rows.all())


async def add_annotation(ctx: Ctx, match_id: uuid.UUID, data: AnnotationCreate) -> Annotation:
    match = await get_match(ctx, match_id, Action.ANNOTATION_WRITE)
    a = Annotation(
        organization_id=match.organization_id,
        match_id=match.id,
        author_id=ctx.user_id,
        t_ms=data.t_ms,
        duration_ms=data.duration_ms,
        shapes=[s.model_dump(mode="json") for s in data.shapes],
    )
    ctx.db.add(a)
    await ctx.db.flush()
    await audit.record(ctx, "annotation.created", target_type="match", target_id=match.id)
    return a


async def delete_annotation(ctx: Ctx, annotation_id: uuid.UUID) -> None:
    a = await ctx.db.get(Annotation, annotation_id)
    if a is None:
        raise ProblemError(404, "not-found", "Drawing not found")
    await get_match(ctx, a.match_id, Action.ANNOTATION_WRITE)
    await ctx.db.delete(a)
