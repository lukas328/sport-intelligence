"""The budget of Prüfen (second round A6, A7): few questions, the useful ones, and an honest word
when the analysis found too little to ask about.

- **Budget**: at most BUDGET questions per match in the main round, by value: the court of each
  part while it is not confirmed, the throw-off (at most KICKOFFS_MAX), then the goal moments
  (graphics._goal_questions: one per moment, the strongest first). Everything else waits behind
  «Mehr prüfen» (`more_checks`) and is never counted in the bell, the start or the mail. A round
  is one analysis: what was answered or left since its end uses up the budget, so leaving a
  question does not pull the next one in.
- **The result**: with the final score known (handball.ch, a paper report, typed in) the analysis
  asks about at most PER_MISSING_GOAL x the goals of the video that have no place in it yet
  (`goals_missing`: the goals a stretch of video of that length should hold, less the goals
  already placed: confirmed, read from the scoreboard, report goals timed by the throw-off); with
  all of them placed, no goal is asked.
- **Weiss nicht**: a goal moment left goes to status "skipped", the court or a throw-off into
  `report_extra.checks_skipped`; skipped questions do not come back in the round and wait behind
  «Mehr prüfen». `skip_all` («Für dieses Spiel fertig») leaves every open question at once, so
  the bell clears.
- **Found little** (`little_found`): the court not recognised and not set by a person, the
  detector saw almost nobody, or almost no play in the video. Then no goal and no throw-off is
  asked (the court question stays: setting the corners is what helps), and `notice` says why and
  what helps instead. A failed analysis gives its notice too (A3).
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.models import Event, GoalCandidate, Match, VideoAsset
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.policies import Action

BUDGET = 10  # questions per match in the main round
KICKOFFS_MAX = 2
PER_MISSING_GOAL = 1.5  # goal questions per goal of the result without a place in the video
SKIPPED = "checks_skipped"  # report_extra: keys of the court and throw-off questions left
OPEN = ("open", "skipped")  # a skipped candidate is still unanswered
# almost no play: less than this many seconds, or this share of the video
# a handball match has at least a dozen people on court: fewer tracks than this is «almost nobody»
LITTLE_MIN_TRACKS = 6
LITTLE_PLAY_S = 30.0
LITTLE_PLAY_SHARE = 0.1
LITTLE_MIN_VIDEO_S = 60.0  # a shorter clip is not judged by its play time
CALIBRATION_REASONS = ("camera_motion", "no_floor", "flat_view", "few_people", "court")
NO_PLAY_MS_MAX = 200  # stretches without play kept in the analysis signals


@dataclass
class Rounds:
    """The questions of a match: the main round (counted), the rest (offered), and why there
    is little to ask, if so."""

    checks: list[dict[str, Any]] = field(default_factory=list)
    more: list[dict[str, Any]] = field(default_factory=list)
    notice: dict[str, Any] | None = None
    goals_missing: int | None = None
    skipped: int = 0


def check_key(c: dict[str, Any]) -> str:
    """The key of a question as web and API name it: field:<video>, kickoff:<half>, <candidate>."""
    if c["kind"] == "field":
        return f"field:{c['id']}"
    if c["kind"] == "kickoff":
        return f"kickoff:{c['frame_ref']}"
    return str(c["id"])


def skipped_keys(match: Match) -> set[str]:
    raw = (match.report_extra or {}).get(SKIPPED)
    return {str(k) for k in raw} if isinstance(raw, list) else set()


def _add_skipped(match: Match, keys: set[str]) -> None:
    if not keys:
        return
    extra = dict(match.report_extra or {})
    extra[SKIPPED] = sorted(skipped_keys(match) | keys)
    match.report_extra = extra


def forget_skipped(match: Match, keys: set[str]) -> None:
    """A new analysis of a part asks its court again."""
    before = skipped_keys(match)
    if not before & keys:
        return
    extra = dict(match.report_extra or {})
    extra[SKIPPED] = sorted(before - keys)
    match.report_extra = extra


def signals(r: dict[str, Any]) -> dict[str, Any]:
    """What the worker said about how much it found, kept in the analysis JSON: the play time
    (from the goal candidates' no-play mask), and whether the detector saw almost nobody."""
    found = r.get("goal_candidates")
    out: dict[str, Any] = {"detector_few_people": bool(r.get("detector_few_people"))}
    if isinstance(found, dict):
        for k in ("duration_s", "play_s"):
            v = found.get(k)
            if isinstance(v, int | float) and not isinstance(v, bool):
                out[k] = float(v)
        stretches = found.get("no_play_ms")
        if isinstance(stretches, list):
            out["no_play_ms"] = stretches[:NO_PLAY_MS_MAX]
    return out


def little_found(asset: VideoAsset | None, court_ok: bool | None) -> str | None:
    """Why the analysis of this file found too little to ask about, or None: the court not
    recognised (and not set by a person: then camera_motion, no_floor, flat_view, few_people or
    court), the detector saw almost nobody and nothing was found (few_people), almost no play
    (no_play)."""
    if asset is None:
        return None
    a = asset.analysis or {}
    if a.get("needs_calibration") and court_ok is not True:
        info = a.get("calibration_info")
        reason = str(info.get("reason") or "court") if isinstance(info, dict) else "court"
        return reason if reason in CALIBRATION_REASONS else "court"
    sig = a.get("signals")
    if not isinstance(sig, dict):
        return None
    # the learned detector can miss people while the fallback still follows the players and finds
    # moments (synthetic or unusual footage): «saw almost nobody» only counts when the analysis
    # also followed almost nobody and found no goal moment
    found = a.get("goal_candidates")
    moments = found.get("goal_candidates") if isinstance(found, dict) else None
    stats = a.get("stats")
    tracks = stats.get("tracks") if isinstance(stats, dict) else None
    followed = isinstance(tracks, int) and tracks >= LITTLE_MIN_TRACKS
    if (
        sig.get("detector_few_people")
        and not followed
        and not (isinstance(moments, int) and moments > 0)
    ):
        return "few_people"
    play, length = sig.get("play_s"), sig.get("duration_s")
    if (
        isinstance(play, int | float)
        and isinstance(length, int | float)
        and length >= LITTLE_MIN_VIDEO_S
        and play < max(LITTLE_PLAY_S, LITTLE_PLAY_SHARE * length)
    ):
        return "no_play"
    return None


def goals_missing(match: Match, goals: list[Event], length_ms: int | None) -> int | None:
    """The goals of the final score that the video should hold but that have no place in it
    yet; None without a final score. A video shorter than the match holds its share of the goals
    (a 10-minute clip of a 60-minute match about a sixth)."""
    if match.score_own is None or match.score_opponent is None:
        return None
    total = int(match.score_own) + int(match.score_opponent)
    full = match.period_s * match.periods * 1000
    expected = total
    if length_ms and full and length_ms < full:
        expected = math.ceil(total * length_ms / full)

    def placed(e: Event) -> bool:
        v = (e.attributes or {}).get("video")
        t = v.get("t_ms") if isinstance(v, dict) and v.get("t_ms") is not None else e.t_ms
        return t is not None and t >= 0 and (length_ms is None or t <= length_ms)

    # a goal estimated from a throw-off is a guess, not a place (auto_events.SOURCE)
    return max(0, expected - sum(1 for e in goals if e.source != "heuristic" and placed(e)))


def goal_limit(missing: int | None, left: int) -> int:
    """How many goal moments the main round may ask."""
    left = max(0, left)
    if missing is None:
        return left
    return min(left, math.ceil(PER_MISSING_GOAL * missing))


def failure_notice(code: str, asset: VideoAsset, limit_s: int | None) -> dict[str, Any]:
    return {
        "reason": code,
        "failed": True,
        "video_id": asset.id,
        "duration_s": asset.duration_s,
        "limit_s": limit_s,
    }


def little_notice(reason: str, asset: VideoAsset) -> dict[str, Any]:
    return {
        "reason": reason,
        "failed": False,
        "video_id": asset.id,
        "duration_s": asset.duration_s,
        "limit_s": None,
    }


# ---- leaving questions ----------------------------------------------------------------------


async def skip(
    ctx: Ctx, match_id: uuid.UUID, kind: str, item_id: uuid.UUID | None, period: int | None
) -> None:
    """«Weiss nicht»: the question waits behind «Mehr prüfen» and is not asked again in this
    round. A goal moment is marked on its candidate, the court and the throw-off on the match."""
    from handball_api.services.matches import get_match

    match = await get_match(ctx, match_id, Action.EVENT_WRITE)
    if kind == "goal":
        if item_id is None:
            raise ProblemError(422, "invalid-check", "A goal question needs its id")
        c = await ctx.db.get(GoalCandidate, item_id)
        if c is None or c.match_id != match.id:
            raise ProblemError(404, "not-found", "Candidate not found")
        if c.status == "open":
            c.status = "skipped"
            c.reviewed_by_id, c.reviewed_at = ctx.user_id, datetime.now(UTC)
        key = str(c.id)
    elif kind == "field":
        if item_id is None:
            raise ProblemError(422, "invalid-check", "A court question needs its video")
        key = f"field:{item_id}"
        _add_skipped(match, {key})
    elif kind == "kickoff":
        if period not in (1, 2):
            raise ProblemError(422, "invalid-check", "A throw-off question needs its half")
        key = f"kickoff:{period}"
        _add_skipped(match, {key})
    else:
        raise ProblemError(422, "invalid-check", "kind is goal, field or kickoff")
    await ctx.db.flush()
    await audit.record(
        ctx, "match.check_skipped", target_type="match", target_id=match.id, data={"key": key}
    )


async def skip_all(ctx: Ctx, match_id: uuid.UUID) -> dict[str, int]:
    """«Für dieses Spiel fertig»: every open question of the match is left at once (the goal
    moments of every rank too, so no new one moves up); they stay behind «Mehr prüfen». The
    bell then has nothing to count and says «Alles geprüft»."""
    from handball_api.services.graphics import open_checks
    from handball_api.services.matches import get_match

    match = await get_match(ctx, match_id, Action.EVENT_WRITE)
    asked = await open_checks(ctx, match)
    keys = {check_key(c) for c in asked if c["kind"] in ("field", "kickoff")}
    _add_skipped(match, keys)
    now = datetime.now(UTC)
    rows = (
        await ctx.db.scalars(
            select(GoalCandidate).where(
                GoalCandidate.match_id == match.id,
                GoalCandidate.kind == "goal",
                GoalCandidate.status == "open",
            )
        )
    ).all()
    for c in rows:
        c.status = "skipped"
        c.reviewed_by_id, c.reviewed_at = ctx.user_id, now
    await ctx.db.flush()
    await _settle_notes(ctx, match)
    await audit.record(
        ctx,
        "match.checks_skipped",
        target_type="match",
        target_id=match.id,
        data={"questions": len(asked), "moments": len(rows)},
    )
    return {"skipped": len(asked), "moments": len(rows)}


async def _settle_notes(ctx: Ctx, match: Match) -> None:
    """The notes «n Fragen an dich» of this match: counted afresh at once (none left: read)."""
    from handball_api.models import Notification
    from handball_api.services.training import QUESTIONS, _questions_now

    notes = (
        await ctx.db.scalars(
            select(Notification).where(
                Notification.kind == QUESTIONS,
                Notification.params["match_id"].astext == str(match.id),
            )
        )
    ).all()
    if notes:
        await _questions_now(ctx, list(notes))
