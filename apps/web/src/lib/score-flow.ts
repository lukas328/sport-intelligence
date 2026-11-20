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

/**
 * The stretch the course of the match is drawn over (app review BUG-20). A match report covers the
 * whole match (null: 0 to the end). Without one, the match minutes the video covers (`span` of the
 * graphics); without a throw-off the goals carry video times, so the video's own minutes, marked
 * as such. Never 0' to 60' for an eight-minute video.
 */
export function courseOf(
  graphics: { has_report?: boolean; span?: readonly number[] | null } | null,
  kickoffMs: Record<string, number> | null | undefined,
  videoSeconds: number | null | undefined,
): { span: [number, number]; video: boolean } | null {
  if (!graphics || graphics.has_report) return null;
  if (graphics.span && graphics.span.length === 2) return { span: [graphics.span[0]!, graphics.span[1]!], video: false };
  const throwOff = Object.keys(kickoffMs ?? {}).length > 0;
  if (throwOff || !videoSeconds || videoSeconds <= 0) return null;
  return { span: [0, Math.round((videoSeconds / 60) * 100) / 100], video: true };
}
