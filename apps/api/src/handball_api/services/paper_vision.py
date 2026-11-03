"""Photographed paper match reports (addendum 01, 5.9): upload, extraction, checks, review, import.

The model's reading is never imported directly: the user reviews it next to the photo (optional
feature, handwriting is uncertain). Checks flag sums against totals, the final score against the
score progression and fields the model marked as uncertain. Confirmed sheets go through the existing
paper report import (BRIEF 15) and appear in the season with source "paper_report".
"""

from __future__ import annotations

import itertools
import json
import uuid
from typing import Any

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.core.paper_vision import PaperExtractionError, PaperExtractor
from handball_api.models import PaperReportUpload
from handball_api.models.enums import UploadStatus
from handball_api.services import audit, paper_reports
from handball_api.services.context import Ctx
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action

MAX_PHOTO = 10 * 1024 * 1024
TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
BLOCKING = {"missing", "unreadable"}


def to_report(x: dict[str, Any]) -> dict[str, Any]:
    """The extraction in the paper report schema (docs/schemas/paper-report.schema.json)."""
    out: dict[str, Any] = {
        "schema": "handball-paper-report/1",
        "date": x.get("date"),
        "opponent": x.get("opponent"),
        "home": bool(x.get("home", True)),
        "score": x.get("score"),
        "players": [_player(p) for p in x.get("players") or []],
        "goalkeepers": [
            {k: v for k, v in g.items() if v is not None} for g in x.get("goalkeepers") or []
        ],
        "score_progression": x.get("score_progression") or [],
    }
    for key in ("kickoff", "competition", "halftime"):
        if x.get(key):
            out[key] = x[key]
    return out


def _player(p: dict[str, Any]) -> dict[str, Any]:
    """The sheet's total goals include 7 m goals; the report schema counts them apart."""
    out = {k: v for k, v in p.items() if v is not None and v != ""}
    seven = int(out.get("seven_m_goals") or 0)
    out["goals"] = max(0, int(out.get("goals") or 0) - seven)
    return out


def validate(x: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    def issue(field: str, code: str, **detail: Any) -> None:
        issues.append({"field": field, "code": code, "detail": detail})

    if not x.get("readable", True):
        issue("photo", "unreadable")
    for field in ("date", "opponent", "score"):
        if not x.get(field):
            issue(field, "missing")
    players = x.get("players") or []
    numbers = [p.get("number") for p in players]
    for n in sorted({n for n in numbers if numbers.count(n) > 1 and n is not None}):
        issue("players", "duplicate_number", number=n)
    goals = sum(int(p.get("goals") or 0) for p in players)
    score = x.get("score") or {}
    if score and players and goals != score.get("own"):
        issue("score.own", "goals_vs_score", players=goals, score=score.get("own"))
    total = x.get("team_goals_total")
    if total is not None and total != goals:
        issue("team_goals_total", "goals_vs_total", players=goals, total=total)
    for i, p in enumerate(players):
        if int(p.get("seven_m_goals") or 0) > int(p.get("goals") or 0):
            issue(f"players[{i}].seven_m_goals", "seven_m_above_goals", number=p.get("number"))
    prog = sorted(x.get("score_progression") or [], key=lambda s: s.get("minute") or 0)
    for a, b in itertools.pairwise(prog):
        if b["own"] < a["own"] or b["opponent"] < a["opponent"]:
            issue("score_progression", "progression_decreases", minute=b["minute"])
            break
    if prog and score:
        last = prog[-1]
        if (last["own"], last["opponent"]) != (score.get("own"), score.get("opponent")) and (
            last["own"] > score.get("own", 0) or last["opponent"] > score.get("opponent", 0)
        ):
            issue("score", "score_vs_progression", progression=[last["own"], last["opponent"]])
    half = x.get("halftime")
    if (
        half
        and score
        and (half["own"] > score.get("own", 0) or half["opponent"] > score.get("opponent", 0))
    ):
        issue("halftime", "halftime_above_final")
    for path in x.get("uncertain") or []:
        issue(str(path)[:80], "uncertain")
    return issues


async def upload(
    ctx: Ctx,
    extractor: PaperExtractor | None,
    team_id: uuid.UUID,
    data: bytes,
    media_type: str,
) -> PaperReportUpload:
    team = await get_team(ctx, team_id, Action.MATCH_WRITE)
    if extractor is None:
        raise ProblemError(503, "vision-unavailable", "Photo reading is not set up")
    if media_type not in TYPES:
        raise ProblemError(415, "unsupported-image", "JPEG, PNG or WebP only")
    if len(data) > MAX_PHOTO:
        raise ProblemError(413, "file-too-large", "Photos up to 10 MB")
    key = f"paper/{team.organization_id}/{uuid.uuid4()}.{TYPES[media_type]}"
    await ctx.storage.put(ctx.settings.s3_bucket_artifacts, key, data, media_type)
    up = PaperReportUpload(
        organization_id=team.organization_id,
        team_id=team.id,
        photo_key=key,
        status=UploadStatus.PENDING,
    )
    ctx.db.add(up)
    await ctx.db.flush()
    try:
        extraction = await extractor.extract(data, media_type)
    except PaperExtractionError as exc:
        up.status = UploadStatus.FAILED
        up.errors = [
            {"field": "photo", "code": "extraction_failed", "detail": {"reason": str(exc)}}
        ]
        return up
    up.extraction = extraction
    up.errors = validate(extraction)
    up.status = UploadStatus.EXTRACTED
    await audit.record(ctx, "paper.extracted", target_type="paper_upload", target_id=up.id)
    return up


async def _upload(ctx: Ctx, upload_id: uuid.UUID) -> PaperReportUpload:
    up = await ctx.db.get(PaperReportUpload, upload_id)
    if up is None:
        raise ProblemError(404, "not-found", "Upload not found")
    await get_team(ctx, up.team_id, Action.MATCH_WRITE)
    return up


async def get(ctx: Ctx, upload_id: uuid.UUID) -> PaperReportUpload:
    return await _upload(ctx, upload_id)


async def listing(ctx: Ctx, team_id: uuid.UUID) -> list[PaperReportUpload]:
    await get_team(ctx, team_id, Action.MATCH_WRITE)
    return list(
        (
            await ctx.db.scalars(
                select(PaperReportUpload)
                .where(PaperReportUpload.team_id == team_id)
                .order_by(PaperReportUpload.created_at.desc())
                .limit(30)
            )
        ).all()
    )


async def photo(ctx: Ctx, upload_id: uuid.UUID) -> tuple[bytes, str]:
    up = await _upload(ctx, upload_id)
    return await ctx.storage.get(ctx.settings.s3_bucket_artifacts, up.photo_key)


async def correct(ctx: Ctx, upload_id: uuid.UUID, extraction: dict[str, Any]) -> PaperReportUpload:
    """The user's corrections; the checks run again."""
    up = await _upload(ctx, upload_id)
    if up.status == UploadStatus.CONFIRMED:
        raise ProblemError(409, "already-confirmed", "This sheet was already imported")
    up.extraction = extraction
    up.errors = validate(extraction)
    up.status = UploadStatus.EXTRACTED
    return up


async def confirm(ctx: Ctx, upload_id: uuid.UUID, accept_warnings: bool) -> PaperReportUpload:
    up = await _upload(ctx, upload_id)
    if up.status == UploadStatus.CONFIRMED:
        raise ProblemError(409, "already-confirmed", "This sheet was already imported")
    if up.extraction is None:
        raise ProblemError(409, "not-extracted", "Nothing to import")
    issues = validate(up.extraction)
    if any(i["code"] in BLOCKING for i in issues):
        raise ProblemError(422, "paper-incomplete", "Date, opponent and score are needed")
    if issues and not accept_warnings:
        raise ProblemError(422, "paper-warnings", "Check the marked fields or accept them")
    result = await paper_reports.import_report(
        ctx, up.team_id, json.dumps(to_report(up.extraction)).encode()
    )
    up.match_id = uuid.UUID(str(result["match_id"]))
    up.status = UploadStatus.CONFIRMED
    up.confirmed_by_id = ctx.user_id
    up.errors = issues
    await audit.record(ctx, "paper.confirmed", target_type="paper_upload", target_id=up.id)
    return up
