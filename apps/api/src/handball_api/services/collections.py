"""Collections (SPEC 7.7, "Sammlung"): one object instead of playlist, presentation and assignment.

A collection is an ordered run of entries of three kinds: a scene (a clip, i.e. a window of a match
video), a play or a note. Playlists, presentations and assignments stay as data and are read as
collections (`source` says which): their entries are mapped, they are not copied or changed here.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import func, select

from handball_api.core.errors import ProblemError
from handball_api.models import (
    Assignment,
    Clip,
    Collection,
    CollectionItem,
    Event,
    Match,
    Play,
    Playlist,
    PlaylistItem,
    Presentation,
    PresentationSlide,
)
from handball_api.models.enums import ClipSource, SlideType
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.insights import insights
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action

Source = Literal["collection", "playlist", "presentation", "assignment"]
# a scene made from an event: a little before the moment and a little after
BEFORE_MS, AFTER_MS = 5_000, 3_000
MAX_ITEMS = 200


def _clip_out(c: Clip) -> dict[str, Any]:
    return {
        "clip_id": str(c.id),
        "match_id": str(c.match_id),
        "start_ms": c.start_ms,
        "end_ms": c.end_ms,
        "title": c.title,
    }


async def _scene(ctx: Ctx, clip_id: uuid.UUID | None, text: str | None) -> dict[str, Any] | None:
    clip = await ctx.db.get(Clip, clip_id) if clip_id else None
    if clip is None:
        return None
    return {"kind": "scene", "text": text, "scene": _clip_out(clip), "play": None}


async def _play(ctx: Ctx, play_id: uuid.UUID | None, text: str | None) -> dict[str, Any] | None:
    play = await ctx.db.get(Play, play_id) if play_id else None
    if play is None:
        return None
    return {
        "kind": "play",
        "text": text,
        "scene": None,
        "play": {"id": str(play.id), "name": play.name},
    }


def _note(text: str | None) -> dict[str, Any] | None:
    return {"kind": "note", "text": text, "scene": None, "play": None} if text else None


def _numbered(items: list[dict[str, Any] | None]) -> list[dict[str, Any]]:
    out = [i for i in items if i is not None]
    for n, i in enumerate(out):
        i["position"] = n
    return out


# ---- reading every kind -----------------------------------------------------------------------


async def _items_of_collection(ctx: Ctx, c: Collection) -> list[dict[str, Any]]:
    rows = (
        await ctx.db.scalars(
            select(CollectionItem)
            .where(CollectionItem.collection_id == c.id)
            .order_by(CollectionItem.position)
        )
    ).all()
    items: list[dict[str, Any] | None] = []
    for r in rows:
        if r.kind == "scene":
            items.append(await _scene(ctx, r.clip_id, r.text))
        elif r.kind == "play":
            items.append(await _play(ctx, r.play_id, r.text))
        else:
            items.append(_note(r.text))
    return _numbered(items)


async def _items_of_playlist(ctx: Ctx, playlist_id: uuid.UUID) -> list[dict[str, Any]]:
    rows = (
        await ctx.db.scalars(
            select(PlaylistItem)
            .where(PlaylistItem.playlist_id == playlist_id)
            .order_by(PlaylistItem.position)
        )
    ).all()
    return _numbered([await _scene(ctx, r.clip_id, r.note) for r in rows])


def _slide_text(content: dict[str, Any]) -> str | None:
    parts = [content.get(k) for k in ("title", "text", "body")]
    text = "\n".join(p for p in parts if isinstance(p, str) and p.strip())
    return text or None


async def _items_of_presentation(ctx: Ctx, pres_id: uuid.UUID) -> list[dict[str, Any]]:
    slides = (
        await ctx.db.scalars(
            select(PresentationSlide)
            .where(PresentationSlide.presentation_id == pres_id)
            .order_by(PresentationSlide.position)
        )
    ).all()
    items: list[dict[str, Any] | None] = []
    for s in slides:
        text = _slide_text(s.content or {})
        if s.type == SlideType.CLIP:
            items.append(await _scene(ctx, s.clip_id, text))
        elif s.type == SlideType.TACTICS_BOARD:
            items.append(await _play(ctx, s.play_id, text))
        else:
            # text, stat card, image: what a person wrote on it
            items.append(_note(text))
    return _numbered(items)


async def _items_of_assignment(ctx: Ctx, a: Assignment) -> list[dict[str, Any]]:
    head = _note(a.note)
    if a.kind == "playlist":
        try:
            rest = await _items_of_playlist(ctx, uuid.UUID(a.target_id))
        except ValueError:
            rest = []
    elif a.kind == "play":
        try:
            rest = [x for x in [await _play(ctx, uuid.UUID(a.target_id), None)] if x]
        except ValueError:
            rest = []
    else:
        # a drill or a whole match: the title says what it is
        rest = []
    return _numbered([head, *rest])


async def _resolve(ctx: Ctx, collection_id: uuid.UUID) -> tuple[Source, Any]:
    for source, model in (
        ("collection", Collection),
        ("playlist", Playlist),
        ("presentation", Presentation),
        ("assignment", Assignment),
    ):
        row = await ctx.db.get(model, collection_id)
        if row is not None:
            return source, row  # type: ignore[return-value]
    raise ProblemError(404, "not-found", "Collection not found")


async def resolve(ctx: Ctx, collection_id: uuid.UUID) -> tuple[Source, Any]:
    """The object behind a collection id, without a permission check (callers check)."""
    return await _resolve(ctx, collection_id)


async def items_of(ctx: Ctx, source: Source, row: Any) -> list[dict[str, Any]]:
    """The entries of any kind of collection (no permission check: callers check)."""
    if source == "collection":
        return await _items_of_collection(ctx, row)
    if source == "playlist":
        return await _items_of_playlist(ctx, row.id)
    if source == "presentation":
        return await _items_of_presentation(ctx, row.id)
    return await _items_of_assignment(ctx, row)


async def get(ctx: Ctx, collection_id: uuid.UUID) -> dict[str, Any]:
    source, row = await _resolve(ctx, collection_id)
    await get_team(ctx, row.team_id, Action.PLAYLIST_READ_ALL)
    items = await items_of(ctx, source, row)
    return {
        "id": str(row.id),
        "team_id": str(row.team_id),
        "title": row.title,
        "source": source,
        "editable": source == "collection",
        "draft": bool(getattr(row, "draft", False)),
        "match_id": str(row.match_id) if getattr(row, "match_id", None) else None,
        "created_at": row.created_at,
        "items": items,
    }


async def list_for_team(ctx: Ctx, team_id: uuid.UUID) -> list[dict[str, Any]]:
    """Every collection of the team, the old kinds included, newest first."""
    team = await get_team(ctx, team_id, Action.PLAYLIST_READ_ALL)
    out: list[dict[str, Any]] = []

    async def counted(model: Any, item: Any, fk: Any, source: Source, *where: Any) -> None:
        rows = (
            await ctx.db.execute(
                select(model, func.count(item.id))
                .outerjoin(item, fk == model.id)
                .where(model.team_id == team.id, *where)
                .group_by(model.id)
            )
        ).all()
        for row, n in rows:
            out.append(
                {
                    "id": str(row.id),
                    "title": row.title,
                    "source": source,
                    "entries": n,
                    "draft": bool(getattr(row, "draft", False)),
                    "created_at": row.created_at,
                }
            )

    await counted(Collection, CollectionItem, CollectionItem.collection_id, "collection")
    await counted(Playlist, PlaylistItem, PlaylistItem.playlist_id, "playlist")
    await counted(
        Presentation, PresentationSlide, PresentationSlide.presentation_id, "presentation"
    )
    assignments = (
        await ctx.db.scalars(select(Assignment).where(Assignment.team_id == team.id))
    ).all()
    for a in assignments:
        out.append(
            {
                "id": str(a.id),
                "title": a.title,
                "source": "assignment",
                "entries": len(await _items_of_assignment(ctx, a)),
                "draft": False,
                "created_at": a.created_at,
            }
        )
    out.sort(key=lambda x: x["created_at"], reverse=True)
    return out


# ---- writing (native collections only) -------------------------------------------------------


async def _native(ctx: Ctx, collection_id: uuid.UUID) -> Collection:
    source, row = await _resolve(ctx, collection_id)
    if source != "collection":
        raise ProblemError(
            409, "read-only-source", f"A {source} is read as a collection and changed where it is"
        )
    await get_team(ctx, row.team_id, Action.PLAYLIST_WRITE)
    return row  # type: ignore[no-any-return]


async def _scene_clip(ctx: Ctx, team_id: uuid.UUID, item: dict[str, Any]) -> uuid.UUID:
    """The clip of a scene entry: given, or made from a match window or an event."""
    if item.get("clip_id"):
        clip = await ctx.db.get(Clip, item["clip_id"])
        match = await ctx.db.get(Match, clip.match_id) if clip else None
        if clip is None or match is None or match.team_id != team_id:
            raise ProblemError(422, "invalid-item", "Scene not found in this team")
        return clip.id
    event = await ctx.db.get(Event, item["event_id"]) if item.get("event_id") else None
    match_id = event.match_id if event else item.get("match_id")
    match = await ctx.db.get(Match, match_id) if match_id else None
    if match is None or match.team_id != team_id:
        raise ProblemError(422, "invalid-item", "A scene needs a clip, an event or a match window")
    if event is not None:
        if event.t_ms is None:
            raise ProblemError(422, "invalid-item", "This event has no place in the video")
        start, end = max(0, event.t_ms - BEFORE_MS), event.t_ms + AFTER_MS
        source = ClipSource.EVENT
    else:
        given_start, given_end = item.get("start_ms"), item.get("end_ms")
        if given_start is None or given_end is None or given_end <= given_start:
            raise ProblemError(422, "invalid-item", "A scene window needs start_ms < end_ms")
        start, end = int(given_start), int(given_end)
        source = ClipSource.MANUAL
    clip = Clip(
        organization_id=match.organization_id,
        match_id=match.id,
        start_ms=start,
        end_ms=end,
        title=item.get("title"),
        source=source,
        source_ref=event.id if event else None,
        created_by_id=ctx.user_id,
    )
    ctx.db.add(clip)
    await ctx.db.flush()
    return clip.id


async def _write_items(ctx: Ctx, c: Collection, items: list[dict[str, Any]]) -> None:
    if len(items) > MAX_ITEMS:
        raise ProblemError(422, "too-many-items", f"At most {MAX_ITEMS} entries")
    for old in (
        await ctx.db.scalars(select(CollectionItem).where(CollectionItem.collection_id == c.id))
    ).all():
        await ctx.db.delete(old)
    await ctx.db.flush()
    for n, item in enumerate(items):
        row = CollectionItem(
            organization_id=c.organization_id,
            collection_id=c.id,
            position=n,
            kind=item["kind"],
            text=item.get("text"),
        )
        if item["kind"] == "scene":
            row.clip_id = await _scene_clip(ctx, c.team_id, item)
        elif item["kind"] == "play":
            play = await ctx.db.get(Play, item.get("play_id")) if item.get("play_id") else None
            if play is None or play.team_id != c.team_id:
                raise ProblemError(422, "invalid-item", "Play not found in this team")
            row.play_id = play.id
        elif not item.get("text"):
            raise ProblemError(422, "invalid-item", "A note needs text")
        ctx.db.add(row)
    await ctx.db.flush()


async def create(
    ctx: Ctx,
    team_id: uuid.UUID,
    title: str,
    items: list[dict[str, Any]],
    *,
    draft: bool = False,
    match_id: uuid.UUID | None = None,
) -> Collection:
    team = await get_team(ctx, team_id, Action.PLAYLIST_WRITE)
    c = Collection(
        organization_id=team.organization_id,
        team_id=team.id,
        title=title,
        draft=draft,
        match_id=match_id,
        created_by_id=ctx.user_id,
    )
    ctx.db.add(c)
    await ctx.db.flush()
    await _write_items(ctx, c, items)
    await audit.record(ctx, "collection.created", target_type="collection", target_id=c.id)
    return c


async def update(
    ctx: Ctx,
    collection_id: uuid.UUID,
    *,
    title: str | None = None,
    draft: bool | None = None,
    items: list[dict[str, Any]] | None = None,
) -> Collection:
    c = await _native(ctx, collection_id)
    if title is not None:
        c.title = title
    if draft is not None:
        c.draft = draft
    if items is not None:
        await _write_items(ctx, c, items)
        c.updated_at = datetime.now(c.created_at.tzinfo)
    return c


async def delete(ctx: Ctx, collection_id: uuid.UUID) -> None:
    c = await _native(ctx, collection_id)
    await ctx.db.delete(c)
    await audit.record(ctx, "collection.deleted", target_type="collection", target_id=c.id)


async def from_match(ctx: Ctx, team_id: uuid.UUID, match_id: uuid.UUID, title: str) -> Collection:
    """'Fürs Team zusammenstellen': a draft from the three things of a match, the scenes behind
    each, for the coach to trim."""
    match = await ctx.db.get(Match, match_id)
    if match is None or match.team_id != team_id:
        raise ProblemError(404, "not-found", "Match not found")
    things = (await insights(ctx, match_id))["insights"][:3]
    items: list[dict[str, Any]] = []
    for thing in things:
        ev = thing.get("evidence") or {}
        q = select(Event).where(Event.match_id == match_id, Event.t_ms.is_not(None))
        for key, col in (
            ("side", Event.side),
            ("type", Event.type),
            ("outcome", Event.outcome),
            ("zone", Event.shot_zone),
            ("goal_zone", Event.goal_zone),
        ):
            if ev.get(key) is not None:
                q = q.where(col == ev[key])
        for e in (await ctx.db.scalars(q.order_by(Event.t_ms).limit(4))).all():
            items.append({"kind": "scene", "event_id": e.id})
    return await create(ctx, team_id, title, items, draft=True, match_id=match_id)
