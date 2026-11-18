/** The run of the match as one line: the goal difference minute by minute, ours above the
 * middle, theirs below (finding A14: two running totals whose end values lay on each other). */
export function scoreFlow(points: readonly { clock_s: number; own: number; opp: number }[]) {
  const diffs = points.map((p) => p.own - p.opp);
  // at least three goals each way, so a close match does not look like a landslide
  const span = Math.max(3, ...diffs.map(Math.abs));
  const step = span <= 4 ? 1 : span <= 10 ? 2 : 5;
  const top = Math.ceil(span / step) * step;
  const grid = Array.from({ length: Math.floor(top / step) * 2 + 1 }, (_, i) => top - i * step);
  return { diffs, top, grid };
}
