import type { Schemas } from "@handball/api-client";
import { formatClock } from "./format";
import { inside, type Span } from "./match-workflow";

/** Official goals compared with the goals the video analysis found (official-report/comparison). */
export type GoalComparison = Schemas["GoalComparison"];
export type Review = "confirmed" | "dismissed";
export type GoalFilter = "all" | "open";

/** One row of the list: an official goal (found in the video, missing, or outside: before or
 * after the video, which is a clip of part of the game) or a video goal that the report does not
 * have. */
export interface GoalRow {
  id: string;
  kind: "found" | "missing" | "outside" | "extra";
  side: string;
  period: number;
  clockS: number | null;
  time: string | null;
  tMs: number | null;
  estimated: boolean;
  number: number | null;
  playerId: string | null;
  name: string | null;
  score: number[] | null;
  penalty: boolean;
  source: string | null;
  review: Review | null;
}

/** Seconds of video before the goal, so the attack that led to it is in the picture. */
export const LEAD_MS = 4000;

/** Official and extra goals in one list, in match order; "open" keeps only what still needs a
 * look: missing and extra goals nobody confirmed or dismissed. Goals outside the video only with
 * `outside` (there is nothing to look at). */
export function goalRows(
  cmp: GoalComparison,
  filter: GoalFilter = "all",
  outside = false,
  covers: Span[] | null = null,
): GoalRow[] {
  const rows: GoalRow[] = [
    ...cmp.goals.map((g) => ({
      id: g.event_id,
      kind: g.status,
      side: g.side,
      period: g.period,
      clockS: g.clock_s,
      time: g.official_time,
      tMs: g.t_ms,
      estimated: g.estimated,
      number: g.number,
      playerId: g.player_id,
      name: g.name,
      score: g.score,
      penalty: g.penalty,
      source: g.video?.source ?? null,
      review: g.review,
    })),
    ...cmp.extra.map((g) => ({
      id: g.event_id,
      kind: "extra" as const,
      side: g.side,
      period: g.period,
      clockS: g.clock_s,
      time: g.official_time,
      tMs: g.t_ms,
      estimated: false,
      number: g.number,
      playerId: g.player_id,
      name: g.name,
      score: g.score,
      penalty: false,
      source: g.source,
      review: g.review,
    })),
  ];
  // a goal without a video time whose match time the video does not show (e.g. the second half of
  // a clip of the first) is outside too: there is nothing to check
  if (covers)
    for (const r of rows)
      if (r.kind === "missing" && r.tMs == null && r.clockS != null && !inside(r.clockS, covers)) r.kind = "outside";
  // match clock first; rows without one (video goal before the throw-off is known) by video time
  const key = (r: GoalRow) => r.clockS ?? (r.tMs != null ? r.tMs / 1000 : Number.POSITIVE_INFINITY);
  rows.sort(
    (a, b) =>
      a.period - b.period ||
      key(a) - key(b) ||
      (a.kind === "extra" ? 1 : 0) - (b.kind === "extra" ? 1 : 0),
  );
  if (filter === "open") return rows.filter(isOpen);
  return outside ? rows : rows.filter((r) => r.kind !== "outside");
}

/** The game time as the event list and the goal candidates show it ("2:59"): from the match
 * clock, else from the report's "MM:SS". */
export function gameTime(r: Pick<GoalRow, "clockS" | "time">): string | null {
  if (r.clockS != null) return formatClock(r.clockS * 1000);
  const m = r.time ? /^(\d+):(\d{2})$/.exec(r.time.trim()) : null;
  return m ? formatClock((Number(m[1]) * 60 + Number(m[2])) * 1000) : r.time;
}

export function isOpen(r: GoalRow): boolean {
  return (r.kind === "missing" || r.kind === "extra") && r.review == null;
}

/** Where the player jumps for a row, or null when the video time is not known yet or the goal is
 * not in the video. */
export function jumpTarget(r: GoalRow): number | null {
  return r.tMs == null || r.kind === "outside" ? null : Math.max(0, r.tMs - LEAD_MS);
}

/** Clicking the active review again undoes it. */
export function nextReview(current: Review | null, clicked: Review): Review | null {
  return current === clicked ? null : clicked;
}

/** The row with its review changed, for an optimistic update of the cached comparison. */
export function withReview(cmp: GoalComparison, id: string, review: Review | null): GoalComparison {
  const goals = cmp.goals.map((g) => (g.event_id === id ? { ...g, review } : g));
  const extra = cmp.extra.map((g) => (g.event_id === id ? { ...g, review } : g));
  const open =
    goals.filter((g) => g.status === "missing" && g.review == null).length +
    extra.filter((g) => g.review == null).length;
  return { ...cmp, goals, extra, counts: { ...cmp.counts, open } };
}
