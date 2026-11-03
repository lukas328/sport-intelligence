"""Own tags, combined search and smart playlists (addendum 01, 4.4).

Own tags are a separate dimension: they never change automatic events or metrics, they only add
filters, facet counts and material for presentations.
"""

from __future__ import annotations

import uuid
from collections import Counter
from typing import Any

from sqlalchemy import delete, or_, select

from handball_api.core.errors import ProblemError
from handball_api.models import (
    Clip,
    ClipTag,
    Event,
    Match,
    Opponent,
    Play,
    SavedFilter,
    Tag,
    TagSet,
    Team,
    VideoAsset,
)
from handball_api.models.enums import VideoRole, VideoStatus
from handball_api.schemas.tags import (
    SavedFilterIn,
    SearchFilter,
    SearchHit,
    SearchResult,
    TagIn,
    TagLinksIn,
    TagPatch,
    TagSetIn,
)
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.matches import get_match
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action

# video window around an event: the build-up matters more than the aftermath
EVENT_PRE_MS = 6000
EVENT_POST_MS = 3000


# ---- tag sets ------------------------------------------------------------------------------


async def tag_sets(ctx: Ctx, team_id: uuid.UUID) -> list[tuple[TagSet, list[Tag]]]:
    team = await get_team(ctx, team_id, Action.PLAYLIST_READ_ALL)
    sets = (
        await ctx.db.scalars(select(TagSet).where(TagSet.team_id == team.id).order_by(TagSet.name))
    ).all()
    tags = (
        await ctx.db.scalars(
            select(Tag).where(Tag.tag_set_id.in_([s.id for s in sets])).order_by(Tag.name)
        )
    ).all()
    return [(s, [t for t in tags if t.tag_set_id == s.id]) for s in sets]


async def create_tag_set(ctx: Ctx, team_id: uuid.UUID, data: TagSetIn) -> TagSet:
    team = await get_team(ctx, team_id, Action.CLIP_WRITE)
    exists = await ctx.db.scalar(
        select(TagSet.id).where(TagSet.team_id == team.id, TagSet.name == data.name)
    )
    if exists:
        raise ProblemError(409, "duplicate-name", "A tag set with this name exists")
    ts = TagSet(organization_id=team.organization_id, team_id=team.id, name=data.name)
    ctx.db.add(ts)
    await ctx.db.flush()
    for t in data.tags:
        await _add_tag(ctx, ts, t)
    await audit.record(ctx, "tag_set.created", target_type="tag_set", target_id=ts.id)
    return ts


async def _tag_set(ctx: Ctx, tag_set_id: uuid.UUID) -> TagSet:
    ts = await ctx.db.get(TagSet, tag_set_id)
    if ts is None:
        raise ProblemError(404, "not-found", "Tag set not found")
    await get_team(ctx, ts.team_id, Action.CLIP_WRITE)
    return ts


async def rename_tag_set(ctx: Ctx, tag_set_id: uuid.UUID, name: str) -> TagSet:
    ts = await _tag_set(ctx, tag_set_id)
    ts.name = name
    return ts


async def delete_tag_set(ctx: Ctx, tag_set_id: uuid.UUID) -> None:
    await ctx.db.delete(await _tag_set(ctx, tag_set_id))


async def _add_tag(ctx: Ctx, ts: TagSet, data: TagIn) -> Tag:
    exists = await ctx.db.scalar(
        select(Tag.id).where(Tag.tag_set_id == ts.id, Tag.name == data.name)
    )
    if exists:
        raise ProblemError(409, "duplicate-name", "A tag with this name exists")
    tag = Tag(organization_id=ts.organization_id, tag_set_id=ts.id, **data.model_dump())
    ctx.db.add(tag)
    await ctx.db.flush()
    return tag


async def add_tag(ctx: Ctx, tag_set_id: uuid.UUID, data: TagIn) -> Tag:
    return await _add_tag(ctx, await _tag_set(ctx, tag_set_id), data)


async def _tag(ctx: Ctx, tag_id: uuid.UUID) -> Tag:
    tag = await ctx.db.get(Tag, tag_id)
    if tag is None:
        raise ProblemError(404, "not-found", "Tag not found")
    await _tag_set(ctx, tag.tag_set_id)
    return tag


async def update_tag(ctx: Ctx, tag_id: uuid.UUID, data: TagPatch) -> Tag:
    tag = await _tag(ctx, tag_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(tag, k, v)
    return tag


async def delete_tag(ctx: Ctx, tag_id: uuid.UUID) -> None:
    await ctx.db.delete(await _tag(ctx, tag_id))


# ---- links ---------------------------------------------------------------------------------


async def _target_team(ctx: Ctx, target_type: str, target_id: uuid.UUID) -> uuid.UUID:
    if target_type == "play":
        play = await ctx.db.get(Play, target_id)
        if play is None:
            raise ProblemError(404, "not-found", "Play not found")
        return play.team_id
    if target_type == "clip":
        clip = await ctx.db.get(Clip, target_id)
        match_id = clip.match_id if clip else None
    else:
        ev = await ctx.db.get(Event, target_id)
        match_id = ev.match_id if ev else None
    if match_id is None:
        raise ProblemError(404, "not-found", f"{target_type.title()} not found")
    return (await get_match(ctx, match_id)).team_id


async def set_links(ctx: Ctx, data: TagLinksIn) -> list[uuid.UUID]:
    team_id = await _target_team(ctx, data.target_type, data.target_id)
    await get_team(ctx, team_id, Action.CLIP_WRITE)
    wanted = set(data.tag_ids)
    if wanted:
        valid = set(
            (
                await ctx.db.scalars(
                    select(Tag.id)
                    .join(TagSet, TagSet.id == Tag.tag_set_id)
                    .where(Tag.id.in_(wanted), TagSet.team_id == team_id)
                )
            ).all()
        )
        if valid != wanted:
            raise ProblemError(422, "unknown-tag", "Tags must belong to the team")
    col = {"clip": ClipTag.clip_id, "event": ClipTag.event_id, "play": ClipTag.play_id}[
        data.target_type
    ]
    await ctx.db.execute(delete(ClipTag).where(col == data.target_id))
    team = await ctx.db.get(Team, team_id)
    assert team is not None
    for tag_id in sorted(wanted):
        ctx.db.add(
            ClipTag(
                organization_id=team.organization_id,
                tag_id=tag_id,
                **{f"{data.target_type}_id": data.target_id},
            )
        )
    await ctx.db.flush()
    return sorted(wanted)


async def match_links(ctx: Ctx, match_id: uuid.UUID) -> dict[str, dict[uuid.UUID, list[uuid.UUID]]]:
    match = await get_match(ctx, match_id)
    await get_team(ctx, match.team_id, Action.PLAYLIST_READ_ALL)
    rows = (
        await ctx.db.execute(
            select(ClipTag.clip_id, ClipTag.event_id, ClipTag.tag_id)
            .outerjoin(Clip, Clip.id == ClipTag.clip_id)
            .outerjoin(Event, Event.id == ClipTag.event_id)
            .where(or_(Clip.match_id == match.id, Event.match_id == match.id))
        )
    ).all()
    out: dict[str, dict[uuid.UUID, list[uuid.UUID]]] = {"clips": {}, "events": {}}
    for clip_id, event_id, tag_id in rows:
        if clip_id:
            out["clips"].setdefault(clip_id, []).append(tag_id)
        elif event_id:
            out["events"].setdefault(event_id, []).append(tag_id)
    return out


async def play_tags(ctx: Ctx, play_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[uuid.UUID]]:
    rows = (
        await ctx.db.execute(
            select(ClipTag.play_id, ClipTag.tag_id).where(ClipTag.play_id.in_(play_ids))
        )
    ).all()
    out: dict[uuid.UUID, list[uuid.UUID]] = {}
    for pid, tid in rows:
        if pid is not None:
            out.setdefault(pid, []).append(tid)
    return out


# ---- search --------------------------------------------------------------------------------


def _tag_condition(f: SearchFilter, col: Any) -> list[Any]:
    """Conditions on the target id column for tags_all / tags_any."""
    conds = []
    for tag_id in f.tags_all:
        conds.append(col.in_(select(_link_col(col)).where(ClipTag.tag_id == tag_id)))
    if f.tags_any:
        conds.append(col.in_(select(_link_col(col)).where(ClipTag.tag_id.in_(f.tags_any))))
    return conds


def _link_col(col: Any) -> Any:
    return ClipTag.event_id if col is Event.id else ClipTag.clip_id


async def search(ctx: Ctx, team_id: uuid.UUID, f: SearchFilter) -> SearchResult:
    team = await get_team(ctx, team_id, Action.PLAYLIST_READ_ALL)
    mq = select(Match.id).where(Match.team_id == team.id)
    if f.season_id:
        mq = mq.where(Match.season_id == f.season_id)
    if f.match_ids:
        mq = mq.where(Match.id.in_(f.match_ids))
    if f.opponent_id:
        mq = mq.where(Match.opponent_id == f.opponent_id)
    if f.kind:
        mq = mq.where(Match.kind == f.kind)
    match_ids = list((await ctx.db.scalars(mq)).all())

    eq = select(Event).where(Event.match_id.in_(match_ids))
    for col, values in (
        (Event.type, f.types),
        (Event.side, f.sides),
        (Event.outcome, f.outcomes),
        (Event.player_id, f.player_ids),
        (Event.number, f.numbers),
        (Event.shot_zone, f.shot_zones),
        (Event.goal_zone, f.goal_zones),
        (Event.turnover_type, f.turnover_types),
    ):
        if values:
            eq = eq.where(col.in_(values))
    eq = eq.where(*_tag_condition(f, Event.id))
    events = list((await ctx.db.scalars(eq)).all())

    clips: list[Clip] = []
    attribute_filter = any(
        (f.types, f.sides, f.outcomes, f.player_ids, f.numbers, f.shot_zones, f.goal_zones)
    ) or bool(f.turnover_types)
    # clips have no event attributes: they only match on tags (or when nothing else is asked)
    if f.include_clips and not attribute_filter:
        cq = select(Clip).where(Clip.match_id.in_(match_ids))
        cq = cq.where(*_tag_condition(f, Clip.id))
        clips = list((await ctx.db.scalars(cq)).all())

    links = (
        await ctx.db.execute(
            select(ClipTag.event_id, ClipTag.clip_id, ClipTag.tag_id).where(
                or_(
                    ClipTag.event_id.in_([e.id for e in events]),
                    ClipTag.clip_id.in_([c.id for c in clips]),
                )
            )
        )
    ).all()
    tags_of: dict[uuid.UUID, list[uuid.UUID]] = {}
    for event_id, clip_id, tag_id in links:
        target = event_id or clip_id
        if target is not None:
            tags_of.setdefault(target, []).append(tag_id)

    used = {e.match_id for e in events} | {c.match_id for c in clips}
    meta = {
        m.id: (m, name)
        for m, name in (
            await ctx.db.execute(
                select(Match, Opponent.name)
                .outerjoin(Opponent, Opponent.id == Match.opponent_id)
                .where(Match.id.in_(used))
            )
        ).all()
    }
    videos = dict(
        (
            await ctx.db.execute(
                select(VideoAsset.match_id, VideoAsset.id).where(
                    VideoAsset.match_id.in_(used),
                    VideoAsset.role == VideoRole.MAIN,
                    VideoAsset.status == VideoStatus.READY,
                )
            )
        ).all()
    )

    def label(match_id: uuid.UUID) -> str:
        m, name = meta[match_id]
        return name or ("Training" if m.kind == "training" else "")

    hits: list[SearchHit] = []
    for e in events:
        start = max(0, e.t_ms - EVENT_PRE_MS) if e.t_ms is not None else None
        hits.append(
            SearchHit(
                kind="event",
                id=e.id,
                match_id=e.match_id,
                match_label=label(e.match_id),
                kickoff_at=meta[e.match_id][0].kickoff_at,
                video_id=videos.get(e.match_id),
                start_ms=start,
                end_ms=e.t_ms + EVENT_POST_MS if e.t_ms is not None else None,
                t_ms=e.t_ms,
                type=e.type,
                side=e.side,
                outcome=e.outcome,
                number=e.number,
                player_id=e.player_id,
                tag_ids=sorted(tags_of.get(e.id, [])),
            )
        )
    for c in clips:
        hits.append(
            SearchHit(
                kind="clip",
                id=c.id,
                match_id=c.match_id,
                match_label=label(c.match_id),
                kickoff_at=meta[c.match_id][0].kickoff_at,
                video_id=videos.get(c.match_id),
                start_ms=c.start_ms,
                end_ms=c.end_ms,
                t_ms=c.start_ms,
                title=c.title,
                tag_ids=sorted(tags_of.get(c.id, [])),
            )
        )
    hits.sort(key=lambda h: (h.kickoff_at, h.t_ms if h.t_ms is not None else 1 << 40))
    types = Counter(h.type for h in hits if h.type)
    tag_counts = Counter(str(t) for h in hits for t in h.tag_ids)
    return SearchResult(
        hits=hits[: f.limit],
        total=len(hits),
        truncated=len(hits) > f.limit,
        facets={"types": dict(types), "tags": dict(tag_counts)},
    )


# ---- smart playlists -----------------------------------------------------------------------


async def saved_filters(ctx: Ctx, team_id: uuid.UUID) -> list[SavedFilter]:
    team = await get_team(ctx, team_id, Action.PLAYLIST_READ_ALL)
    rows = await ctx.db.scalars(
        select(SavedFilter).where(SavedFilter.team_id == team.id).order_by(SavedFilter.name)
    )
    return list(rows.all())


async def save_filter(ctx: Ctx, team_id: uuid.UUID, data: SavedFilterIn) -> SavedFilter:
    team = await get_team(ctx, team_id, Action.PLAYLIST_WRITE)
    sf = SavedFilter(
        organization_id=team.organization_id,
        team_id=team.id,
        name=data.name,
        query=data.query.model_dump(mode="json", exclude_defaults=True),
        created_by_id=ctx.user_id,
    )
    ctx.db.add(sf)
    await ctx.db.flush()
    await audit.record(ctx, "saved_filter.created", target_type="saved_filter", target_id=sf.id)
    return sf


async def _saved(ctx: Ctx, filter_id: uuid.UUID, action: Action) -> SavedFilter:
    sf = await ctx.db.get(SavedFilter, filter_id)
    if sf is None:
        raise ProblemError(404, "not-found", "Filter not found")
    await get_team(ctx, sf.team_id, action)
    return sf


async def delete_filter(ctx: Ctx, filter_id: uuid.UUID) -> None:
    await ctx.db.delete(await _saved(ctx, filter_id, Action.PLAYLIST_WRITE))


async def run_filter(ctx: Ctx, filter_id: uuid.UUID) -> SearchResult:
    """Smart playlist: the stored filter is evaluated now, so new matches appear automatically."""
    sf = await _saved(ctx, filter_id, Action.PLAYLIST_READ_ALL)
    return await search(ctx, sf.team_id, SearchFilter.model_validate(sf.query))
