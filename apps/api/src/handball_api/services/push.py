"""Push notifications to the native apps (addendum 01, 5.5).

Devices register their Expo push token per user. Every in-app notification is also queued as a
push job; the worker sends it to the Expo push service (APNs and FCM behind it). The text is short
and contains no names; the link opens the matching screen (deep link).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.models import DeviceToken, User
from handball_api.services.context import Ctx

QUEUE = "default"
FUNC = "handball_worker.push.send"
TEXTS: dict[str, dict[str, str]] = {
    "de-CH": {
        "assignment": "Neue Aufgabe vom Trainerteam",
        "assignment_done": "Eine Aufgabe wurde erledigt",
        "feed_ready": "Neue Szenen von dir sind da",
        "analysis_ready": "Die Analyse ist fertig",
        "analysis_failed": "Die Analyse hat nicht geklappt",
        "scouting_ready": "Der Vorbereitungsbericht ist bereit",
        "_": "Neue Mitteilung",
    },
    "fr": {
        "assignment": "Nouvelle tâche du staff",
        "assignment_done": "Une tâche a été terminée",
        "feed_ready": "De nouvelles scènes de toi sont là",
        "analysis_ready": "L'analyse est prête",
        "analysis_failed": "L'analyse n'a pas abouti",
        "scouting_ready": "Le rapport de préparation est prêt",
        "_": "Nouvelle notification",
    },
    "en": {
        "assignment": "New assignment from the coaches",
        "assignment_done": "An assignment was completed",
        "feed_ready": "New scenes of you are ready",
        "analysis_ready": "The analysis is ready",
        "analysis_failed": "The analysis did not work",
        "scouting_ready": "The scouting report is ready",
        "_": "New notification",
    },
}


def text_for(kind: str, locale: str) -> str:
    t = TEXTS.get(locale, TEXTS["de-CH"])
    return t.get(kind, t["_"])


async def register(ctx: Ctx, token: str, platform: str) -> DeviceToken:
    if ctx.user_id is None:
        raise ProblemError(401, "unauthenticated", "Sign in first")
    if not (token.startswith("ExponentPushToken[") or token.startswith("ExpoPushToken[")):
        raise ProblemError(422, "validation", "Not an Expo push token")
    d = await ctx.db.scalar(select(DeviceToken).where(DeviceToken.token == token))
    if d is None:
        d = DeviceToken(token=token, user_id=ctx.user_id, platform=platform)
        ctx.db.add(d)
    d.user_id, d.platform, d.last_seen_at = ctx.user_id, platform, datetime.now(UTC)
    await ctx.db.flush()
    return d


async def unregister(ctx: Ctx, token: str) -> None:
    d = await ctx.db.scalar(
        select(DeviceToken).where(DeviceToken.token == token, DeviceToken.user_id == ctx.user_id)
    )
    if d is not None:
        await ctx.db.delete(d)


async def enqueue(ctx: Ctx, user_ids: list[uuid.UUID], kind: str, link: str | None) -> int:
    """Queues one push job per language for the users' devices; returns the number of devices."""
    if ctx.jobs is None or not user_ids:
        return 0
    rows = (
        await ctx.db.execute(
            select(DeviceToken.token, User.locale)
            .join(User, User.id == DeviceToken.user_id)
            .where(DeviceToken.user_id.in_(user_ids))
        )
    ).all()
    by_locale: dict[str, list[str]] = {}
    for token, locale in rows:
        by_locale.setdefault(locale or "de-CH", []).append(token)
    for locale, tokens in by_locale.items():
        payload: dict[str, Any] = {
            "tokens": tokens,
            "title": "Handball AI",
            "body": text_for(kind, locale),
            "data": {"kind": kind, "link": link},
        }
        ctx.jobs.enqueue(QUEUE, FUNC, f"push-{uuid.uuid4()}", {"payload": payload})
    return len(rows)
