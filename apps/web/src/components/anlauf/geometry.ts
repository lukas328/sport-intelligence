/**
 * Court geometry for the Anlauf graphics (port of docs/design/ux-reset/assets/anlauf-feld.js).
 * Rule for every drawing: a line is a measured way. What the analysis does not measure is not
 * drawn (no ball flight, no pass lines). Confirmed is solid, estimated is dashed or lighter.
 *
 * Coordinates:
 * - court: metres on the whole court, 40 x 20, goals at x = 0 and x = 40
 * - half: one half with the goal at the top, u across (0 to 20 m), v away from the goal line
 */

export type Pt = readonly [number, number];

/** viewBox of the half court (goal at the top) */
export const HALF_BOX = [-0.6, -1.2, 21.2, 17.2] as const;

/** SVG path through points, straight segments. */
export function pathOf(pts: readonly Pt[]): string {
  return pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join("");
}

/** Catmull-Rom through measured points, n samples per segment: a display smoothing, nothing added. */
export function smooth(pts: readonly Pt[], n: number): Pt[] {
  if (pts.length < 2) return pts.slice();
  const out: Pt[] = [];
  const P = [pts[0]!, ...pts, pts[pts.length - 1]!];
  for (let i = 1; i < P.length - 2; i++) {
    const a = P[i - 1]!;
    const b = P[i]!;
    const c = P[i + 1]!;
    const e = P[i + 2]!;
    for (let k = 0; k < n; k++) {
      const t = k / n;
      const t2 = t * t;
      const t3 = t2 * t;
      const at = (j: 0 | 1) => 0.5 * (2 * b[j] + (-a[j] + c[j]) * t + (2 * a[j] - 5 * b[j] + 4 * c[j] - e[j]) * t2 + (-a[j] + 3 * b[j] - 3 * c[j] + e[j]) * t3);
      out.push([at(0), at(1)]);
    }
  }
  out.push(pts[pts.length - 1]!);
  return out;
}

/** Point at t (0 to 1) along the smoothed path. */
export function sampleAt(pts: readonly Pt[], t: number): Pt {
  const s = smooth(pts, 10);
  const n = s.length - 1;
  const f = Math.max(0, Math.min(1, t)) * n;
  const i = Math.floor(f);
  const r = f - i;
  if (i >= n) return s[n]!;
  return [s[i]![0] + (s[i + 1]![0] - s[i]![0]) * r, s[i]![1] + (s[i + 1]![1] - s[i]![1]) * r];
}

/** The way of the last `back` (share of the scene) up to t. */
export function trailOf(pts: readonly Pt[], t: number, back: number): Pt[] {
  const out: Pt[] = [];
  for (let j = 0; j <= 14; j++) {
    const tt = t - back + (back * j) / 14;
    if (tt >= 0) out.push(sampleAt(pts, tt));
  }
  return out;
}

const FADE = 0.03; // share of the scene a track takes to appear or go

/**
 * How much of a track shows at t (0 to 1): 1 while it has data, fading in and out at its ends,
 * 0 outside (real-video test F5: a track exists only while the analysis saw it). Without times
 * (a drawn demo scene) a track shows for the whole scene.
 */
export function presence(ts: readonly number[] | null | undefined, t: number): number {
  if (!ts || ts.length === 0) return 1;
  const a = ts[0]!;
  const b = ts[ts.length - 1]!;
  if (t < a - FADE || t > b + FADE) return 0;
  if (t < a) return (t - (a - FADE)) / FADE;
  if (t > b) return (b + FADE - t) / FADE;
  return 1;
}

/** Where a track is at t: by its own times when it has them, else spread over the scene. */
export function positionAt(pts: readonly Pt[], ts: readonly number[] | null | undefined, t: number): Pt {
  if (!ts || ts.length !== pts.length || pts.length === 0) return sampleAt(pts, t);
  if (t <= ts[0]!) return pts[0]!;
  const n = ts.length - 1;
  if (t >= ts[n]!) return pts[n]!;
  let i = 0;
  while (i < n - 1 && ts[i + 1]! < t) i++;
  const span = ts[i + 1]! - ts[i]!;
  const r = span > 0 ? (t - ts[i]!) / span : 0;
  return [pts[i]![0] + (pts[i + 1]![0] - pts[i]![0]) * r, pts[i]![1] + (pts[i + 1]![1] - pts[i]![1]) * r];
}

/** The way of the last `back` up to t, only where the track has data. */
export function trailAt(pts: readonly Pt[], ts: readonly number[] | null | undefined, t: number, back: number): Pt[] {
  if (!ts || ts.length !== pts.length) return trailOf(pts, t, back);
  const out: Pt[] = [];
  for (let j = 0; j <= 14; j++) {
    const tt = t - back + (back * j) / 14;
    if (tt >= 0 && tt >= ts[0]! && tt <= ts[ts.length - 1]!) out.push(positionAt(pts, ts, tt));
  }
  return out;
}

/** Court metres to the half the attack goes to (goal at x = 0 or x = 40). */
export function toHalf(p: Pt, goalAtZero: boolean): Pt {
  return goalAtZero ? [p[1], p[0]] : [20 - p[1], 40 - p[0]];
}

/** Goal area arc of radius r (6 m line, 9 m line) on the left goal of the court. */
export function goalArea(r: number): string {
  const k = Math.sqrt(Math.max(0, r * r - 8.5 * 8.5));
  const y0 = r > 8.5 ? 0 : 8.5 - r;
  const x0 = r > 8.5 ? k : 0;
  return `M${x0.toFixed(3)} ${y0.toFixed(3)} A${r} ${r} 0 0 1 ${r} 8.5 L${r} 11.5 A${r} ${r} 0 0 1 ${x0.toFixed(3)} ${(20 - y0).toFixed(3)}`;
}

/** Views of the whole court for the tactics camera. */
export const VIEWS = {
  /** our left half wide (desktop stage) */
  camL: { box: [-1.2, -1.2, 34, 22.4], turn: false },
  /** left half turned, goal at the top (phone, tiles) */
  halfB: { box: [-0.6, -1.2, 21.2, 17.2], turn: true },
  halfDeep: { box: [-0.6, -0.9, 21.2, 18.6], turn: true },
} as const satisfies Record<string, { box: readonly [number, number, number, number]; turn: boolean }>;

export type ViewName = keyof typeof VIEWS;

export function inView(view: ViewName, p: Pt): Pt {
  return VIEWS[view].turn ? [p[1], p[0]] : p;
}

/** Zone anchors on the half court, where the count of a zone stands. */
export const ZONE_AT: Record<string, Pt> = {
  la: [3.2, 4.4],
  ra: [16.8, 4.4],
  rl: [4.2, 13.6],
  rm: [10, 14.4],
  rr: [15.8, 13.6],
  kr: [10, 3.2],
  m7: [13.4, 7.6],
  gs: [10, 11.8],
};
