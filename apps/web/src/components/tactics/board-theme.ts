/** Colours and drawing helpers of the tactics board (kept apart from the component so unit tests can import them). */

/**
 * The board's own colours (K23): a light floor with ink lines, so the board reads on a phone in the
 * sun and on a projector; never the dark court of the match screens. Own players blue with white
 * numbers, opponents orange with ink numbers: they differ in hue and in lightness, so they stay apart
 * for every common colour-vision deficiency and in black and white. Every mark has an ink rim
 * (non-text contrast 3:1 against any floor colour). Contrast is checked in board-theme.test.ts.
 */
export const BOARD_THEME = {
  surround: "#d3d9de",
  floor: "#f7f5ef",
  goalArea: "#d6e4f2",
  line: "#17191c",
  own: "#1747c4",
  ownText: "#ffffff",
  opp: "#f39a3a",
  oppText: "#17191c",
  rim: "#17191c",
  ball: "#ffd23c",
  select: "#ffd23c",
  cone: "#ffffff",
} as const;

export const distToSegment = (p: [number, number], a: readonly [number, number], b: readonly [number, number]) => {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const l2 = dx * dx + dy * dy || 1;
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2));
  return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
};

/** Ramer-Douglas-Peucker: a drawn run as at most `max` points (the API takes 12) */
export function simplify(points: [number, number][], tolerance = 0.35, max = 12): [number, number][] {
  if (points.length <= 2) return points;
  const rdp = (pts: [number, number][], tol: number): [number, number][] => {
    if (pts.length <= 2) return pts;
    let idx = 0;
    let best = 0;
    for (let i = 1; i < pts.length - 1; i++) {
      const d = distToSegment(pts[i]!, pts[0]!, pts[pts.length - 1]!);
      if (d > best) {
        best = d;
        idx = i;
      }
    }
    if (best <= tol) return [pts[0]!, pts[pts.length - 1]!];
    return [...rdp(pts.slice(0, idx + 1), tol).slice(0, -1), ...rdp(pts.slice(idx), tol)];
  };
  let tol = tolerance;
  let out = rdp(points, tol);
  while (out.length > max) out = rdp(points, (tol *= 1.5));
  return out;
}
