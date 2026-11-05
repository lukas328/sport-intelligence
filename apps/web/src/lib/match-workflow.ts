/** The order of work on a match video (court, throw-off, goals, players) and what the video
 * covers of the match, in match time. Pure functions: the match workspace and its tests use them. */

export type StepId = "court" | "kickoff" | "goals" | "players";
export type StepState = "done" | "open" | "waiting";
export interface Step {
  id: StepId;
  state: StepState;
  /** what is still open (goals to check, tracks without a player), when that is a count */
  count?: number;
  /** a short reason key for the state, e.g. "check" (court found, not confirmed yet) */
  reason?: string;
}

/** One stretch of the match the video shows, in match seconds (0 = throw-off of the first half). */
export interface Span {
  from: number;
  to: number;
}

/** The parts of the match the video covers, from the throw-off marks (video ms per period).
 * Null while no throw-off is set: then the video cannot be placed on the match clock. */
export function coverage(
  kickoff: Record<string, number> | null | undefined,
  periodS: number,
  durationMs: number | null | undefined,
  periods = 2,
): Span[] | null {
  const k = kickoff ?? {};
  if (!Object.keys(k).length || !durationMs) return null;
  const spans: Span[] = [];
  for (let p = 1; p <= periods; p++) {
    const start = k[String(p)];
    if (start == null) continue;
    const next = k[String(p + 1)];
    const end = Math.min(durationMs, start + periodS * 1000, next ?? Infinity);
    if (end <= start) continue;
    const base = (p - 1) * periodS;
    // a clip that starts after the throw-off (a negative mark, e.g. read from the score overlay)
    spans.push({ from: base + Math.max(0, -start) / 1000, to: base + (end - start) / 1000 });
  }
  return spans;
}

/** Seconds of the match the video covers. */
export const covered = (spans: Span[]) => spans.reduce((s, x) => s + (x.to - x.from), 0);

export const inside = (clockS: number, spans: Span[]) => spans.some((s) => clockS >= s.from && clockS <= s.to);

/** Whether a throw-off mark is still needed: the first half always, the second half once the
 * video runs past the end of the first half. */
export function kickoffMissing(
  kickoff: Record<string, number> | null | undefined,
  periodS: number,
  durationMs: number | null | undefined,
): number[] {
  const k = kickoff ?? {};
  const k1 = k["1"];
  if (k1 == null) return [1];
  // a halftime break of a few minutes: only then the second half is in the picture
  const second = durationMs != null && durationMs > k1 + periodS * 1000 + 5 * 60_000;
  return second && k["2"] == null ? [2] : [];
}

export interface StepInput {
  analysis: { status: string; needsCalibration: boolean; unconfirmed: boolean } | null;
  kickoff: Record<string, number> | null | undefined;
  periodS: number;
  durationMs: number | null | undefined;
  /** open goal candidates and open official goals; null when there is no such list */
  candidatesOpen: number | null;
  officialOpen: number | null;
  /** own-team tracks without a player; null before the analysis has tracks */
  unassigned: number | null;
}

export function steps(i: StepInput): Step[] {
  const a = i.analysis;
  const court: Step =
    !a || a.status === "none" || a.status === "running"
      ? { id: "court", state: "waiting" }
      : a.status === "failed"
        ? { id: "court", state: "open", reason: "failed" }
        : a.needsCalibration
          ? { id: "court", state: "open", reason: "mark" }
          : a.unconfirmed
            ? { id: "court", state: "open", reason: "check" }
            : { id: "court", state: "done" };
  const missing = kickoffMissing(i.kickoff, i.periodS, i.durationMs);
  const kickoff: Step = missing.length
    ? { id: "kickoff", state: "open", reason: `period${missing[0]}` }
    : (i.kickoff?.["1"] ?? 0) < 0
      ? { id: "kickoff", state: "done", reason: "fromClip" } // the video starts later in the half
      : { id: "kickoff", state: "done" };
  const open = (i.candidatesOpen ?? 0) + (i.officialOpen ?? 0);
  const goals: Step =
    i.candidatesOpen == null && i.officialOpen == null
      ? { id: "goals", state: "waiting" }
      : open > 0
        ? { id: "goals", state: "open", count: open }
        : { id: "goals", state: "done" };
  const players: Step =
    i.unassigned == null
      ? { id: "players", state: "waiting" }
      : i.unassigned > 0
        ? { id: "players", state: "open", count: i.unassigned }
        : { id: "players", state: "done" };
  return [court, kickoff, goals, players];
}

/** The step to show first: the first one that asks for something. */
export const firstOpen = (list: Step[]): StepId | null => list.find((s) => s.state === "open")?.id ?? null;

/** Match clock (s) for a video time, from the throw-off marks; mirrors the API's clock_from_video. */
export function clockAt(kickoff: Record<string, number> | null | undefined, periodS: number, tMs: number): number | null {
  const starts = Object.entries(kickoff ?? {})
    .map(([p, ms]) => [Number(p), ms] as const)
    .filter(([, ms]) => ms <= tMs)
    .sort((a, b) => a[0] - b[0]);
  const last = starts[starts.length - 1];
  if (!last) return null;
  const [period, start] = last;
  return (period - 1) * periodS + (tMs - start) / 1000;
}
