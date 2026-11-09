"""Presentation mode for the team video session (addendum 01, 4.1).

Slides: clip (window of a match video with hold points, slow motion, drawings, spotlight), tactics
board (a play), text, stat card and image. The phone remote pairs with a short-lived key and sends
commands that the presenter receives over Server-Sent Events (same event bus as job progress).
"""

from __future__ import annotations

import io
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import func, select

from handball_api.core.errors import ProblemError
from handball_api.models import (
    CameraCalibration,
    Clip,
    Match,
    Play,
    Presentation,
    PresentationSlide,
    ScoutingReport,
    VideoAsset,
)
from handball_api.models.enums import SlideType
from handball_api.schemas.presentations import (
    PresentationIn,
    PresentationPatch,
    SlideIn,
    SlidePatch,
)
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.matches import timeline_video
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action, can
from handball_api.services.report_pdf import _esc, _styles
from handball_api.services.scouting_pdf import observation_text
from handball_api.services.videos import media_prefix

MAX_SLIDES = 200
REMOTE_TTL_S = 4 * 3600
IMAGE_TYPES = {b"\x89PNG": "image/png", b"\xff\xd8\xff": "image/jpeg"}


async def _get(ctx: Ctx, pres_id: uuid.UUID, write: bool = False) -> Presentation:
    p = await ctx.db.get(Presentation, pres_id)
    if p is None:
        raise ProblemError(404, "not-found", "Presentation not found")
    await get_team(ctx, p.team_id, Action.CLIP_WRITE if write else Action.TEAM_READ)
    if (
        not write
        and not p.shared_with_players
        and not can(ctx.require_actor(), Action.PLAYLIST_READ_ALL, p.team_id)
    ):
        raise ProblemError(404, "not-found", "Presentation not found")
    return p


async def list_for_team(ctx: Ctx, team_id: uuid.UUID) -> list[tuple[Presentation, int]]:
    team = await get_team(ctx, team_id)
    q = (
        select(Presentation, func.count(PresentationSlide.id))
        .outerjoin(PresentationSlide, PresentationSlide.presentation_id == Presentation.id)
        .where(Presentation.team_id == team.id)
        .group_by(Presentation.id)
        .order_by(Presentation.created_at.desc())
    )
    if not can(ctx.require_actor(), Action.PLAYLIST_READ_ALL, team.id):
        q = q.where(Presentation.shared_with_players)
    return [(p, n) for p, n in (await ctx.db.execute(q)).all()]


async def create(ctx: Ctx, team_id: uuid.UUID, data: PresentationIn) -> Presentation:
    team = await get_team(ctx, team_id, Action.CLIP_WRITE)
    if data.match_id:
        m = await ctx.db.get(Match, data.match_id)
        if m is None or m.team_id != team.id:
            raise ProblemError(404, "not-found", "Match not found")
    p = Presentation(
        organization_id=team.organization_id,
        team_id=team.id,
        match_id=data.match_id,
        title=data.title,
        created_by_id=ctx.user_id,
    )
    ctx.db.add(p)
    await ctx.db.flush()
    await audit.record(ctx, "presentation.created", target_type="presentation", target_id=p.id)
    return p


async def detail(
    ctx: Ctx, pres_id: uuid.UUID
) -> tuple[Presentation, list[PresentationSlide], bool]:
    p = await _get(ctx, pres_id)
    slides = (
        await ctx.db.scalars(
            select(PresentationSlide)
            .where(PresentationSlide.presentation_id == p.id)
            .order_by(PresentationSlide.position)
        )
    ).all()
    return p, list(slides), can(ctx.require_actor(), Action.CLIP_WRITE, p.team_id)


async def update(ctx: Ctx, pres_id: uuid.UUID, data: PresentationPatch) -> Presentation:
    p = await _get(ctx, pres_id, write=True)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    return p


async def delete(ctx: Ctx, pres_id: uuid.UUID) -> None:
    await ctx.db.delete(await _get(ctx, pres_id, write=True))


def _num(content: dict[str, Any], key: str) -> int:
    v = content.get(key)
    if not isinstance(v, int) or v < 0:
        raise ProblemError(422, "invalid-slide", f"{key} must be a positive number of ms")
    return v


async def _validate(
    ctx: Ctx, p: Presentation, data: SlideIn | SlidePatch, type_: SlideType
) -> None:
    c = data.content if data.content is not None else {}  # the defaults below are stored
    if len(str(c)) > 50_000:
        raise ProblemError(422, "invalid-slide", "Slide content too large")
    if type_ == SlideType.CLIP:
        clip_id = getattr(data, "clip_id", None)
        if clip_id:
            clip = await ctx.db.get(Clip, clip_id)
            owner = await ctx.db.get(Match, clip.match_id) if clip else None
            if clip is None or owner is None or owner.team_id != p.team_id:
                raise ProblemError(404, "not-found", "Clip not found")
            c.setdefault("in_ms", clip.start_ms)
            c.setdefault("out_ms", clip.end_ms)
            if "video_id" not in c:
                # the video the clip's times refer to; a match without one has nothing to play
                main = await timeline_video(ctx, clip.match_id)
                if main is None:
                    raise ProblemError(422, "no-video", "The clip's match has no video yet")
                c["video_id"] = str(main.id)
        if "video_id" in c:
            try:
                video_id = uuid.UUID(str(c["video_id"]))
            except ValueError as exc:
                raise ProblemError(404, "not-found", "Video not found") from exc
            v = await ctx.db.get(VideoAsset, video_id)
            m = await ctx.db.get(Match, v.match_id) if v else None
            if m is None or m.team_id != p.team_id:
                raise ProblemError(404, "not-found", "Video not found")
        if _num(c, "out_ms") <= _num(c, "in_ms"):
            raise ProblemError(422, "invalid-slide", "out_ms must be after in_ms")
    if type_ == SlideType.TACTICS_BOARD and data.play_id:
        play = await ctx.db.get(Play, data.play_id)
        if play is None or play.team_id != p.team_id:
            raise ProblemError(404, "not-found", "Play not found")


async def add_slide(ctx: Ctx, pres_id: uuid.UUID, data: SlideIn) -> PresentationSlide:
    p = await _get(ctx, pres_id, write=True)
    count = await ctx.db.scalar(
        select(func.count(PresentationSlide.id)).where(PresentationSlide.presentation_id == p.id)
    )
    if (count or 0) >= MAX_SLIDES:
        raise ProblemError(422, "too-many-slides", "At most 200 slides")
    await _validate(ctx, p, data, data.type)
    s = PresentationSlide(
        organization_id=p.organization_id,
        presentation_id=p.id,
        position=count or 0,
        type=data.type,
        clip_id=data.clip_id,
        play_id=data.play_id,
        content=data.content,
    )
    ctx.db.add(s)
    await ctx.db.flush()
    return s


async def _slide(ctx: Ctx, slide_id: uuid.UUID) -> tuple[PresentationSlide, Presentation]:
    s = await ctx.db.get(PresentationSlide, slide_id)
    if s is None:
        raise ProblemError(404, "not-found", "Slide not found")
    return s, await _get(ctx, s.presentation_id, write=True)


async def update_slide(ctx: Ctx, slide_id: uuid.UUID, data: SlidePatch) -> PresentationSlide:
    s, p = await _slide(ctx, slide_id)
    if data.content is not None:
        await _validate(ctx, p, data, SlideType(s.type))
        s.content = data.content
    if data.play_id is not None:
        s.play_id = data.play_id
    return s


async def delete_slide(ctx: Ctx, slide_id: uuid.UUID) -> None:
    s, p = await _slide(ctx, slide_id)
    await ctx.db.delete(s)
    await ctx.db.flush()
    await _renumber(ctx, p.id)


async def _renumber(ctx: Ctx, pres_id: uuid.UUID, order: list[uuid.UUID] | None = None) -> None:
    slides = list(
        (
            await ctx.db.scalars(
                select(PresentationSlide)
                .where(PresentationSlide.presentation_id == pres_id)
                .order_by(PresentationSlide.position)
            )
        ).all()
    )
    if order is not None:
        if sorted(order) != sorted(s.id for s in slides):
            raise ProblemError(422, "invalid-order", "Give every slide exactly once")
        by_id = {s.id: s for s in slides}
        slides = [by_id[i] for i in order]
    for i, s in enumerate(slides):
        s.position = i


async def reorder(ctx: Ctx, pres_id: uuid.UUID, order: list[uuid.UUID]) -> None:
    p = await _get(ctx, pres_id, write=True)
    await _renumber(ctx, p.id, order)


async def set_image(ctx: Ctx, slide_id: uuid.UUID, data: bytes) -> None:
    s, p = await _slide(ctx, slide_id)
    if s.type != SlideType.IMAGE:
        raise ProblemError(422, "invalid-slide", "Not an image slide")
    ctype = next((v for k, v in IMAGE_TYPES.items() if data.startswith(k)), None)
    if ctype is None:
        raise ProblemError(415, "unsupported-image", "PNG or JPEG only")
    if len(data) > 3 * 1024 * 1024:
        raise ProblemError(413, "image-too-large", "At most 3 MB")
    key = f"{p.organization_id}/presentations/{p.id}/{s.id}"
    await ctx.storage.put(ctx.settings.s3_bucket_artifacts, key, data, ctype)
    s.content = {**s.content, "image_key": key, "image_type": ctype}


async def get_image(ctx: Ctx, slide_id: uuid.UUID) -> tuple[bytes, str]:
    s = await ctx.db.get(PresentationSlide, slide_id)
    if s is None or "image_key" not in s.content:
        raise ProblemError(404, "not-found", "No image")
    await _get(ctx, s.presentation_id)
    data, _ = await ctx.storage.get(ctx.settings.s3_bucket_artifacts, s.content["image_key"])
    return data, str(s.content.get("image_type", "image/png"))


async def from_scouting(ctx: Ctx, report_id: uuid.UUID) -> Presentation:
    """Preparation report as a presentation (4.6): observations as text, then their clips."""
    rep = await ctx.db.get(ScoutingReport, report_id)
    if rep is None:
        raise ProblemError(404, "not-found", "Report not found")
    f = rep.facts
    p = await create(
        ctx,
        rep.team_id,
        PresentationIn(title=f"{f['opponent']['name']}: Vorbereitung", match_id=rep.match_id),
    )
    g = f["glance"]
    await add_slide(
        ctx,
        p.id,
        SlideIn(
            type=SlideType.STAT_CARD,
            content={
                "title": f["opponent"]["name"],
                "rows": [
                    {"label": "matches", "value": g["matches"], "n": g["matches"]},
                    {"label": "goals_per_match", "value": g["goals_per_match"], "n": g["n"]},
                    {"label": "shooting_pct", "value": g["shooting_pct"], "n": g["n"]},
                ],
                "source": "scouting",
            },
        ),
    )
    for o in f.get("observations", []):
        await add_slide(
            ctx,
            p.id,
            SlideIn(type=SlideType.TEXT, content={"observation": o, "source": "scouting"}),
        )
        for ref in o.get("clips", []):
            if ref.get("video_id") and ref.get("t_ms") is not None:
                await add_slide(
                    ctx,
                    p.id,
                    SlideIn(
                        type=SlideType.CLIP,
                        content={
                            "video_id": ref["video_id"],
                            "in_ms": max(0, int(ref["t_ms"]) - 6000),
                            "out_ms": int(ref["t_ms"]) + 3000,
                        },
                    ),
                )
    return p


# ---- phone remote --------------------------------------------------------------------------


def _channel(pres_id: uuid.UUID, key: str) -> str:
    return f"presentation:{pres_id}:{key}"


async def pair(ctx: Ctx, pres_id: uuid.UUID) -> str:
    """A pairing key for the QR code; commands with this key reach this presenter only."""
    p = await _get(ctx, pres_id, write=True)
    key = secrets.token_urlsafe(18)
    await audit.record(
        ctx, "presentation.remote_paired", target_type="presentation", target_id=p.id
    )
    return key


async def command(ctx: Ctx, pres_id: uuid.UUID, key: str, payload: dict[str, Any]) -> None:
    await _get(ctx, pres_id, write=True)
    await ctx.require_events().publish(
        _channel(pres_id, key), {**payload, "sent_at": datetime.now(UTC).isoformat()}
    )


def channel(pres_id: uuid.UUID, key: str) -> str:
    return _channel(pres_id, key)


# ---- export ---------------------------------------------------------------------------------

EXPORT_FUNC = "handball_worker.export.run_presentation_export"


def slide_lines(slide: PresentationSlide, lang: str = "de-CH") -> list[str]:
    """Text of a text or stat slide for title cards and the PDF."""
    c = slide.content or {}
    if "observation" in c:
        return [observation_text(lang, c["observation"]), f"n = {c['observation'].get('n')}"]
    lines = [str(c.get("title") or "")]
    if c.get("body"):
        lines += str(c["body"]).splitlines()
    for row in c.get("rows") or []:
        lines.append(
            f"{row.get('label')}: {row.get('value')}"
            + (f" (n = {row['n']})" if row.get("n") is not None else "")
        )
    return [x for x in lines if x] or [""]


async def start_export(ctx: Ctx, pres_id: uuid.UUID) -> Presentation:
    p, slides, _ = await detail(ctx, pres_id)
    await get_team(ctx, p.team_id, Action.CLIP_WRITE)
    sources: dict[str, str] = {}
    payload_slides: list[dict[str, Any]] = []
    for s in slides:
        c = dict(s.content or {})
        if s.type == SlideType.CLIP and c.get("video_id"):
            v = await ctx.db.get(VideoAsset, uuid.UUID(str(c["video_id"])))
            if v is None or not v.proxy_key:
                continue
            sources[str(v.id)] = v.proxy_key
            payload_slides.append({"type": "clip", **c})
        elif s.type in (SlideType.TEXT, SlideType.STAT_CARD):
            payload_slides.append({"type": str(s.type), "lines": slide_lines(s)})
    if not payload_slides:
        raise ProblemError(422, "nothing-to-export", "Add clip or text slides first")
    analysis: dict[str, dict[str, Any]] = {}
    for vid in {
        str(sl["video_id"]) for sl in payload_slides if sl["type"] == "clip" and sl.get("spotlight")
    }:
        v = await ctx.db.get(VideoAsset, uuid.UUID(vid))
        cal = await ctx.db.scalar(
            select(CameraCalibration)
            .where(CameraCalibration.video_asset_id == uuid.UUID(vid))
            .order_by(CameraCalibration.created_at.desc())
            .limit(1)
        )
        if v is not None and cal is not None and (v.analysis or {}).get("chunk_ms"):
            analysis[vid] = {
                "chunks_prefix": media_prefix(v) + "analysis/",
                "chunk_ms": v.analysis["chunk_ms"],  # type: ignore[index]
                "homography": cal.homography,
                "image_size": cal.image_size,
            }
    job_id = f"pres-{p.id}-{int(datetime.now(UTC).timestamp())}"
    await ctx.enqueue(
        "default",
        EXPORT_FUNC,
        job_id,
        {
            "payload": {
                "presentation_id": str(p.id),
                "bucket_videos": ctx.settings.s3_bucket_videos,
                "bucket_artifacts": ctx.settings.s3_bucket_artifacts,
                "out_key": f"{p.organization_id}/presentations/{p.id}/export.mp4",
                "sources": sources,
                "slides": payload_slides,
                "analysis": analysis,
            }
        },
    )
    p.export_status, p.export_error = "queued", None
    await audit.record(
        ctx, "presentation.export_started", target_type="presentation", target_id=p.id
    )
    return p


async def export_done(
    ctx: Ctx, pres_id: uuid.UUID, status: str, key: str | None, error: str | None
) -> None:
    """Worker callback (system access)."""
    p = await ctx.db.get(Presentation, pres_id)
    if p is None:
        raise ProblemError(404, "not-found", "Presentation not found")
    p.export_status = status
    p.export_key = key
    p.export_error = error
    p.exported_at = datetime.now(UTC) if status == "ready" else p.exported_at


async def export_file(ctx: Ctx, pres_id: uuid.UUID) -> bytes:
    p = await _get(ctx, pres_id)
    if p.export_status != "ready" or not p.export_key:
        raise ProblemError(404, "not-found", "No export yet")
    data, _ = await ctx.storage.get(ctx.settings.s3_bucket_artifacts, p.export_key)
    return data


def _vtt_cue(vtt: str, t_s: float) -> tuple[int, int, int, int] | None:
    def secs(x: str) -> float:
        return float(sum(float(p) * 60**i for i, p in enumerate(reversed(x.strip().split(":")))))

    for block in vtt.replace("\r\n", "\n").split("\n\n"):
        lines = [x for x in block.strip().split("\n") if x]
        timing = next((x for x in lines if "-->" in x), None)
        if not timing or lines.index(timing) + 1 >= len(lines):
            continue
        a, b = timing.split("-->")
        target = lines[lines.index(timing) + 1]
        if "#xywh=" in target and secs(a) <= t_s < secs(b):
            x, y, w, h = (int(v) for v in target.split("#xywh=")[1].split(","))
            return x, y, w, h
    return None


async def still(ctx: Ctx, video_id: uuid.UUID, t_ms: int) -> bytes | None:
    """A still for the PDF, cut from the thumbnail sprite (no video decoding in the API)."""
    v = await ctx.db.get(VideoAsset, video_id)
    if v is None:
        return None
    try:
        vtt, _ = await ctx.storage.get(
            ctx.settings.s3_bucket_videos, media_prefix(v) + "thumbs.vtt"
        )
        sprite, _ = await ctx.storage.get(
            ctx.settings.s3_bucket_videos, media_prefix(v) + "thumbs.jpg"
        )
    except Exception:
        return None
    cue = _vtt_cue(vtt.decode(), t_ms / 1000)
    if cue is None:
        return None
    x, y, w, h = cue
    out = io.BytesIO()
    Image.open(io.BytesIO(sprite)).crop((x, y, x + w, y + h)).save(out, "JPEG", quality=85)
    return out.getvalue()


async def pdf(ctx: Ctx, pres_id: uuid.UUID, lang: str) -> bytes:
    """Stills plus notes per slide (4.1)."""
    p, slides, _ = await detail(ctx, pres_id)
    s = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=p.title,
    )
    story: list[Any] = [Paragraph(_esc(p.title), s["h1"]), Spacer(1, 4 * mm)]
    for i, sl in enumerate(slides, start=1):
        c = sl.content or {}
        story.append(Paragraph(_esc(f"{i}. {c.get('title') or ''}"), s["h2"]))
        if sl.type == SlideType.CLIP and c.get("video_id"):
            img = await still(ctx, uuid.UUID(str(c["video_id"])), int(c.get("in_ms", 0)))
            if img:
                story.append(RLImage(io.BytesIO(img), width=110 * mm, height=62 * mm))
            window = f"{c.get('in_ms', 0) / 1000:.1f} s - {c.get('out_ms', 0) / 1000:.1f} s"
            story.append(Paragraph(_esc(window), s["muted"]))
        elif sl.type in (SlideType.TEXT, SlideType.STAT_CARD):
            for line in slide_lines(sl, lang):
                story.append(Paragraph(_esc(line), s["base"]))
        elif sl.type == SlideType.IMAGE and c.get("image_key"):
            data, _ = await ctx.storage.get(ctx.settings.s3_bucket_artifacts, c["image_key"])
            story.append(
                RLImage(io.BytesIO(data), width=110 * mm, height=62 * mm, kind="proportional")
            )
        if c.get("notes"):
            story.append(Paragraph(_esc(str(c["notes"])), s["muted"]))
    doc.build(story)
    return buf.getvalue()
