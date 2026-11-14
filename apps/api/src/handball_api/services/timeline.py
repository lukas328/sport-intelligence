"""One match over several files (Q-VIDEO-PARTS).

A match's main files are its parts (two halves, a recording the phone split). They lie one after
the other on the match timeline (services/matches.parts_of). Everything that belongs to the match
(events, possessions, goal and shot candidates, clips, comments, drawings, throw-off times) carries
times on that timeline; tracks, the court and formations stay per file.

When the parts change (a part is added or deleted, a person swaps the order, a part fails), every
match row moves with the part it lies in: `settle` compares the layout before and after and shifts
the rows of each part by the change of its start. Nothing a person confirmed is dropped; only the
automatic rows of a part that left the timeline go with it.

The player: the first part's playlists join all parts (`joined_playlist`), segment by segment with a
discontinuity between files and without re-encoding, so every player that plays the match video
plays the whole match on its timeline.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Integer, and_, case, delete, select, update
from sqlalchemy.orm import InstrumentedAttribute

from handball_api.models import (
    Annotation,
    Clip,
    Comment,
    Event,
    GoalCandidate,
    Match,
    Possession,
    VideoAsset,
)
from handball_api.services import matches, segments
from handball_api.services.context import Ctx
from handball_api.services.matches import Part, locate, parts_of, second_half

AUTOMATIC_SOURCES = ("heuristic", "scoreboard_ocr")


# ---- the layout and its changes --------------------------------------------------------------


@dataclass(frozen=True)
class Move:
    """Rows whose anchor time lies in [lo, hi) move by `delta` (None: the part left the
    timeline)."""

    video_id: uuid.UUID
    lo: int | None
    hi: int | None
    delta: int | None


def moves(before: list[Part], after: list[Part], lead: uuid.UUID | None = None) -> list[Move]:
    """How each placed part of `before` moves in `after`. The last part also takes the times
    after it (events past the end). The times before the timeline (a throw-off before the video
    began, report events placed by it) belong to `lead`, the part they belonged to when they were
    set (by default the first one), and move with it wherever it goes: swapped and swapped back,
    they are where they were."""
    placed = [p for p in before if p.offset_ms is not None]
    now = {p.video_id: p for p in after}
    if lead is None or all(p.video_id != lead for p in placed):
        lead = placed[0].video_id if placed else None
    out: list[Move] = []

    def delta(p: Part) -> int | bool | None:
        q = now.get(p.video_id)
        if q is None or q.offset_ms is None:
            return None
        return False if q.offset_ms == p.offset_ms else int(q.offset_ms) - int(p.offset_ms or 0)

    for i, p in enumerate(placed):
        d = delta(p)
        if d is False:
            continue
        lo = int(p.offset_ms or 0) if i else (None if p.video_id == lead else 0)
        hi = None if i == len(placed) - 1 else int(placed[i + 1].offset_ms or 0)
        out.append(Move(p.video_id, lo, hi, None if d is None else int(d)))
        if i and p.video_id == lead:
            out.append(Move(p.video_id, None, int(placed[0].offset_ms or 0), d or None))
    return out


def _inside(col: Any, m: Move) -> Any:
    conds = []
    if m.lo is not None:
        conds.append(col >= m.lo)
    if m.hi is not None:
        conds.append(col < m.hi)
    return and_(*conds) if conds else col.is_not(None)


def shift_value(t: int | None, ms: list[Move]) -> int | None:
    """A single time moved by the same rules (throw-off times, JSON values)."""
    if t is None:
        return None
    for m in ms:
        if (m.lo is None or t >= m.lo) and (m.hi is None or t < m.hi):
            return None if m.delta is None else t + m.delta
    return t


# (model, anchor column, columns that move with it)
_TABLES: list[tuple[Any, InstrumentedAttribute[Any], list[InstrumentedAttribute[Any]]]] = [
    (Event, Event.t_ms, [Event.t_ms, Event.t_end_ms]),
    (Possession, Possession.start_ms, [Possession.start_ms, Possession.end_ms]),
    (
        GoalCandidate,
        GoalCandidate.goal_ms,
        [GoalCandidate.t_ms, GoalCandidate.goal_ms, GoalCandidate.start_ms, GoalCandidate.end_ms],
    ),
    (Clip, Clip.start_ms, [Clip.start_ms, Clip.end_ms]),
    (Comment, Comment.t_ms, [Comment.t_ms]),
    (Annotation, Annotation.t_ms, [Annotation.t_ms]),
]


# report_extra: which part the throw-offs and the times before the timeline belong to, kept
# through every change of the order: {"kickoffs": {half: {"video_id", "t_ms"}}, "lead": video_id}.
# A throw-off record holds while the throw-off still has that time; "lead" is the part a time
# before the timeline (a throw-off before the video began, report events placed by it) moves with.
OWNERS = "timeline_owners"


def _owners(match: Match) -> dict[str, Any]:
    rec = (match.report_extra or {}).get(OWNERS)
    return rec if isinstance(rec, dict) else {}


def lead_part(match: Match, parts: list[Part]) -> uuid.UUID | None:
    """The part the times before the timeline belong to, when known (`OWNERS`)."""
    vid = str(_owners(match).get("lead"))
    return next((p.video_id for p in parts if str(p.video_id) == vid), None)


def _move_kickoffs(match: Match, ms: list[Move]) -> None:
    """The throw-offs moved with the part they belong to (also one before the timeline, or one
    that moved into another part's old stretch), and the owners kept for the next change."""
    owners = _owners(match)
    raw_known = owners.get("kickoffs")
    known: dict[str, Any] = raw_known if isinstance(raw_known, dict) else {}
    kept: dict[str, int] = {}
    recs: dict[str, Any] = {}
    for k, raw in (match.kickoff_ms or {}).items():
        v = int(raw)
        rec = known.get(k)
        owner = str(rec["video_id"]) if isinstance(rec, dict) and rec.get("t_ms") == v else None
        if owner is not None:
            m = next((m for m in ms if str(m.video_id) == owner), None)
        else:
            m = next(
                (m for m in ms if (m.lo is None or v >= m.lo) and (m.hi is None or v < m.hi)),
                None,
            )
        if m is not None and m.delta is None:
            continue  # its part left the timeline
        new = v if m is None else v + int(m.delta or 0)
        kept[k] = new
        if m is not None:
            recs[k] = {"video_id": str(m.video_id), "t_ms": new}
        elif owner is not None:
            recs[k] = rec
    if kept != match.kickoff_ms:
        match.kickoff_ms = kept or None
    first = next((m for m in ms if m.lo is None), None)
    lead = (
        owners.get("lead")
        if first is None
        else (None if first.delta is None else str(first.video_id))
    )
    out = {k: v for k, v in (("kickoffs", recs), ("lead", lead)) if v}
    extra = {**(match.report_extra or {}), OWNERS: out}
    if not out:
        extra.pop(OWNERS)
    if extra != (match.report_extra or {}):
        match.report_extra = extra or None


def forget_lead(match: Match) -> None:
    """A throw-off set anew: times before the timeline belong to the first part again."""
    owners = _owners(match)
    if "lead" in owners:
        rest = {k: v for k, v in owners.items() if k != "lead"}
        extra = {**(match.report_extra or {}), OWNERS: rest}
        if not rest:
            extra.pop(OWNERS)
        match.report_extra = extra or None


def swap_halves(match: Match) -> None:
    """The throw-offs of the two halves change places (the earlier one is the first half's)."""
    k = match.kickoff_ms or {}
    match.kickoff_ms = {**k, "1": int(k["2"]), "2": int(k["1"])}
    owners = _owners(match)
    known = owners.get("kickoffs")
    if isinstance(known, dict) and known:
        swapped = {str(3 - int(h)) if h in ("1", "2") else h: rec for h, rec in known.items()}
        match.report_extra = {**(match.report_extra or {}), OWNERS: {**owners, "kickoffs": swapped}}


async def apply_moves(ctx: Ctx, match: Match, ms: list[Move]) -> None:
    """Moves the match's rows: in one UPDATE per table, every row decided on its old time (so a
    row moved into another part's old stretch is not moved twice)."""
    gone = [m for m in ms if m.delta is None]
    shifts = [m for m in ms if m.delta is not None]
    for m in gone:
        # what the analysis of a part found goes with the part; the coach's rows stay, without a
        # place on the video (a report event keeps its match clock)
        await ctx.db.execute(
            delete(Event).where(
                Event.match_id == match.id,
                Event.source.in_(AUTOMATIC_SOURCES),
                _inside(Event.t_ms, m),
            )
        )
        await ctx.db.execute(
            delete(Possession).where(
                Possession.match_id == match.id,
                Possession.source == "heuristic",
                _inside(Possession.start_ms, m),
            )
        )
        await ctx.db.execute(
            delete(GoalCandidate).where(GoalCandidate.video_asset_id == m.video_id)
        )
        await ctx.db.execute(
            update(Event)
            .where(Event.match_id == match.id, _inside(Event.t_ms, m))
            .values(t_ms=None, t_end_ms=None)
        )
        for model, anchor in ((Clip, Clip.start_ms), (Comment, Comment.t_ms)):
            await ctx.db.execute(
                delete(model).where(model.match_id == match.id, _inside(anchor, m))
            )
        await ctx.db.execute(
            delete(Annotation).where(Annotation.match_id == match.id, _inside(Annotation.t_ms, m))
        )
    if shifts:
        for model, anchor, cols in _TABLES:
            whens = [(_inside(anchor, m), int(m.delta or 0)) for m in shifts]
            delta = case(*whens, else_=0).cast(Integer)
            values = {c.key: case((c.is_(None), None), else_=c + delta) for c in cols}
            await ctx.db.execute(
                update(model)
                .where(model.match_id == match.id)
                .values(**values)
                .execution_options(synchronize_session=False)
            )
    if match.kickoff_ms:
        _move_kickoffs(match, ms)
    await ctx.db.flush()
    # rows of these tables already loaded in the session would hide the new times
    stale = (Event, Possession, GoalCandidate, Clip, Comment, Annotation)
    for obj in list(ctx.db.identity_map.values()):
        if isinstance(obj, stale):
            ctx.db.expire(obj)


async def settle(ctx: Ctx, match: Match, before: list[Part]) -> list[Part]:
    """After a change of the files: the parts' order again, then the match rows moved with their
    part. Returns the new layout."""
    await segments.rebuild(ctx, match)
    after = await parts_of(ctx, match.id)
    ms = moves(before, after, lead_part(match, before))
    if ms:
        await apply_moves(ctx, match, ms)
        await ctx.db.refresh(match)
    return after


# ---- an analysis result on the timeline --------------------------------------------------------


def shift_times(value: Any, offset: int, keys: Sequence[str]) -> Any:
    """A copy of a worker result with every time under `keys` (in dicts at any depth) moved."""
    if offset == 0:
        return value
    if isinstance(value, list):
        return [shift_times(v, offset, keys) for v in value]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if k in keys and isinstance(v, int | float) and not isinstance(v, bool):
                out[k] = int(v) + offset
            else:
                out[k] = shift_times(v, offset, keys)
        return out
    return value


EVENT_TIMES = ("t_ms", "end_ms", "start_ms", "from_ms")
OVERLAY_TIMES = ("t_ms", "start_ms", "end_ms")
CANDIDATE_TIMES = ("t_ms", "goal_ms", "start_ms", "end_ms")


def is_second_half(parts: list[Part], part: Part) -> bool:
    """A part that is recognisably the second half (matches.second_half)."""
    return second_half(parts, part)


def side_hint(parts: list[Part], part: Part, analyses: dict[uuid.UUID, Any]) -> str | None:
    """The side the home team defends in a second half: the other one than at the end of the part
    before (the teams change ends at half-time)."""
    if not is_second_half(parts, part):
        return None
    prev = (
        next(
            p
            for p in reversed(parts[: part.position])
            if p.duration_ms is None or p.duration_ms >= matches.MIN_HALF_MS
        )
        if part.position
        else parts[0]
    )
    sides = ((analyses.get(prev.video_id) or {}).get("auto_events") or {}).get("sides") or []
    last = sides[-1].get("home_defends") if sides and isinstance(sides[-1], dict) else None
    return {"left": "right", "right": "left"}.get(str(last))


async def side_hint_for(ctx: Ctx, asset: VideoAsset) -> str | None:
    parts = await parts_of(ctx, asset.match_id)
    part = next((p for p in parts if p.video_id == asset.id), None)
    if part is None or not is_second_half(parts, part):
        return None
    rows = await ctx.db.execute(
        select(VideoAsset.id, VideoAsset.analysis).where(
            VideoAsset.id.in_([p.video_id for p in parts[: part.position]])
        )
    )
    return side_hint(parts, part, {vid: meta for vid, meta in rows.all()})


# ---- the joined player playlist ----------------------------------------------------------------

_VARIANT = re.compile(r"^(\d+)p/index\.m3u8$")


def variants(master: str) -> list[str]:
    """The variant names of an HLS master playlist ("720p", "1080p")."""
    out = []
    for line in master.splitlines():
        m = _VARIANT.match(line.strip())
        if m:
            out.append(f"{m.group(1)}p")
    return out


def nearest_variant(name: str, available: list[str]) -> str | None:
    if name in available or not available:
        return name if name in available else None
    want = int(name.rstrip("p"))
    return min(available, key=lambda v: abs(int(v.rstrip("p")) - want))


def join_variants(playlists: list[tuple[str, str]]) -> str:
    """One VOD playlist of several files' variant playlists (`(text, prefix)` per file, `prefix`
    leading from the first playlist's place to the file's variant folder). Each file after the
    first starts with a discontinuity and its own init segment."""
    target = 1
    body: list[str] = []
    for i, (text, prefix) in enumerate(playlists):
        if i:
            body.append("#EXT-X-DISCONTINUITY")
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#EXT-X-TARGETDURATION:"):
                target = max(target, int(float(line.split(":", 1)[1])))
            elif line.startswith("#EXT-X-MAP:"):
                uri = re.search(r'URI="([^"]+)"', line)
                body.append(
                    line.replace(uri.group(0), f'URI="{prefix}{uri.group(1)}"') if uri else line
                )
            elif line.startswith("#EXTINF") or line.startswith("#EXT-X-BYTERANGE"):
                body.append(line)
            elif not line.startswith("#"):
                body.append(prefix + line)
    head = [
        "#EXTM3U",
        "#EXT-X-VERSION:7",
        f"#EXT-X-TARGETDURATION:{target}",
        "#EXT-X-MEDIA-SEQUENCE:0",
        "#EXT-X-PLAYLIST-TYPE:VOD",
        "#EXT-X-INDEPENDENT-SEGMENTS",
    ]
    return "\n".join([*head, *body, "#EXT-X-ENDLIST", ""])


def _ts(s: float) -> str:
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{sec:06.3f}"


def _secs(t: str) -> float:
    total = 0.0
    for p in t.strip().split(":"):
        total = total * 60 + float(p)
    return total


def join_thumbs(files: list[tuple[str, str, float]]) -> str:
    """The hover previews of several files as one WebVTT (`(text, prefix, offset_s)` per file)."""
    out = ["WEBVTT", ""]
    for text, prefix, offset in files:
        for block in re.split(r"\r?\n\r?\n", text):
            lines = [x.strip() for x in block.strip().splitlines()]
            timing = next((x for x in lines if "-->" in x), None)
            if timing is None:
                continue
            target = lines[lines.index(timing) + 1] if lines.index(timing) + 1 < len(lines) else ""
            if not target:
                continue
            a, b = timing.split("-->")
            out += [f"{_ts(_secs(a) + offset)} --> {_ts(_secs(b) + offset)}", prefix + target, ""]
    return "\n".join(out)


async def joined_playlist(
    ctx: Ctx,
    asset: VideoAsset,
    path: str,
    read: Callable[[VideoAsset, str], Any],
    sibling: Callable[[VideoAsset], str],
) -> bytes | None:
    """The playlist `path` of the first part, joined over all parts that play; None when the
    asset is not the first of several parts or `path` is not a joined file. `read(asset, path)`
    reads a file of a part, `sibling(part)` is the path from the videos folder of the URL to that
    part's media folder."""
    if not (path == "thumbs.vtt" or path.endswith("/index.m3u8")):
        return None
    parts = [p for p in await parts_of(ctx, asset.match_id) if p.offset_ms is not None]
    if len(parts) < 2 or parts[0].video_id != asset.id:
        return None
    assets = {
        a.id: a
        for a in (
            await ctx.db.scalars(
                select(VideoAsset).where(VideoAsset.id.in_([p.video_id for p in parts]))
            )
        ).all()
    }
    playing = [(p, assets[p.video_id]) for p in parts if assets[p.video_id].hls_prefix]
    if len(playing) < 2:
        return None
    up = "../" * (path.count("/") + 2)  # from the playlist's folder to the videos folder
    if path == "thumbs.vtt":
        thumbs: list[tuple[str, str, float]] = []
        for p, a in playing:
            data = await read(a, "thumbs.vtt")
            if data is None:
                continue
            prefix = "" if a.id == asset.id else up + sibling(a)
            thumbs.append((data.decode(), prefix, int(p.offset_ms or 0) / 1000))
        return join_thumbs(thumbs).encode()
    name = path.split("/")[-2]
    lists: list[tuple[str, str]] = []
    for _, a in playing:
        own = a.id == asset.id
        variant = name
        if not own:
            master = await read(a, "hls/master.m3u8")
            variant = nearest_variant(name, variants(master.decode()) if master else []) or name
        data = await read(a, f"hls/{variant}/index.m3u8")
        if data is None:
            return None
        lists.append((data.decode(), "" if own else f"{up}{sibling(a)}hls/{variant}/"))
    return join_variants(lists).encode()


# ---- reading a timeline time in its file ----------------------------------------------------


class Files:
    """The files of a match for reading timeline times in them (tracks, court): each part's video
    and the time in it. A match without placed parts reads its timeline video as it is."""

    def __init__(self, parts: list[Part], fallback: VideoAsset | None, assets: dict[Any, Any]):
        self.parts = parts
        self.fallback = fallback
        self.assets: dict[uuid.UUID, VideoAsset] = assets

    @classmethod
    async def of(cls, ctx: Ctx, match_id: uuid.UUID) -> Files:
        from handball_api.services.matches import timeline_video

        parts = [p for p in await parts_of(ctx, match_id) if p.offset_ms is not None]
        assets = (
            {
                a.id: a
                for a in (
                    await ctx.db.scalars(
                        select(VideoAsset).where(VideoAsset.id.in_([p.video_id for p in parts]))
                    )
                ).all()
            }
            if parts
            else {}
        )
        fallback = None if parts else await timeline_video(ctx, match_id)
        return cls(parts, fallback, assets)

    def at(self, t_ms: int) -> tuple[VideoAsset, int] | None:
        """The file a timeline time lies in and the time in that file."""
        hit = locate(self.parts, t_ms)
        if hit is None:
            return (self.fallback, t_ms) if self.fallback is not None else None
        asset = self.assets.get(hit[0].video_id)
        return (asset, hit[1]) if asset is not None else None

    def all(self) -> list[tuple[VideoAsset, int]]:
        """Every file with its start on the timeline."""
        if not self.parts:
            return [(self.fallback, 0)] if self.fallback is not None else []
        return [
            (self.assets[p.video_id], int(p.offset_ms or 0))
            for p in self.parts
            if p.video_id in self.assets
        ]


async def clock_analysis(ctx: Ctx, match_id: uuid.UUID) -> dict[str, Any] | None:
    """The overlay clock the analysis read, on the match timeline: the runs of every part moved
    by the part's start (what match_clock.build reads of an analysis)."""
    files = await Files.of(ctx, match_id)
    pairs = files.all()
    if len(pairs) == 1:
        return pairs[0][0].analysis
    runs: list[Any] = []
    for asset, offset in pairs:
        board = (asset.analysis or {}).get("scoreboard")
        clock = board.get("clock") if isinstance(board, dict) else None
        runs += shift_times(list(clock or []), offset, ("start_ms", "end_ms"))
    return {"scoreboard": {"clock": runs}} if runs else None
