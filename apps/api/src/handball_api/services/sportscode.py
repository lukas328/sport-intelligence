"""Sportscode XML and CSV export, Sportscode XML import as own tags (addendum 01, 5.4).

Sportscode (Hudl) timelines are XML files with instances (ID, start and end in seconds, a code and
labels with group and text) and rows (one per code, with an RGB colour). The export writes every
event with video time and every clip; the import creates clips with source "import": the code
becomes the clip title and a tag of the set "Sportscode", each label a tag in the set named after
its group. Export after import gives the same instances (tested round trip).
"""

from __future__ import annotations

import csv
import io
import uuid
from collections import defaultdict
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

from defusedxml import ElementTree as SafeET
from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.models import Clip, ClipTag, Event, Match, RosterEntry, Tag, TagSet
from handball_api.models.enums import ClipSource
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.events import _to_metric
from handball_api.services.matches import get_match
from handball_api.services.policies import Action
from handball_metrics.stats import zone_of

CODE_SET = "Sportscode"
NO_GROUP = "Sportscode labels"
MAX_BYTES = 5 * 1024 * 1024
MAX_INSTANCES = 5000
PRE_MS, POST_MS = 5000, 3000
EVENT_CODES = {
    ("own", "shot"): "Own shot",
    ("opponent", "shot"): "Opponent shot",
    ("own", "turnover"): "Own turnover",
    ("opponent", "turnover"): "Opponent turnover",
}


def _seconds(ms: int) -> str:
    return f"{ms / 1000:.3f}"


def _code(e: Event) -> str:
    return EVENT_CODES.get((e.side, e.type), f"{e.side.capitalize()} {e.type.replace('_', ' ')}")


async def _numbers(ctx: Ctx, match: Match) -> dict[uuid.UUID, int | None]:
    return {
        r.player_id: r.jersey_number
        for r in (
            await ctx.db.scalars(
                select(RosterEntry).where(
                    RosterEntry.team_id == match.team_id, RosterEntry.season_id == match.season_id
                )
            )
        ).all()
    }


async def _instances(ctx: Ctx, match: Match) -> list[dict[str, Any]]:
    numbers = await _numbers(ctx, match)
    out: list[dict[str, Any]] = []
    events = (
        await ctx.db.scalars(
            select(Event).where(Event.match_id == match.id, Event.t_ms.is_not(None))
        )
    ).all()
    for e in events:
        assert e.t_ms is not None
        labels: list[tuple[str | None, str]] = []
        number = (
            e.number if e.number is not None else numbers.get(e.player_id) if e.player_id else None
        )
        if e.outcome:
            labels.append(("Outcome", e.outcome))
        if e.type == "shot" and (zone := zone_of(_to_metric(e))):
            labels.append(("Zone", zone))
        if number is not None:
            labels.append(("Number", str(number)))
        labels.append(("Period", str(e.period)))
        out.append(
            {
                "start": max(0, e.t_ms - PRE_MS),
                "end": e.t_end_ms if e.t_end_ms and e.t_end_ms > e.t_ms else e.t_ms + POST_MS,
                "code": _code(e),
                "labels": labels,
            }
        )
    clips = (await ctx.db.scalars(select(Clip).where(Clip.match_id == match.id))).all()
    links = (
        await ctx.db.execute(
            select(ClipTag.clip_id, Tag.name, TagSet.name)
            .join(Tag, Tag.id == ClipTag.tag_id)
            .join(TagSet, TagSet.id == Tag.tag_set_id)
            .where(ClipTag.clip_id.in_([c.id for c in clips]))
        )
    ).all()
    by_clip: dict[uuid.UUID, list[tuple[str | None, str]]] = defaultdict(list)
    for clip_id, tag, tag_set in links:
        if tag_set == CODE_SET or clip_id is None:
            continue
        by_clip[clip_id].append((None if tag_set == NO_GROUP else tag_set, tag))
    for c in clips:
        out.append(
            {
                "start": c.start_ms,
                "end": c.end_ms,
                "code": c.title or "Clip",
                "labels": sorted(by_clip[c.id], key=lambda lt: (lt[0] or "", lt[1])),
            }
        )
    out.sort(key=lambda i: (i["start"], i["end"], i["code"]))
    return out


async def export_xml(ctx: Ctx, match_id: uuid.UUID) -> tuple[bytes, str]:
    match = await get_match(ctx, match_id)
    instances = await _instances(ctx, match)
    root = Element("file")
    all_i = SubElement(root, "ALL_INSTANCES")
    for n, inst in enumerate(instances, start=1):
        el = SubElement(all_i, "instance")
        SubElement(el, "ID").text = str(n)
        SubElement(el, "start").text = _seconds(inst["start"])
        SubElement(el, "end").text = _seconds(inst["end"])
        SubElement(el, "code").text = inst["code"]
        for group, text in inst["labels"]:
            lab = SubElement(el, "label")
            if group:
                SubElement(lab, "group").text = group
            SubElement(lab, "text").text = text
    rows = SubElement(root, "ROWS")
    for code in sorted({i["code"] for i in instances}):
        row = SubElement(rows, "row")
        SubElement(row, "code").text = code
        r, g, b = _colour(code)
        SubElement(row, "R").text, SubElement(row, "G").text, SubElement(row, "B").text = (
            str(r),
            str(g),
            str(b),
        )
    data = b'<?xml version="1.0" encoding="utf-8"?>\n' + tostring(root, encoding="utf-8")
    await audit.record(ctx, "match.exported", target_type="match", target_id=match.id)
    return data, f"match-{match.kickoff_at.date().isoformat()}-sportscode.xml"


def _colour(code: str) -> tuple[int, int, int]:
    """A stable colour per code (Sportscode stores 16-bit channels)."""
    h = sum(ord(c) * (i + 1) for i, c in enumerate(code))
    return ((h * 97) % 65535, (h * 193) % 65535, (h * 389) % 65535)


def parse_xml(data: bytes) -> list[dict[str, Any]]:
    if len(data) > MAX_BYTES:
        raise ProblemError(413, "file-too-large", "The XML file is larger than 5 MB")
    try:
        root = SafeET.fromstring(data)
    except Exception as exc:  # defusedxml raises several types for unsafe or broken XML
        raise ProblemError(422, "invalid-format", "Not a readable XML file") from exc
    out = []
    for el in root.iter("instance"):
        try:
            start = round(float((el.findtext("start") or "").strip()) * 1000)
            end = round(float((el.findtext("end") or "").strip()) * 1000)
        except ValueError:
            continue
        code = (el.findtext("code") or "").strip()
        if not code or end <= start or start < 0:
            continue
        labels = []
        for lab in el.findall("label"):
            text = (lab.findtext("text") or "").strip()
            if text:
                group = (lab.findtext("group") or "").strip() or None
                labels.append((group, text))
        out.append({"start": start, "end": end, "code": code, "labels": labels})
        if len(out) > MAX_INSTANCES:
            raise ProblemError(422, "invalid-format", "More than 5000 instances")
    if not out:
        raise ProblemError(422, "invalid-format", "No instances found")
    return out


async def import_xml(ctx: Ctx, match_id: uuid.UUID, data: bytes) -> dict[str, int]:
    match = await get_match(ctx, match_id, Action.CLIP_WRITE)
    instances = parse_xml(data)
    sets: dict[str, TagSet] = {
        s.name: s
        for s in (await ctx.db.scalars(select(TagSet).where(TagSet.team_id == match.team_id))).all()
    }
    tags: dict[tuple[str, str], Tag] = {}
    for t, set_name in (
        await ctx.db.execute(
            select(Tag, TagSet.name)
            .join(TagSet, TagSet.id == Tag.tag_set_id)
            .where(TagSet.team_id == match.team_id)
        )
    ).all():
        tags[(set_name, t.name)] = t
    created_tags = 0

    async def tag_for(set_name: str, name: str) -> Tag:
        nonlocal created_tags
        set_name, name = set_name[:60], name[:60]
        if set_name not in sets:
            ts = TagSet(organization_id=match.organization_id, team_id=match.team_id, name=set_name)
            ctx.db.add(ts)
            await ctx.db.flush()
            sets[set_name] = ts
        if (set_name, name) not in tags:
            tag = Tag(
                organization_id=match.organization_id, tag_set_id=sets[set_name].id, name=name
            )
            ctx.db.add(tag)
            await ctx.db.flush()
            tags[(set_name, name)] = tag
            created_tags += 1
        return tags[(set_name, name)]

    for inst in instances:
        clip = Clip(
            organization_id=match.organization_id,
            match_id=match.id,
            start_ms=inst["start"],
            end_ms=inst["end"],
            title=inst["code"][:200],
            source=ClipSource.IMPORT,
            created_by_id=ctx.user_id,
        )
        ctx.db.add(clip)
        await ctx.db.flush()
        linked = {(await tag_for(CODE_SET, inst["code"])).id}
        for group, text in inst["labels"]:
            linked.add((await tag_for(group or NO_GROUP, text)).id)
        for tag_id in linked:
            ctx.db.add(
                ClipTag(organization_id=match.organization_id, clip_id=clip.id, tag_id=tag_id)
            )
    await ctx.db.flush()
    await audit.record(ctx, "match.imported_sportscode", target_type="match", target_id=match.id)
    return {"clips": len(instances), "tags_created": created_tags}


async def events_csv(ctx: Ctx, match_id: uuid.UUID) -> tuple[bytes, str]:
    match = await get_match(ctx, match_id)
    numbers = await _numbers(ctx, match)
    events = (
        await ctx.db.scalars(
            select(Event)
            .where(Event.match_id == match.id)
            .order_by(Event.period, Event.clock_s, Event.t_ms)
        )
    ).all()
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(
        [
            "period",
            "clock_s",
            "video_ms",
            "type",
            "side",
            "outcome",
            "zone",
            "shot_type",
            "goal_zone",
            "number",
            "x",
            "y",
            "source",
            "confidence",
        ]
    )
    for e in events:
        number = (
            e.number if e.number is not None else numbers.get(e.player_id) if e.player_id else None
        )
        w.writerow(
            [
                e.period,
                e.clock_s if e.clock_s is not None else "",
                e.t_ms if e.t_ms is not None else "",
                e.type,
                e.side,
                e.outcome or "",
                (zone_of(_to_metric(e)) or "") if e.type == "shot" else "",
                e.shot_type or "",
                e.goal_zone or "",
                number if number is not None else "",
                e.x if e.x is not None else "",
                e.y if e.y is not None else "",
                e.source,
                e.confidence,
            ]
        )
    return ("﻿" + buf.getvalue()).encode(), f"match-{match.kickoff_at.date().isoformat()}-events.csv"
