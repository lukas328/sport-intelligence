"""Support, help and onboarding (addendum 01, 4.11).

- failed analyses: an understandable reason, what to do next, and the match is credited
- feedback with automatic context (page, match, browser, optional screenshot) to the support inbox
- onboarding checklist from the club's real data, demo match to try things out
- onboarding e-mail series on day 0, 1, 3, 7 and 14 with one-click unsubscribe
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import random
import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select

from handball_api.core.email import Email, try_send
from handball_api.core.errors import ProblemError
from handball_api.integrations.support import CrispChat, NoSupportChat
from handball_api.models import (
    Event,
    Match,
    Opponent,
    Organization,
    OrgMembership,
    Presentation,
    RosterEntry,
    Team,
    User,
    VideoAsset,
)
from handball_api.models.enums import VideoRole
from handball_api.schemas.matches import MatchCreate
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.mail_templates import render
from handball_api.services.matches import DEMO_SOURCE, create_match
from handball_api.services.orgs import current_seasons, get_team
from handball_api.services.policies import Action

SERIES_DAYS = (0, 1, 3, 7, 14)
SERIES_LINKS = {0: "/app", 1: "/hilfe/aufnahme", 3: "/hilfe/videositzung", 7: "/app", 14: "/app"}


# ---- failed analyses ------------------------------------------------------------------------


def failure_code(error: str | None) -> str:
    """Stable code for an analysis error; the UI explains it and suggests the next step."""
    e = (error or "").lower()
    # the watchdog ended a job whose worker went silent twice (services/progress.STALLED_ERROR):
    # a lost worker, not a video too long; starting again can help
    if e.startswith("stalled"):
        return "stalled"
    if "calibration" in e:
        return "calibration"
    if "no video stream" in e or "unknown duration" in e or "probe" in e or "decode" in e:
        return "unreadable"
    if "too short" in e:
        return "too_short"
    # longer than the environment's limit (HB_ANALYSIS_MAX_MINUTES, e.g. the GPU test phase)
    if "too long for this environment" in e:
        return "too_long"
    if "timeout" in e or "timed out" in e:
        return "timeout"
    return "generic"


# ---- feedback --------------------------------------------------------------------------------

MAX_SCREENSHOT = 2 * 1024 * 1024


async def feedback(
    ctx: Ctx, user: User, message: str, context: dict[str, Any], screenshot: str | None
) -> None:
    attachments: tuple[tuple[str, str, bytes], ...] = ()
    if screenshot:
        try:
            header, data = screenshot.split(",", 1)
            raw = base64.b64decode(data, validate=True)
        except (ValueError, base64.binascii.Error) as exc:  # type: ignore[attr-defined]
            raise ProblemError(422, "validation", "Invalid screenshot") from exc
        if not header.startswith("data:image/png") or len(raw) > MAX_SCREENSHOT:
            raise ProblemError(422, "validation", "Screenshot must be a PNG up to 2 MB")
        attachments = (("screenshot.png", "image/png", raw),)
    lines = [f"{k}: {v}" for k, v in sorted(context.items()) if v not in (None, "")]
    # the mail is the whole action here: report the outage instead of a bare 500
    sent = await try_send(
        ctx.email,
        Email(
            to=ctx.settings.support_email,
            subject=f"Feedback: {message[:60]}",
            text=f"{message}\n\n---\nVon: {user.name} <{user.email}>\n" + "\n".join(lines),
            attachments=attachments,
        ),
        "feedback",
        user_id=str(user.id),
    )
    if not sent:
        raise ProblemError(
            503, "email-unavailable", "The e-mail could not be sent; please try again later"
        )
    # without mail delivery (console backend) the mail went nowhere: keep the message in the audit
    # log so the support can read it there (L2); with mail it is in the support's inbox
    kept = {} if ctx.settings.mail_delivers else {"message": message[:2000]}
    await audit.record(ctx, "support.feedback", data={"page": context.get("page"), **kept})


def chat_config(ctx: Ctx, user: User | None, locale: str) -> dict[str, Any] | None:
    adapter = (
        CrispChat(ctx.settings.crisp_website_id)
        if ctx.settings.crisp_website_id
        else NoSupportChat()
    )
    pseudonym = (
        hmac.new(
            ctx.settings.secret_key.get_secret_value().encode(),
            str(user.id).encode(),
            hashlib.sha256,
        ).hexdigest()[:32]
        if user
        else None
    )
    w = adapter.widget(locale, pseudonym)
    return {"provider": w.provider, **w.config} if w else None


# ---- onboarding checklist and demo match -------------------------------------------------------


async def checklist(ctx: Ctx, org: Organization) -> list[dict[str, Any]]:
    async def count(q: Any) -> int:
        return int(await ctx.db.scalar(q) or 0)

    teams = await count(select(func.count(Team.id)))
    players = await count(select(func.count(RosterEntry.id)))
    members = await count(select(func.count(OrgMembership.id)))
    videos = await count(select(func.count(VideoAsset.id)).where(VideoAsset.role == VideoRole.MAIN))
    analysed = await count(
        select(func.count(VideoAsset.id)).where(
            VideoAsset.analysis.is_not(None), VideoAsset.role == VideoRole.MAIN
        )
    )
    presentations = await count(select(func.count(Presentation.id)))
    demo = await count(select(func.count(Match.id)).where(Match.source == DEMO_SOURCE))
    team_id = await ctx.db.scalar(select(Team.id).order_by(Team.created_at).limit(1))
    return [
        {"key": "team", "done": teams > 0, "link": f"/app/{org.id}"},
        {
            "key": "roster",
            "done": players >= 5,
            "link": f"/app/{org.id}/teams/{team_id}" if team_id else None,
        },
        {"key": "invite", "done": members > 1, "link": f"/app/{org.id}/settings"},
        {"key": "demo", "done": demo > 0, "link": None},
        {
            "key": "upload",
            "done": videos > 0,
            "link": f"/app/{org.id}/teams/{team_id}/matches" if team_id else None,
        },
        {"key": "analysis", "done": analysed > 0, "link": None},
        {
            "key": "presentation",
            "done": presentations > 0,
            "link": f"/app/{org.id}/teams/{team_id}/presentations" if team_id else None,
        },
    ]


# The example match: a plausible 27:24 with three clear patterns, so the three things show what
# they are (app review R20): 9 of 24 goals against over the right wing, 4 fast breaks against,
# 9 of 27 own goals from the circle. Zone -> a shot spot of that zone (attacked goal at x = 40).
DEMO_SPOT = {
    "wing_left": (38.6, 18.4),
    "wing_right": (38.6, 1.6),
    "circle_left": (34.2, 13.0),
    "circle_centre": (33.6, 10.2),
    "circle_right": (34.2, 7.0),
    "back_left": (30.0, 15.5),
    "back_centre": (29.5, 10.0),
    "back_right": (30.0, 4.5),
    "fast_break": (34.0, 10.0),
    "penalty": (33.0, 10.0),
}
# goals per zone and side, then the shots that did not go in (saved, missed, blocked)
DEMO_GOALS = {
    "own": {
        "circle_centre": 4,
        "circle_left": 3,
        "circle_right": 2,
        "back_left": 4,
        "back_centre": 3,
        "back_right": 3,
        "wing_left": 2,
        "wing_right": 2,
        "penalty": 3,
        "fast_break": 1,
    },
    "opponent": {
        "wing_right": 9,
        "fast_break": 4,
        "back_left": 3,
        "back_centre": 3,
        "circle_centre": 2,
        "wing_left": 1,
        "penalty": 2,
    },
}
DEMO_OTHER = {
    "own": {"save": 12, "miss": 5, "blocked": 2, "penalty_save": 1},
    "opponent": {"save": 13, "miss": 4, "blocked": 1, "penalty_save": 1},
}
DEMO_TURNOVERS = {"own": 9, "opponent": 11}
DEMO_SUSPENSIONS = {"own": 2, "opponent": 3}
# The example's opponent: an invented club of the demo story (the website's demo match). Until
# 18.11.2026 it was «Demo HC Beispiel» (migration 0051 renamed it). An example match is told by
# its `source` (DEMO_SOURCE), never by this name.
DEMO_OPPONENT = "TSV Nachtwind"
# The example names nobody of the team (A4): our players are shirt numbers only, invented ones,
# never linked to the roster; our goalkeeper wears the 12, theirs the 1
DEMO_NUMBERS = [2, 4, 5, 8, 13, 15, 17, 19, 22, 24]
DEMO_KEEPER = 12
DEMO_KEEPER_OPPONENT = 1


def demo_kickoff(season_start: date, today: date) -> datetime:
    """The example's date, far from any real fixture (A4): the first day of the season, in the
    summer break before the championship starts (18:00 Swiss time); a season that has not
    started yet takes the same day one year earlier."""
    day = (
        season_start if season_start <= today else season_start.replace(year=season_start.year - 1)
    )
    return datetime.combine(day, time(16, 0), tzinfo=UTC)


def demo_events(
    period_s: int, numbers: list[int] | None = None, keeper: int = DEMO_KEEPER
) -> list[dict[str, Any]]:
    """The example match's events in match order (fixed seed): our field players by the shirt
    numbers `numbers` (no player of the roster), our goalkeeper's saves credited to the number
    `keeper`."""
    field = numbers if numbers is not None else DEMO_NUMBERS
    rng = random.Random(7)  # noqa: S311 (example data, not security relevant)
    shots: list[dict[str, Any]] = []
    for side in ("own", "opponent"):
        for zone, n in DEMO_GOALS[side].items():
            shots += [{"side": side, "outcome": "goal", "zone": zone} for _ in range(n)]
        for outcome, n in DEMO_OTHER[side].items():
            for _ in range(n):
                if outcome == "penalty_save":
                    shots.append({"side": side, "outcome": "save", "zone": "penalty"})
                else:
                    zone = rng.choice(["back_left", "back_centre", "back_right", "wing_left"])
                    shots.append({"side": side, "outcome": outcome, "zone": zone})
    rest: list[dict[str, Any]] = [
        {"side": side, "type": "turnover"} for side, n in DEMO_TURNOVERS.items() for _ in range(n)
    ] + [
        {"side": side, "type": "suspension_2min"}
        for side, n in DEMO_SUSPENSIONS.items()
        for _ in range(n)
    ]
    items = shots + rest
    rng.shuffle(items)
    length = 2 * period_s
    out: list[dict[str, Any]] = []
    opp_numbers = [3, 5, 7, 9, 11, 14, 18, 21, 23, 27]
    for k, item in enumerate(items):
        clock = round((k + 0.5) * length / len(items) + rng.uniform(-8, 8), 1)
        e: dict[str, Any] = {
            "side": item["side"],
            "period": 1 if clock < period_s else 2,
            "clock_s": clock,
        }
        own = item["side"] == "own"
        shooter = rng.choice(field) if own and field else None
        if "type" in item:
            e["type"] = item["type"]
            if item["type"] == "turnover":
                e["turnover_type"] = rng.choice(["bad_pass", "steps", "offensive_foul"])
        else:
            zone = item["zone"]
            x, y = DEMO_SPOT[zone]
            e.update(
                type="shot",
                outcome=item["outcome"],
                x=round(x + rng.uniform(-0.4, 0.4), 1),
                y=round(y + rng.uniform(-0.4, 0.4), 1),
                shot_zone=zone,
                shot_type="penalty"
                if zone == "penalty"
                else "fast_break"
                if zone == "fast_break"
                else None,
                goal_zone=rng.choice(["TL", "TC", "TR", "ML", "MC", "MR", "BL", "BC", "BR"])
                if item["outcome"] in ("goal", "save")
                else None,
            )
            if item["outcome"] in ("save", "goal"):
                # saves and goals against to the numbered goalkeeper in goal: ours, theirs
                e["attributes"] = {"goalkeeper_number": DEMO_KEEPER_OPPONENT if own else keeper}
        if own:
            e["number"] = shooter
        else:
            e["number"] = rng.choice(opp_numbers)
        out.append(e)
    return out


async def demo_match(ctx: Ctx, team_id: uuid.UUID) -> Match:
    """The example match of «Demo-Spiel ansehen»: one per team, with realistic events, marked as
    an example (`source` demo). It is no match of the team: lists, figures, statistics and pick
    lists leave it out (services/matches.counted, app review R1).

    It mixes with nothing real (A4): our players are invented shirt numbers, never the roster's
    names; the date is the first day of the season, far from the fixtures; the opponent is an
    invented club of the demo story with an opponent entry of its own (not a real opponent of the
    club that happens to carry the name)."""
    existing = await ctx.db.scalar(
        select(Match).where(Match.team_id == team_id, Match.source == DEMO_SOURCE)
    )
    if existing:
        return existing
    team = await get_team(ctx, team_id, Action.MATCH_WRITE)
    season = (await current_seasons(ctx, [team.id])).get(team.id)
    if season is None:
        raise ProblemError(409, "no-season", "The team has no season")
    m = await create_match(
        ctx,
        team_id,
        MatchCreate(
            opponent_id=(await _demo_opponent(ctx)).id,
            kickoff_at=demo_kickoff(season.starts_on, datetime.now(UTC).date()),
            is_demo=True,
        ),
    )
    m.source = DEMO_SOURCE
    m.halftime_own = m.halftime_opponent = 0
    own = opp = 0
    for e in demo_events(m.period_s):
        if e.get("outcome") == "goal":
            own, opp = (own + 1, opp) if e["side"] == "own" else (own, opp + 1)
            if e["period"] == 1:
                m.halftime_own, m.halftime_opponent = own, opp
        ctx.db.add(
            Event(
                organization_id=m.organization_id,
                match_id=m.id,
                source="demo",
                confidence=1.0,
                **e,
            )
        )
    m.score_own, m.score_opponent = own, opp
    await ctx.db.flush()
    await audit.record(ctx, "match.demo_created", target_type="match", target_id=m.id)
    return m


async def _demo_opponent(ctx: Ctx) -> Opponent:
    """The opponent entry of the club's example matches: the one an example already plays,
    else a new one (a real opponent of the same name stays the club's own)."""
    org_id = ctx.require_actor().organization_id
    known = await ctx.db.scalar(
        select(Opponent)
        .join(Match, Match.opponent_id == Opponent.id)
        .where(
            Opponent.organization_id == org_id,
            Match.source == DEMO_SOURCE,
            Opponent.name == DEMO_OPPONENT,
        )
        .order_by(Opponent.created_at)
        .limit(1)
    )
    if known is not None:
        return known
    opp = Opponent(organization_id=org_id, name=DEMO_OPPONENT)
    ctx.db.add(opp)
    await ctx.db.flush()
    return opp


# ---- onboarding e-mail series ------------------------------------------------------------------


def unsubscribe_token(ctx: Ctx, user_id: uuid.UUID) -> str:
    key = ctx.settings.secret_key.get_secret_value().encode()
    return hmac.new(key, f"onboarding:{user_id}".encode(), hashlib.sha256).hexdigest()[:40]


async def unsubscribe(ctx: Ctx, user_id: uuid.UUID, token: str) -> None:
    if not hmac.compare_digest(unsubscribe_token(ctx, user_id), token):
        raise ProblemError(404, "not-found", "Link not valid")
    user = await ctx.db.get(User, user_id)
    if user is not None:
        user.onboarding_opt_out = True


async def run_series(ctx: Ctx, now: datetime | None = None) -> int:
    """Sends the due mail of the series (one per user and run); needs system access."""
    now = now or datetime.now(UTC)
    since = now - timedelta(days=max(SERIES_DAYS) + 2)
    users = (
        await ctx.db.scalars(
            select(User).where(
                User.created_at >= since,
                User.onboarding_opt_out.is_(False),
                User.email_verified_at.is_not(None),
            )
        )
    ).all()
    sent = 0
    for u in users:
        age = (now - u.created_at).days
        due = [d for d in SERIES_DAYS if d <= age and d not in (u.onboarding_sent or [])]
        if not due:
            continue
        day = max(due)  # never send a backlog: only the latest due mail
        base = ctx.settings.web_base_url
        link = (
            base + SERIES_LINKS[day]
            if not SERIES_LINKS[day].startswith("/hilfe")
            else ctx.settings.help_base_url + SERIES_LINKS[day][6:]
        )
        unsub = f"{base}/v1/onboarding/unsubscribe?u={u.id}&t={unsubscribe_token(ctx, u.id)}"
        sent_ok = await try_send(
            ctx.email,
            render(
                f"onboarding_{day}",
                u.locale,
                to=u.email,
                name=u.name.split()[0],
                link=link,
                unsubscribe=unsub,
            ),
            f"onboarding_{day}",
            user_id=str(u.id),
        )
        if not sent_ok:  # retried on the next run; the other users still get theirs
            continue
        u.onboarding_sent = sorted({*(u.onboarding_sent or []), *due})
        sent += 1
    await ctx.db.flush()
    return sent
