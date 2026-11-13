/**
 * The clip of a goal question and the goal already confirmed in it (third real-video test G2):
 * the candidate time lies 4 to 7 s after the goal, so the clip runs from about 10 s before it
 * to 2 s after. A goal confirmed for the same side inside that clip is most likely the same goal.
 */

export function goalWindow(c: { t_ms: number }): { start_ms: number; end_ms: number } {
  return { start_ms: Math.max(0, c.t_ms - 10_000), end_ms: c.t_ms + 2_000 };
}

/** A confirmed goal of the same side (any side without a suggestion) inside the question's clip. */
export function sameGoal<G extends { team: string; t_ms?: number | null; has_video?: boolean }>(goals: readonly G[], c: { t_ms: number; suggested_side?: string | null }): G | null {
  const w = goalWindow(c);
  const team = c.suggested_side === "own" ? "own" : c.suggested_side === "opponent" ? "opp" : null;
  return goals.find((g) => g.has_video && g.t_ms != null && g.t_ms >= w.start_ms && g.t_ms <= w.end_ms && (team == null || g.team === team)) ?? null;
}
