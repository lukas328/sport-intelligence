"""Automatic events from the analysis (addendum 01, A3, principle P1).

The pipeline's event baseline (throw-offs, goals inferred from throw-offs, possession phases, side
changes) is stored with source "heuristic" and its confidence. A re-analysis replaces the previous
automatic rows. Events a person entered (tagging, import, correction) always win: an automatic
goal close to a manual one is dropped. The opening throw-offs set the match clock if nobody did.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select

from handball_api.models import Event, Match, Possession
from handball_api.services.context import Ctx
from handball_api.services.events import clock_from_video

SOURCE = "heuristic"
MIN_CONFIDENCE = 0.5
DEDUPE_MS = 5000


def _side(team: object) -> str | None:
    return {"home": "own", "away": "opponent"}.get(str(team))


async def apply(ctx: Ctx, match: Match, payload: dict[str, Any] | None) -> dict[str, int]:
    if not payload:
        return {"events": 0, "possessions": 0}
    await ctx.db.execute(delete(Event).where(Event.match_id == match.id, Event.source == SOURCE))
    await ctx.db.execute(
        delete(Possession).where(Possession.match_id == match.id, Possession.source == SOURCE)
    )
    found = list(payload.get("events") or [])

    # match clock from the opening throw-offs (first one, first one after a side change)
    k = dict(match.kickoff_ms or {})
    side_changes = sorted(int(e["t_ms"]) for e in found if e.get("type") == "side_change")
    throw_offs = sorted(int(e["t_ms"]) for e in found if e.get("type") == "throw_off")
    if "1" not in k and throw_offs:
        k["1"] = throw_offs[0]
    if "2" not in k and side_changes:
        after = [t for t in throw_offs if t >= side_changes[0] - 2000]
        if after:
            k["2"] = after[0]
    if k != (match.kickoff_ms or {}):
        match.kickoff_ms = k

    manual_goals = [
        (e.side, e.t_ms)
        for e in (
            await ctx.db.scalars(
                select(Event).where(
                    Event.match_id == match.id,
                    Event.type == "shot",
                    Event.outcome == "goal",
                    Event.t_ms.is_not(None),
                )
            )
        ).all()
    ]
    created = 0
    for e in found:
        kind, side, t_ms = e.get("type"), _side(e.get("team")), int(e["t_ms"])
        conf = float(e.get("confidence", 0))
        if kind not in ("goal", "throw_off") or side is None or conf < MIN_CONFIDENCE:
            continue
        if kind == "goal" and any(
            s == side and t is not None and abs(t - t_ms) <= DEDUPE_MS for s, t in manual_goals
        ):
            continue
        derived = clock_from_video(match, t_ms)
        period, clock = derived if derived else (1, None)
        attrs = {k2: v for k2, v in e.items() if k2 not in ("t_ms", "type", "team", "confidence")}
        ctx.db.add(
            Event(
                organization_id=match.organization_id,
                match_id=match.id,
                type="shot" if kind == "goal" else "throw_off",
                side=side,
                outcome="goal" if kind == "goal" else None,
                t_ms=t_ms,
                period=period,
                clock_s=clock,
                source=SOURCE,
                confidence=conf,
                attributes=attrs,
            )
        )
        created += 1
    possessions = 0
    for p in payload.get("possessions") or []:
        side = _side(p.get("team"))
        if side is None:
            continue
        ctx.db.add(
            Possession(
                organization_id=match.organization_id,
                match_id=match.id,
                side=side,
                start_ms=int(p["start_ms"]),
                end_ms=int(p["end_ms"]),
                outcome=p.get("outcome"),
                confidence=float(p.get("confidence", 0.5)),
                source=SOURCE,
            )
        )
        possessions += 1
    await ctx.db.flush()
    return {"events": created, "possessions": possessions}
