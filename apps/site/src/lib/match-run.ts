/**
 * Saturday's card on the demo page, «Das Spiel in 20 Sekunden» (BEFUNDE-4 U32, U36): one match
 * clock drives the blurred hall video and the run-of-play line at once. Pure and light, so the
 * client component can use it without pulling in the demo match.
 */

export interface ScorePoint {
  clock_s: number;
  own: number;
  opp: number;
}

export const MATCH_SECONDS = 3600;

/** The score at second s of the match (the last goal at or before s). */
export function scoreAt(score: readonly ScorePoint[], s: number): ScorePoint {
  let cur: ScorePoint = score[0] ?? { clock_s: 0, own: 0, opp: 0 };
  for (const p of score) if (p.clock_s <= s) cur = p;
  return cur;
}

/** How many goals have fallen by second s; the video flashes each time this grows (U36). */
export function goalsBy(score: readonly ScorePoint[], s: number): number {
  return score.filter((p) => p.clock_s <= s && p.own + p.opp > 0).length;
}

/** Who scored the n-th goal (1-based), from the step in the score. */
export function scorerOf(score: readonly ScorePoint[], n: number): "own" | "opp" | null {
  const goals = score.filter((p) => p.own + p.opp > 0);
  const g = goals[n - 1];
  if (!g) return null;
  const before = goals[n - 2] ?? { own: 0, opp: 0 };
  return g.own > before.own ? "own" : "opp";
}

/** The match clock at second s, as on the video: «34:12», at the end «60:00». */
export function matchClock(s: number): string {
  const v = Math.floor(Math.max(0, Math.min(MATCH_SECONDS, s)));
  return `${Math.floor(v / 60)}:${String(v % 60).padStart(2, "0")}`;
}

/**
 * The blurred hall video is the hero film's still, moved by the match clock: the camera follows
 * the play from one goal to the other and back, seven times over the match, and slowly closes in.
 * At the end (and so with reduced motion and without JavaScript) it rests centred.
 */
export function videoPan(s: number): { scale: number; x: number; y: number } {
  const p = Math.max(0, Math.min(1, s / MATCH_SECONDS));
  const round = (v: number) => (Math.abs(v) < 1e-6 ? 0 : Math.round(v * 1000) / 1000);
  return {
    scale: round(1.12 - 0.04 * p),
    x: round(Math.sin(p * Math.PI * 2 * 7) * 3.2),
    y: round(Math.sin(p * Math.PI * 2 * 3) * 0.8),
  };
}
