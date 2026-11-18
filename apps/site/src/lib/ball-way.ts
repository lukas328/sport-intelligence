/**
 * The ball's way through the steps of «So funktioniert es» (components/ball-run.tsx): from ball to
 * ball, each leg an S that leaves one ball straight down and arrives at the next from straight
 * above, so the way only ever runs down the page (the ball can follow the screen's middle).
 */
export type XY = readonly [number, number];

/**
 * Where the ball is (its height on the way) when the screen's middle is at `m`: at step i's ball
 * while the middle of step i's row (`rows[i]`) is in the middle, in between in proportion, and held
 * at the first and the last ball before and after.
 */
export function ballY(rows: readonly number[], pts: readonly XY[], m: number): number {
  const n = Math.min(rows.length, pts.length);
  if (!n) return m;
  if (m <= rows[0]!) return pts[0]![1];
  for (let i = 1; i < n; i++) {
    if (m <= rows[i]!) {
      const t = (m - rows[i - 1]!) / Math.max(1, rows[i]! - rows[i - 1]!);
      return pts[i - 1]![1] + t * (pts[i]![1] - pts[i - 1]![1]);
    }
  }
  return pts[n - 1]![1];
}

export function ballWay(pts: readonly XY[]): string {
  if (!pts.length) return "";
  const f = (v: number) => v.toFixed(1);
  let d = `M${f(pts[0]![0])} ${f(pts[0]![1])}`;
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1]!;
    const [x1, y1] = pts[i]!;
    const k = Math.max(0, y1 - y0) * 0.5;
    d += `C${f(x0)} ${f(y0 + k)} ${f(x1)} ${f(y1 - k)} ${f(x1)} ${f(y1)}`;
  }
  return d;
}
