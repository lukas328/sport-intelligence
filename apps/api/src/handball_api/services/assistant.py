"""Ask your data (addendum 01, 5.1).

The model only chooses typed, predefined queries (no SQL) and phrases the answer. Every tool works
on the data of one team the user may analyse; jersey numbers instead of names leave the
organisation. The final answer goes through `final_answer`; each number of its text must come from
a tool result of this question (`invented_numbers`), otherwise the model gets one correction round
and then the user gets an honest "cannot answer" with a suggestion. Everything is logged with tool
calls, tokens and cost; the model cost per organisation and month is capped by the plan.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from handball_api.core.assistant_llm import (
    AssistantModel,
    AssistantUnavailableError,
    ModelTurn,
    Usage,
    invented_numbers,
    numbers_from,
)
from handball_api.core.errors import ProblemError
from handball_api.models import (
    AssistantConversation,
    AssistantMessage,
    Organization,
    Play,
)
from handball_api.services import audit, billing
from handball_api.services.context import Ctx
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action
from handball_api.services.team_data import TeamData, load
from handball_metrics.query import (
    GROUPS,
    METRICS,
    Filter,
    Row,
    aggregate,
    compare,
    minute,
    ordered_matches,
)
from handball_metrics.query import (
    select as select_rows,
)
from handball_metrics.stats import zone_of

MAX_MODEL_CALLS = 6
MAX_EVENTS = 30
ZONES = [
    "wing_left",
    "wing_right",
    "back_left",
    "back_centre",
    "back_right",
    "half_left",
    "half_centre",
    "half_right",
    "circle_left",
    "circle_centre",
    "circle_right",
    "penalty",
    "fast_break",
    "long_range",
    "empty_goal",
]
FORMATIONS = ["6-0", "5-1", "4-2", "3-2-1", "3-3", "open"]
LANG = {
    "de-CH": "German (Switzerland: write ss, never the sharp s)",
    "fr": "French",
    "en": "English",
}

SYSTEM = """You answer handball coaches' questions about their own team's data.

Rules:
- Use the tools to get every figure. Never compute, estimate or remember numbers yourself: every
  number in your answer must appear in a tool result (percentages may be rounded from a ratio).
- Finish every question with exactly one call of `final_answer`. Put the key figures in `values`,
  the number of events or shots behind them in `sample_size`, and up to 10 `event_ids` from tool
  results as evidence clips. Add a `chart` only when it helps compare several groups.
- Say how large the sample is. With fewer than 10 events, say the figure is uncertain.
- Comparisons and before/after are observations, not proof of cause; say so.
- If the question cannot be answered with the tools or the data (no events of that kind, a topic
  the data does not cover, a person's name instead of a jersey number), call `final_answer` with
  `answerable: false`, explain briefly why, and suggest one question that can be answered.
- Players are identified by jersey number only. Do not invent names.
- Write short, plain sentences in the user's language, no bullet points, no long dashes.

Glossary: "we/our/own" = side own, "they/opponent/Gegner" = side opponent. Goals against us =
opponent goals (side opponent, outcome goal). Our goalkeeper's saves = metric save_pct on side
opponent. Zones are seen from the attacker: Rechtsaussen / right wing = wing_right, Linksaussen =
wing_left, Kreis = circle_*, Rückraum = back_*, 7 m = penalty. A timeout question means events up
to 120 s after an own timeout (filter after_timeout_s)."""

FILTER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Restricts the events. Omit fields you do not need.",
    "properties": {
        "last_n_matches": {"type": "integer", "minimum": 1, "maximum": 100},
        "match_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        "opponent": {"type": "string", "description": "part of the opponent's name"},
        "type": {
            "type": "string",
            "enum": [
                "shot",
                "turnover",
                "steal",
                "foul",
                "seven_meter_awarded",
                "suspension_2min",
                "yellow_card",
                "red_card",
                "timeout",
            ],
        },
        "side": {"type": "string", "enum": ["own", "opponent"]},
        "outcome": {"type": "string", "enum": ["goal", "save", "miss", "post", "blocked"]},
        "zone": {"type": "string", "enum": ZONES},
        "shot_type": {
            "type": "string",
            "enum": [
                "jump_shot",
                "standing",
                "pivot",
                "wing",
                "fast_break",
                "penalty",
                "empty_net",
            ],
        },
        "goal_zone": {
            "type": "string",
            "enum": ["TL", "TC", "TR", "ML", "MC", "MR", "BL", "BC", "BR"],
        },
        "number": {"type": "integer", "description": "jersey number"},
        "period": {"type": "integer", "minimum": 1, "maximum": 4},
        "minute_from": {"type": "integer", "minimum": 1},
        "minute_to": {"type": "integer", "minimum": 1},
        "after_timeout_s": {"type": "integer", "minimum": 10, "maximum": 600},
        "opponent_formation": {"type": "string", "enum": FORMATIONS},
    },
    "additionalProperties": False,
}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "list_matches",
        "description": "Matches of the team, newest first, with date, opponent, score and the "
        "number of recorded events.",
        "input_schema": {
            "type": "object",
            "properties": {
                "last_n": {"type": "integer", "minimum": 1, "maximum": 50},
                "opponent": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "query_events",
        "description": "Counts and lists events matching a filter (newest first, at most 30 "
        "listed), with match, minute, zone and jersey number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filter": FILTER_SCHEMA,
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_EVENTS},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "aggregate_metric",
        "description": "One metric over the filtered events, optionally grouped. Ratios are "
        "0..1 with numerator and denominator. Metrics: "
        + "; ".join(f"{k}: {v.label}" for k, v in METRICS.items()),
        "input_schema": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "enum": list(METRICS)},
                "filter": FILTER_SCHEMA,
                "group_by": {"type": "string", "enum": list(GROUPS)},
            },
            "required": ["metric"],
            "additionalProperties": False,
        },
    },
    {
        "name": "compare_periods",
        "description": "The same metric for two filters (for example first and second half, "
        "last 5 matches against the 5 before, after a timeout against the rest).",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "enum": list(METRICS)},
                "a": {
                    "type": "object",
                    "properties": {"label": {"type": "string"}, "filter": FILTER_SCHEMA},
                    "required": ["label", "filter"],
                    "additionalProperties": False,
                },
                "b": {
                    "type": "object",
                    "properties": {"label": {"type": "string"}, "filter": FILTER_SCHEMA},
                    "required": ["label", "filter"],
                    "additionalProperties": False,
                },
            },
            "required": ["metric", "a", "b"],
            "additionalProperties": False,
        },
    },
    {
        "name": "find_plays",
        "description": "Plays of the team's library with the shots linked to them (goals, "
        "shooting percentage), optionally only against an opponent defence formation detected "
        "by the video analysis.",
        "input_schema": {
            "type": "object",
            "properties": {"opponent_formation": {"type": "string", "enum": FORMATIONS}},
            "additionalProperties": False,
        },
    },
    {
        "name": "get_clips",
        "description": "Video positions for event ids (only events with video).",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 10}
            },
            "required": ["event_ids"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_insights",
        "description": "Automatic insights of a match (default: the newest match with events), "
        "each with its sample.",
        "input_schema": {
            "type": "object",
            "properties": {"match_id": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "final_answer",
        "description": "The answer shown to the user. Call it exactly once, last.",
        "input_schema": {
            "type": "object",
            "properties": {
                "answerable": {"type": "boolean"},
                "text": {"type": "string", "description": "2 to 4 short sentences"},
                "values": {"type": "array", "items": {"type": "number"}},
                "sample_size": {"type": "integer"},
                "event_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
                "chart": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "labels": {"type": "array", "items": {"type": "string"}},
                        "values": {"type": "array", "items": {"type": "number"}},
                    },
                    "required": ["title", "labels", "values"],
                    "additionalProperties": False,
                },
                "suggestion": {
                    "type": "string",
                    "description": "an answerable question, when answerable is false",
                },
            },
            "required": ["answerable", "text"],
            "additionalProperties": False,
        },
    },
]


# ---- tools --------------------------------------------------------------------------------------


def _event_out(data: TeamData, r: Row) -> dict[str, Any]:
    e = r.event
    return {
        "event_id": e.id,
        "match_id": r.match.id,
        "date": r.match.date,
        "opponent": r.match.opponent,
        "period": e.period,
        "minute": minute(e),
        "type": e.type.value,
        "side": e.side.value,
        "outcome": e.outcome,
        "zone": zone_of(e) if e.is_shot else None,
        "number": e.number,
        "has_video": data.event_ms.get(e.id) is not None,
    }


def _filter(raw: Any) -> Filter:
    return Filter.from_dict(raw if isinstance(raw, dict) else None)


async def run_tool(ctx: Ctx, data: TeamData, name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "list_matches":
        counts: dict[str, int] = {}
        for r in data.rows:
            counts[r.match.id] = counts.get(r.match.id, 0) + 1
        ms = ordered_matches(data.matches.values())
        if args.get("opponent"):
            ms = [m for m in ms if str(args["opponent"]).lower() in (m.opponent or "").lower()]
        ms = ms[: int(args.get("last_n") or 20)]
        return {
            "matches": [
                {
                    "match_id": m.id,
                    "date": m.date,
                    "opponent": m.opponent,
                    "score_own": m.score_own,
                    "score_opponent": m.score_opponent,
                    "events": counts.get(m.id, 0),
                    "formation_data": bool(m.opponent_formations),
                }
                for m in ms
            ],
            "total_matches": len(data.matches),
        }
    if name == "query_events":
        rows = select_rows(data.rows, _filter(args.get("filter")))
        rows.sort(key=lambda r: (r.match.date, r.event.period, r.event.clock_s or 0), reverse=True)
        limit = min(int(args.get("limit") or 20), MAX_EVENTS)
        return {
            "count": len(rows),
            "matches": len({r.match.id for r in rows}),
            "events": [_event_out(data, r) for r in rows[:limit]],
        }
    if name == "aggregate_metric":
        rows = select_rows(data.rows, _filter(args.get("filter")))
        result = aggregate(rows, str(args["metric"]), args.get("group_by"))
        if result.get("group_by") == "match":
            for g in result["groups"]:
                m = data.matches.get(g["key"])
                g["date"], g["opponent"] = (m.date, m.opponent) if m else (None, None)
        result["example_event_ids"] = [r.event.id for r in rows[:10]]
        return result
    if name == "compare_periods":
        a, b = args["a"], args["b"]
        result = compare(data.rows, str(args["metric"]), _filter(a["filter"]), _filter(b["filter"]))
        result["a"]["label"], result["b"]["label"] = a.get("label"), b.get("label")
        return result
    if name == "find_plays":
        plays = (
            await ctx.db.scalars(
                select(Play).where(Play.team_id == data.team.id).order_by(Play.name)
            )
        ).all()
        out = []
        for p in plays:
            rows = select_rows(
                data.rows,
                Filter(
                    play_id=str(p.id),
                    type="shot",
                    opponent_formation=args.get("opponent_formation"),
                ),
            )
            v = aggregate(rows, "shooting_pct")
            out.append(
                {
                    "play_id": str(p.id),
                    "name": p.name,
                    "category": p.category,
                    "shots": v["denominator"],
                    "goals": int(v["numerator"]),
                    "shooting_pct": v["value"],
                    "event_ids": [r.event.id for r in rows[:5]],
                }
            )
        out.sort(key=lambda x: (-(x["shots"] or 0), x["name"]))
        linked = sum(1 for p in out if p["shots"])
        return {
            "plays": out,
            "plays_with_shots": linked,
            "note": None
            if linked
            else "no shots are linked to plays yet (link plays to events while tagging)",
        }
    if name == "get_clips":
        clips = []
        for eid in args.get("event_ids") or []:
            row = data.by_id.get(str(eid))
            t = data.event_ms.get(str(eid))
            if row is not None and t is not None:
                clips.append({"event_id": row.event.id, "match_id": row.match.id, "t_ms": t})
        return {"clips": clips}
    if name == "list_insights":
        from handball_api.services.insights import insights as match_insights

        match_id = args.get("match_id")
        if not match_id:
            with_events = {r.match.id for r in data.rows}
            newest = [m for m in ordered_matches(data.matches.values()) if m.id in with_events]
            if not newest:
                return {"insights": [], "note": "no match with events"}
            match_id = newest[0].id
        if str(match_id) not in data.matches:
            raise ValueError("unknown match")
        result = await match_insights(ctx, uuid.UUID(str(match_id)))
        return {
            "match_id": str(match_id),
            "baseline_matches": result["baseline_matches"],
            "insights": [
                {
                    "kind": i.get("kind"),
                    "key": i.get("key"),
                    "params": i.get("params"),
                    "sample": i.get("sample"),
                }
                for i in result["insights"]
            ],
        }
    raise ValueError(f"unknown tool {name}")


# ---- budget -------------------------------------------------------------------------------------


def _month_start() -> datetime:
    return datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def month_cost(ctx: Ctx, org_id: uuid.UUID) -> float:
    total = await ctx.db.scalar(
        select(func.coalesce(func.sum(AssistantMessage.cost_usd), 0.0)).where(
            AssistantMessage.organization_id == org_id,
            AssistantMessage.created_at >= _month_start(),
        )
    )
    return float(total or 0.0)


def month_budget(ctx: Ctx, org: Organization) -> float:
    if not ctx.settings.billing_enforce:
        return ctx.settings.assistant_usd_month_unenforced
    return billing.spec(org).assistant_usd_month


# ---- conversation -------------------------------------------------------------------------------


def _fallback(lang: str, reason: str) -> dict[str, Any]:
    texts = {
        "de-CH": (
            "Diese Frage kann ich mit den vorhandenen Daten nicht verlässlich beantworten.",
            "Wie hoch war unsere Wurfquote in den letzten 5 Spielen?",
        ),
        "fr": (
            "Je ne peux pas répondre de manière fiable à cette question avec les données "
            "disponibles.",
            "Quel était notre pourcentage de réussite au tir lors des 5 derniers matchs ?",
        ),
        "en": (
            "I cannot answer this question reliably with the available data.",
            "What was our shooting percentage in the last 5 matches?",
        ),
    }
    text, suggestion = texts.get(lang, texts["de-CH"])
    return {
        "answerable": False,
        "text": text,
        "values": [],
        "sample_size": None,
        "event_ids": [],
        "chart": None,
        "suggestion": suggestion,
        "reason": reason,
    }


def _history(previous: list[AssistantMessage]) -> list[dict[str, Any]]:
    """Earlier questions and answers of the conversation as plain text (no tool blocks)."""
    out: list[dict[str, Any]] = []
    for m in previous[-4:]:
        out.append({"role": "user", "content": m.question})
        out.append({"role": "assistant", "content": str(m.answer.get("text") or "-")})
    return out


async def ask(
    ctx: Ctx,
    model: AssistantModel | None,
    team_id: uuid.UUID,
    question: str,
    conversation_id: uuid.UUID | None = None,
    lang: str = "de-CH",
) -> AssistantMessage:
    if model is None:
        raise ProblemError(503, "assistant-unavailable", "The assistant is not configured")
    team = await get_team(ctx, team_id, Action.ASSISTANT_USE)
    await billing.require_feature(ctx, "assistant", team.organization_id)
    org = await ctx.db.get(Organization, team.organization_id)
    assert org is not None
    if await month_cost(ctx, org.id) >= month_budget(ctx, org):
        raise ProblemError(429, "assistant-budget", "The assistant budget of this month is used up")
    question = question.strip()[:500]
    if conversation_id:
        conv = await ctx.db.get(AssistantConversation, conversation_id)
        if conv is None or conv.team_id != team.id or conv.user_id != ctx.user_id:
            raise ProblemError(404, "not-found", "Conversation not found")
    else:
        conv = AssistantConversation(
            organization_id=org.id, team_id=team.id, user_id=ctx.user_id, title=question[:200]
        )
        ctx.db.add(conv)
        await ctx.db.flush()
    previous = (
        await ctx.db.scalars(
            select(AssistantMessage)
            .where(AssistantMessage.conversation_id == conv.id)
            .order_by(AssistantMessage.created_at)
        )
    ).all()
    data = await load(ctx, team)
    record = await _converse(ctx, model, data, question, list(previous), lang)
    record.organization_id = org.id
    record.conversation_id = conv.id
    ctx.db.add(record)
    await ctx.db.flush()
    await audit.record(ctx, "assistant.asked", target_type="assistant_message", target_id=record.id)
    return record


async def _converse(
    ctx: Ctx,
    model: AssistantModel,
    data: TeamData,
    question: str,
    previous: list[AssistantMessage],
    lang: str,
) -> AssistantMessage:
    with_events = len({r.match.id for r in data.rows})
    context = (
        f"Team: {data.team.name}. Matches: {len(data.matches)}, with recorded events: "
        f"{with_events}. Answer in {LANG.get(lang, LANG['de-CH'])}.\n\nQuestion: {question}"
    )
    messages: list[dict[str, Any]] = [*_history(previous), {"role": "user", "content": context}]
    start = len(messages) - 1
    allowed = numbers_from(question)
    seen_ids: set[str] = set()
    calls: list[dict[str, Any]] = []
    usage = Usage()
    answer: dict[str, Any] | None = None
    status = "ok"
    corrections = 0
    began = time.monotonic()
    model_name = model.model
    for _ in range(MAX_MODEL_CALLS):
        try:
            turn: ModelTurn = await model.respond(SYSTEM, TOOLS, messages)
        except AssistantUnavailableError as exc:
            status = f"model_{exc}"
            break
        usage.add(turn.usage)
        model_name = turn.model
        messages.append({"role": "assistant", "content": turn.content})
        uses = [b for b in turn.content if b.get("type") == "tool_use"]
        if turn.stop_reason in ("refusal", "max_tokens") or (
            not uses and turn.stop_reason != "end_turn"
        ):
            status = f"stopped_{turn.stop_reason}"
            break
        if not uses:
            text = " ".join(b.get("text", "") for b in turn.content if b.get("type") == "text")
            answer = {"answerable": True, "text": text.strip(), "values": [], "event_ids": []}
            bad = invented_numbers(answer["text"], allowed)
            if bad:
                status, answer = "invented_numbers", None
            break
        results: list[dict[str, Any]] = []
        final: dict[str, Any] | None = None
        for block in uses:
            name, args, tid = block["name"], dict(block.get("input") or {}), block["id"]
            if name == "final_answer":
                bad = _check_answer(args, allowed)
                if bad and corrections == 0:
                    corrections += 1
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tid,
                            "is_error": True,
                            "content": "These numbers come from no tool result: "
                            + ", ".join(bad)
                            + ". Use only numbers from tool results and call final_answer again.",
                        }
                    )
                    continue
                if bad:
                    status = "invented_numbers"
                    final = {}
                else:
                    final = args
                results.append({"type": "tool_result", "tool_use_id": tid, "content": "shown"})
                calls.append({"name": name, "input": args})
                continue
            t0 = time.monotonic()
            try:
                result = await run_tool(ctx, data, name, args)
                allowed |= numbers_from(result)
                seen_ids |= _ids(result)
                content = json.dumps(result, ensure_ascii=False, default=str)
                results.append({"type": "tool_result", "tool_use_id": tid, "content": content})
                calls.append(
                    {
                        "name": name,
                        "input": args,
                        "ms": round((time.monotonic() - t0) * 1000),
                        "summary": _summary(result),
                    }
                )
            except (ValueError, KeyError, TypeError) as exc:
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tid,
                        "is_error": True,
                        "content": f"Invalid input: {exc}",
                    }
                )
                calls.append({"name": name, "input": args, "error": str(exc)[:200]})
        messages.append({"role": "user", "content": results})
        if final is not None:
            answer = final or None
            break
    else:
        status = "too_many_steps"
    answer = _fallback(lang, status) if answer is None else _clean(answer, seen_ids, data)
    return AssistantMessage(
        question=question,
        answer=answer,
        transcript=messages[start:],
        tool_calls=calls,
        model=model_name,
        input_tokens=usage.input_tokens + usage.cache_read_tokens + usage.cache_write_tokens,
        output_tokens=usage.output_tokens,
        cost_usd=round(usage.cost_usd(model_name), 6),
        latency_ms=round((time.monotonic() - began) * 1000),
        answerable=bool(answer.get("answerable")),
        validated=status == "ok",
        status=status,
    )


def _check_answer(args: dict[str, Any], allowed: set[float]) -> list[str]:
    bad = invented_numbers(str(args.get("text") or ""), allowed)
    numbers = list(args.get("values") or []) + list((args.get("chart") or {}).get("values") or [])
    for v in numbers:
        if isinstance(v, int | float) and invented_numbers(str(v), allowed):
            bad.append(str(v))
    return bad


def _ids(result: dict[str, Any]) -> set[str]:
    out: set[str] = set()

    def walk(v: Any) -> None:
        if isinstance(v, dict):
            for k, x in v.items():
                if k in ("event_id",) and isinstance(x, str):
                    out.add(x)
                elif k in ("event_ids", "example_event_ids") and isinstance(x, list):
                    out.update(str(i) for i in x)
                else:
                    walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(result)
    return out


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    keys = ("count", "value", "numerator", "denominator", "matches", "total_matches", "difference")
    return {k: result[k] for k in keys if k in result}


def _clean(answer: dict[str, Any], seen: set[str], data: TeamData) -> dict[str, Any]:
    ids = [str(i) for i in answer.get("event_ids") or [] if str(i) in seen][:10]
    clips = [
        {
            "event_id": i,
            "match_id": data.by_id[i].match.id,
            "t_ms": data.event_ms.get(i),
            "label": _clip_label(data.by_id[i]),
        }
        for i in ids
        if i in data.by_id and data.event_ms.get(i) is not None
    ]
    chart = answer.get("chart")
    if chart and len(chart.get("labels") or []) != len(chart.get("values") or []):
        chart = None
    return {
        "answerable": bool(answer.get("answerable", True)),
        "text": str(answer.get("text") or "").strip(),
        "values": [v for v in answer.get("values") or [] if isinstance(v, int | float)],
        "sample_size": answer.get("sample_size"),
        "event_ids": ids,
        "clips": clips,
        "chart": chart,
        "suggestion": answer.get("suggestion"),
    }


def _clip_label(r: Row) -> str:
    e = r.event
    parts = [r.match.date, r.match.opponent or "", f"{minute(e)}'" if minute(e) else ""]
    if e.number is not None:
        parts.append(f"#{e.number}")
    return " ".join(p for p in parts if p)


# ---- reading ------------------------------------------------------------------------------------


async def conversations(ctx: Ctx, team_id: uuid.UUID) -> list[AssistantConversation]:
    await get_team(ctx, team_id, Action.ASSISTANT_USE)
    return list(
        (
            await ctx.db.scalars(
                select(AssistantConversation)
                .where(
                    AssistantConversation.team_id == team_id,
                    AssistantConversation.user_id == ctx.user_id,
                )
                .order_by(AssistantConversation.created_at.desc())
                .limit(50)
            )
        ).all()
    )


async def conversation(
    ctx: Ctx, conversation_id: uuid.UUID
) -> tuple[AssistantConversation, list[AssistantMessage]]:
    conv = await ctx.db.get(AssistantConversation, conversation_id)
    if conv is None or conv.user_id != ctx.user_id:
        raise ProblemError(404, "not-found", "Conversation not found")
    await get_team(ctx, conv.team_id, Action.ASSISTANT_USE)
    msgs = (
        await ctx.db.scalars(
            select(AssistantMessage)
            .where(AssistantMessage.conversation_id == conv.id)
            .order_by(AssistantMessage.created_at)
        )
    ).all()
    return conv, list(msgs)


async def rate(ctx: Ctx, message_id: uuid.UUID, rating: int) -> None:
    msg = await ctx.db.get(AssistantMessage, message_id)
    if msg is None:
        raise ProblemError(404, "not-found", "Message not found")
    await conversation(ctx, msg.conversation_id)
    msg.rating = 1 if rating > 0 else -1
