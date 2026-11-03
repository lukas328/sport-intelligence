"""Statistics matrix (addendum 01, 5.4): rows (players, positions, plays, matches, phases ...),
metric columns, a filter. Every cell lists its events, so it leads to the clips (P2). Templates
store a layout per team; the matrix exports as CSV or Excel."""

from __future__ import annotations

import csv
import io
import uuid
from typing import Any

from openpyxl import Workbook
from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.models import MatrixTemplate
from handball_api.schemas.matrix import (
    MatrixCell,
    MatrixIn,
    MatrixOut,
    MatrixRow,
    TemplateIn,
)
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action
from handball_api.services.team_data import TeamData, load
from handball_metrics.query import GROUPS, METRICS, Filter, compute
from handball_metrics.query import select as select_rows

MAX_CLIPS = 50


def _label(data: TeamData, by: str, key: str) -> str:
    if by == "number":
        return f"#{key}"
    if by == "match":
        m = data.matches.get(key)
        return f"{m.date} {m.opponent or ''}".strip() if m else key
    if by == "play":
        return data.plays.get(key, key)
    return key


async def matrix(ctx: Ctx, team_id: uuid.UUID, spec: MatrixIn) -> MatrixOut:
    team = await get_team(ctx, team_id, Action.MATCH_READ)
    if spec.rows not in GROUPS:
        raise ProblemError(422, "validation", "Unknown row dimension")
    unknown = [m for m in spec.metrics if m not in METRICS]
    if unknown:
        raise ProblemError(422, "validation", f"Unknown metrics: {', '.join(unknown)}")
    data = await load(ctx, team)
    try:
        rows = select_rows(data.rows, Filter.from_dict(spec.filter))
    except (TypeError, ValueError) as exc:
        raise ProblemError(422, "validation", str(exc)) from exc
    key = GROUPS[spec.rows]
    buckets: dict[str, list[Any]] = {}
    for r in rows:
        k = key(r)
        if k is not None:
            buckets.setdefault(k, []).append(r)

    def cells(rs: list[Any]) -> dict[str, MatrixCell]:
        out = {}
        for metric in spec.metrics:
            v = compute(metric, rs)
            clips = [
                {"event_id": i, "match_id": data.by_id[i].match.id, "t_ms": data.event_ms[i]}
                for i in v.event_ids
                if data.event_ms.get(i) is not None
            ][:MAX_CLIPS]
            out[metric] = MatrixCell(
                value=v.value,
                numerator=v.numerator,
                denominator=v.denominator,
                events=v.events,
                event_ids=v.event_ids[:200],
                clips=clips,
            )
        return out

    result = [
        MatrixRow(key=k, label=_label(data, spec.rows, k), cells=cells(rs))
        for k, rs in buckets.items()
    ]
    first = spec.metrics[0]
    result.sort(key=lambda r: (r.cells[first].value is None, -(r.cells[first].value or 0), r.label))
    return MatrixOut(
        rows=result,
        totals=MatrixRow(key="total", label="", cells=cells(rows)),
        metrics=spec.metrics,
        definitions={m: METRICS[m].label for m in spec.metrics},
        by=spec.rows,
    )


def _fmt(v: float | None, metric: str) -> float | str:
    if v is None:
        return ""
    return round(v * 100, 1) if METRICS[metric].kind == "ratio" else v


def to_table(out: MatrixOut) -> list[list[Any]]:
    head: list[Any] = [out.by] + [
        f"{m} (%)" if METRICS[m].kind == "ratio" else m for m in out.metrics
    ]
    body: list[list[Any]] = [
        [r.label, *(_fmt(r.cells[m].value, m) for m in out.metrics)] for r in out.rows
    ]
    total: list[list[Any]] = [["total", *(_fmt(out.totals.cells[m].value, m) for m in out.metrics)]]
    return [head, *body, *total]


def to_csv(out: MatrixOut) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    for row in to_table(out):
        w.writerow([_safe(c) for c in row])
    return ("﻿" + buf.getvalue()).encode()


def to_xlsx(out: MatrixOut) -> bytes:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Matrix"
    for row in to_table(out):
        ws.append([_safe(c) for c in row])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _safe(value: Any) -> Any:
    """No spreadsheet formulas from data (CSV injection): = + - @ at the start get a quote."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


# ---- templates ----------------------------------------------------------------------------------


async def templates(ctx: Ctx, team_id: uuid.UUID) -> list[MatrixTemplate]:
    await get_team(ctx, team_id, Action.MATCH_READ)
    return list(
        (
            await ctx.db.scalars(
                select(MatrixTemplate)
                .where(MatrixTemplate.team_id == team_id)
                .order_by(MatrixTemplate.name)
            )
        ).all()
    )


async def save_template(ctx: Ctx, team_id: uuid.UUID, data: TemplateIn) -> MatrixTemplate:
    team = await get_team(ctx, team_id, Action.PLAYLIST_WRITE)
    exists = await ctx.db.scalar(
        select(MatrixTemplate.id).where(
            MatrixTemplate.team_id == team.id, MatrixTemplate.name == data.name
        )
    )
    if exists:
        raise ProblemError(409, "duplicate-name", "A template with this name exists")
    t = MatrixTemplate(
        organization_id=team.organization_id,
        team_id=team.id,
        name=data.name,
        config=data.config.model_dump(),
        created_by_id=ctx.user_id,
    )
    ctx.db.add(t)
    await ctx.db.flush()
    await audit.record(
        ctx, "matrix_template.created", target_type="matrix_template", target_id=t.id
    )
    return t


async def delete_template(ctx: Ctx, template_id: uuid.UUID) -> None:
    t = await ctx.db.get(MatrixTemplate, template_id)
    if t is None:
        raise ProblemError(404, "not-found", "Template not found")
    await get_team(ctx, t.team_id, Action.PLAYLIST_WRITE)
    await ctx.db.delete(t)
