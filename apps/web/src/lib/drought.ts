/**
 * The longest phase without an own goal, in seconds. Without a span the server's value counts
 * from the throw-off; a video that covers only minutes a to b (span) is measured only there: from
 * its start to the first own goal, between own goals and from the last one to its end. Counted
 * from the throw-off, a clip from minute 8 had «8 min without a goal» that nobody saw (fourth
 * real-video test).
 */
export function ownDrought(points: readonly { clock_s: number; own: number }[], span: readonly [number, number] | null, server: number): number {
  if (!span) return server;
  const [from, to] = [span[0] * 60, span[1] * 60];
  const goals: number[] = [];
  for (let i = 1; i < points.length; i++) {
    const p = points[i]!;
    if (p.own > points[i - 1]!.own && p.clock_s >= from && p.clock_s <= to) goals.push(p.clock_s);
  }
  let last = from;
  let best = 0;
  for (const t of [...goals, to]) {
    best = Math.max(best, t - last);
    last = t;
  }
  return best;
}
