# 021. Data assistant: typed tools, number validator, scripted and live evaluation

- Status: accepted
- Date: 2026-11-03

## Context
Addendum 01, 5.1 asks for a chat in which coaches ask questions about their data in plain
language. Answers must not contain invented numbers (P3), every figure must lead to video (P2),
the cost per organisation is capped, and an evaluation set of at least 60 questions runs in CI.
This environment has no API key for the model, so the model itself cannot be measured here.

## Decision
- **Claude API with tool use**, model `claude-opus-5-5`, effort `low` (chat latency, the tools do
  the arithmetic), server-side refusal fallback, cached system prompt and tools. A manual loop in
  `services/assistant.py` (at most 6 model calls) instead of the SDK tool runner: we need the
  validator between the model's final answer and the user, per-question budget checks and our own
  log format.
- **Typed tools, no SQL**: `list_matches`, `query_events`, `aggregate_metric`, `compare_periods`,
  `find_plays`, `get_clips`, `list_insights`, and `final_answer` for the answer itself. They run on
  one team's data that the user may analyse (`Action.ASSISTANT_USE` = coaches, analysts and
  specialist coaches). The queries live in `handball_metrics.query` (pure functions, reused by the
  statistics matrix of 5.4). Players leave the organisation only as jersey numbers.
- **Number validator**: every number in the answer text, the values and the chart must appear in a
  tool result of the same question (ratios also as rounded percentages, dates by their parts,
  counting words 0, 1, 2 and 60 minutes allowed). A violation gets one correction round, then the
  user gets "cannot answer reliably" with an answerable suggestion. Clips are limited to event ids
  the tools returned and to events with video.
- **Follow-up questions** get the last four questions and answers as plain text, not the earlier
  tool and thinking blocks (no history edits, small requests).
- **Logging and budget**: every question with answer, transcript, tool calls, tokens, cost, latency,
  validator status and the user's rating in `assistant_messages` (tenant RLS). Monthly cap per plan
  (`assistant_usd_month`: Team 5, Club 25 USD of model cost; 5 when limits are off).
- **Evaluation**: `apps/api/tests/assistant_eval.py` holds a deterministic season (8 matches, about
  560 events) and 62 questions (55 answerable, 7 deliberately not answerable: speed, spectators,
  names, weather, salary, the future, plays against 5-1 without formation data). Expected values are
  computed from the raw events with plain Python, not with the query module. CI replays each
  question's tool plan with a scripted model through the real API (permissions, tools, validator,
  logging); this tests everything except the model's planning. `pytest -m live` runs the same set
  against the real model and writes `docs/perf/assistant-eval.md` (acceptance 90 % correct, no
  invented number, p95 under 8 s).

## Consequences
- The scripted CI run cannot prove the 90 % accuracy of the model; the live run with a key does and
  is listed as open until it ran (OPEN_QUESTIONS Q-M10-1).
- Answers are only as good as the recorded events: until ball detection exists most shot data comes
  from tagging and imports.
- Formation questions need video analysis; plays need events linked to plays (`attributes.play_id`).
