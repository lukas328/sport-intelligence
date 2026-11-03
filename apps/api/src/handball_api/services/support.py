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
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from handball_api.core.email import Email
from handball_api.core.errors import ProblemError
from handball_api.integrations.support import CrispChat, NoSupportChat
from handball_api.models import (
    Event,
    Match,
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
from handball_api.services.matches import create_match

SERIES_DAYS = (0, 1, 3, 7, 14)
SERIES_LINKS = {0: "/app", 1: "/hilfe/aufnahme", 3: "/hilfe/videositzung", 7: "/app", 14: "/app"}


# ---- failed analyses ------------------------------------------------------------------------


def failure_code(error: str | None) -> str:
    """Stable code for an analysis error; the UI explains it and suggests the next step."""
    e = (error or "").lower()
    if "calibration" in e:
        return "calibration"
    if "no video stream" in e or "unknown duration" in e or "probe" in e or "decode" in e:
        return "unreadable"
    if "too short" in e:
        return "too_short"
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
    await ctx.email.send(
        Email(
            to=ctx.settings.support_email,
            subject=f"Feedback: {message[:60]}",
            text=f"{message}\n\n---\nVon: {user.name} <{user.email}>\n" + "\n".join(lines),
            attachments=attachments,
        )
    )
    await audit.record(ctx, "support.feedback", data={"page": context.get("page")})


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
    demo = await count(select(func.count(Match.id)).where(Match.is_demo))
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


async def demo_match(ctx: Ctx, team_id: uuid.UUID) -> Match:
    """A demo match with realistic events to try the analysis views (marked as demo)."""
    existing = await ctx.db.scalar(select(Match).where(Match.team_id == team_id, Match.is_demo))
    if existing:
        return existing
    m = await create_match(
        ctx,
        team_id,
        MatchCreate(
            opponent_name="Demo HC Beispiel",
            kickoff_at=datetime.now(UTC) - timedelta(days=2),
            is_demo=True,
        ),
    )
    rng = random.Random(7)  # noqa: S311 (demo data, not security relevant)
    numbers = await ctx.db.execute(
        select(RosterEntry.player_id, RosterEntry.jersey_number).where(
            RosterEntry.season_id == m.season_id
        )
    )
    own_players = [pid for pid, _ in numbers.all()]
    own = opp = 0
    for k in range(64):
        period = 1 if k < 32 else 2
        clock = (k % 32) * 55.0 + rng.uniform(0, 40) + (period - 1) * m.period_s
        side = "own" if k % 2 == 0 else "opponent"
        x = rng.uniform(26, 38) if side == "own" else rng.uniform(2, 14)
        y = rng.uniform(1, 19)
        outcome = rng.choices(["goal", "save", "miss", "blocked"], weights=[55, 25, 15, 5])[0]
        if outcome == "goal":
            own, opp = (own + 1, opp) if side == "own" else (own, opp + 1)
        ctx.db.add(
            Event(
                organization_id=m.organization_id,
                match_id=m.id,
                type="shot",
                side=side,
                period=period,
                clock_s=round(clock, 1),
                x=round(x, 1),
                y=round(y, 1),
                outcome=outcome,
                number=rng.randint(2, 30) if side == "opponent" else None,
                player_id=rng.choice(own_players) if side == "own" and own_players else None,
                goal_zone=rng.choice(["TL", "TC", "TR", "ML", "MC", "MR", "BL", "BC", "BR"])
                if outcome in ("goal", "save")
                else None,
                source="demo",
                confidence=1.0,
            )
        )
        if k % 9 == 4:
            ctx.db.add(
                Event(
                    organization_id=m.organization_id,
                    match_id=m.id,
                    type="turnover",
                    side=side,
                    period=period,
                    clock_s=round(clock + 5, 1),
                    turnover_type=rng.choice(["bad_pass", "steps", "offensive_foul"]),
                    source="demo",
                    confidence=1.0,
                )
            )
    m.score_own, m.score_opponent = own, opp
    await ctx.db.flush()
    await audit.record(ctx, "match.demo_created", target_type="match", target_id=m.id)
    return m


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
        await ctx.email.send(
            render(
                f"onboarding_{day}",
                u.locale,
                to=u.email,
                name=u.name.split()[0],
                link=link,
                unsubscribe=unsub,
            )
        )
        u.onboarding_sent = sorted({*(u.onboarding_sent or []), *due})
        sent += 1
    await ctx.db.flush()
    return sent
