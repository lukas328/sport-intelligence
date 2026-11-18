/**
 * Court calibration from clicked court lines and named points (manual calibration, line mode).
 *
 * The coach picks a court line (sidelines, goal lines, centre line, 6 m and 9 m lines) and clicks
 * two or three spots anywhere on it in the hall image; named points (corners, post feet, marks)
 * may be added. The court -> image homography is fitted to both: a point by its distance to the
 * projected point, a line click by its distance to the projected line, arcs included.
 *
 * The same method as the API's fit (packages/vision courtclicks.py): the linear equations (a point
 * gives two, a click on a straight line one) leave up to three directions open on a pan end; these
 * are searched on a grid and refined (Nelder-Mead) for the court that explains all clicks, then a
 * robust least-squares fit (soft L1, Levenberg-Marquardt) from the best starts. The same
 * thresholds decide whether the clicks agree with one court, so «Speichern» is offered only for
 * clicks the server takes. Here it draws the court live while the coach clicks.
 */
import type { Homography } from "@/lib/spotlight";

export type Pt = [number, number];

/** The nine court lines a coach can click, in the order of the keys 1 to 9. */
export const LINE_NAMES = [
  "side_near",
  "side_far",
  "goal_left",
  "goal_right",
  "centre",
  "six_left",
  "six_right",
  "nine_left",
  "nine_right",
] as const;
export type LineName = (typeof LINE_NAMES)[number];

/** Named points offered in the advanced mode (corners, centre line ends, post feet, 7 m marks,
 * substitution marks), names as the API knows them. */
export const POINT_NAMES = [
  "corner_bl",
  "corner_tl",
  "corner_br",
  "corner_tr",
  "center_bottom",
  "center_top",
  "post_left_low",
  "post_left_high",
  "post_right_low",
  "post_right_high",
  "penalty_mark_left",
  "penalty_mark_right",
  "subst_left_low",
  "subst_right_low",
  "subst_left_high",
  "subst_right_high",
] as const;
export type PointName = (typeof POINT_NAMES)[number];

export interface CourtLine {
  kind: "line" | "arc";
  /** court metres: the two ends of a straight line, or a polyline along an arc */
  court: Pt[];
}

/** Court geometry for the fit: lines and named points in metres (x 0 to 40 from the left goal
 * line, y 0 to 20 from the near sideline). The API serves the same model (court-model). */
export interface CourtModel {
  lines: Record<string, CourtLine>;
  points: Record<string, Pt>;
}

const FT = Math.sqrt(81 - 8.5 * 8.5); // where the 9 m line meets the sidelines

/** Goal area (r = 6) or free-throw line (r = 9) at the goal line x = cx (sx = +1: left goal). */
function arc(cx: number, sx: number, r: number): Pt[] {
  const out: Pt[] = [];
  for (let a = 0; a <= 90; a += 1) {
    const t = (a * Math.PI) / 180;
    out.push([cx + sx * r * Math.sin(t), 8.5 - r * Math.cos(t)]);
  }
  for (let a = 90; a >= 0; a -= 1) {
    const t = (a * Math.PI) / 180;
    out.push([cx + sx * r * Math.sin(t), 11.5 + r * Math.cos(t)]);
  }
  return out.filter((p) => p[1] >= 0 && p[1] <= 20);
}

/** The model built here from the court rules: used while the API does not serve one. */
export const LOCAL_COURT_MODEL: CourtModel = {
  lines: {
    side_near: { kind: "line", court: [[0, 0], [40, 0]] },
    side_far: { kind: "line", court: [[0, 20], [40, 20]] },
    goal_left: { kind: "line", court: [[0, 0], [0, 20]] },
    goal_right: { kind: "line", court: [[40, 0], [40, 20]] },
    centre: { kind: "line", court: [[20, 0], [20, 20]] },
    six_left: { kind: "arc", court: arc(0, 1, 6) },
    six_right: { kind: "arc", court: arc(40, -1, 6) },
    nine_left: { kind: "arc", court: arc(0, 1, 9) },
    nine_right: { kind: "arc", court: arc(40, -1, 9) },
  },
  points: {
    corner_bl: [0, 0],
    corner_tl: [0, 20],
    corner_br: [40, 0],
    corner_tr: [40, 20],
    center_bottom: [20, 0],
    center_top: [20, 20],
    center: [20, 10],
    post_left_low: [0, 8.5],
    post_left_high: [0, 11.5],
    post_right_low: [40, 8.5],
    post_right_high: [40, 11.5],
    goal_area_left_low: [0, 2.5],
    goal_area_left_high: [0, 17.5],
    goal_area_right_low: [40, 2.5],
    goal_area_right_high: [40, 17.5],
    goal_area_left_front_low: [6, 8.5],
    goal_area_left_front_high: [6, 11.5],
    goal_area_right_front_low: [34, 8.5],
    goal_area_right_front_high: [34, 11.5],
    free_throw_left_front_low: [9, 8.5],
    free_throw_left_front_high: [9, 11.5],
    free_throw_right_front_low: [31, 8.5],
    free_throw_right_front_high: [31, 11.5],
    free_throw_left_side_low: [FT, 0],
    free_throw_left_side_high: [FT, 20],
    free_throw_right_side_low: [40 - FT, 0],
    free_throw_right_side_high: [40 - FT, 20],
    penalty_mark_left: [7, 10],
    penalty_mark_right: [33, 10],
    gk_line_left: [4, 10],
    gk_line_right: [36, 10],
    subst_left_low: [15.5, 0],
    subst_right_low: [24.5, 0],
    subst_left_high: [15.5, 20],
    subst_right_high: [24.5, 20],
  },
};

/** The thresholds of the API (courtclicks.py): 8 unknowns and a check, median and worst click. */
export const MIN_EQUATIONS = 10;
export const MAX_MEDIAN_PX = 5;
export const MAX_CLICK_PX = 20;
export const DROP_PX = 15;
/** The court is drawn from this many equations on (exact, not yet checkable). */
export const PREVIEW_EQUATIONS = 8;

export interface Clicks {
  points: Record<string, Pt>;
  lines: Record<string, Pt[]>;
}

/** A click: a named point, or the index-th click on a line. */
export type ClickRef = { kind: "point"; name: string } | { kind: "line"; name: string; index: number };

export function equations(c: Clicks): number {
  return 2 * Object.keys(c.points).length + Object.values(c.lines).reduce((s, l) => s + l.length, 0);
}

function items(c: Clicks): number {
  return Object.keys(c.points).length + Object.values(c.lines).filter((l) => l.length > 0).length;
}

/** The clicks in a fixed order: points first, then each line's clicks (as the API counts them). */
export function clickRefs(c: Clicks): ClickRef[] {
  return [
    ...Object.keys(c.points).map((name): ClickRef => ({ kind: "point", name })),
    ...Object.entries(c.lines).flatMap(([name, l]) => l.map((_, index): ClickRef => ({ kind: "line", name, index }))),
  ];
}

// ---- small linear algebra (3 x 3 as a flat row-major array) ----------------------------------

type M3 = number[];

function inv3(m: M3): M3 | null {
  const [a, b, c, d, e, f, g, h, i] = m as [number, number, number, number, number, number, number, number, number];
  const A = e * i - f * h;
  const B = -(d * i - f * g);
  const C = d * h - e * g;
  const det = a * A + b * B + c * C;
  if (!Number.isFinite(det) || Math.abs(det) < 1e-15) return null;
  return [A / det, -(b * i - c * h) / det, (b * f - c * e) / det, B / det, (a * i - c * g) / det, -(a * f - c * d) / det, C / det, -(a * h - b * g) / det, (a * e - b * d) / det];
}

function mul3(p: M3, q: M3): M3 {
  const r: M3 = [];
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) r.push(p[i * 3]! * q[j]! + p[i * 3 + 1]! * q[3 + j]! + p[i * 3 + 2]! * q[6 + j]!);
  return r;
}

const flat = (h: Homography): M3 => [...h[0]!, ...h[1]!, ...h[2]!];
const nested = (m: M3): Homography => [m.slice(0, 3), m.slice(3, 6), m.slice(6, 9)];

/** Court metres -> image pixels (homogeneous: w <= 0 lies behind the camera). */
function project(m: M3, x: number, y: number): [number, number, number] {
  const w = m[6]! * x + m[7]! * y + m[8]!;
  return [(m[0]! * x + m[1]! * y + m[2]!) / w, (m[3]! * x + m[4]! * y + m[5]!) / w, w];
}

/** Image pixels -> court metres with the inverse homography; null when it has none. */
export function toCourt(h: Homography, p: Pt): Pt | null {
  const inv = inv3(flat(h));
  if (!inv) return null;
  const [x, y, w] = project(inv, p[0], p[1]);
  return Number.isFinite(x) && Number.isFinite(y) && Math.abs(w) > 1e-12 ? [x, y] : null;
}

/** Symmetric eigen decomposition (Jacobi): eigenvectors, smallest eigenvalue first. */
function jacobiEigen(a0: number[][]): number[][] {
  const n = a0.length;
  const a = a0.map((r) => r.slice());
  const v = Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => (i === j ? 1 : 0)));
  for (let sweep = 0; sweep < 60; sweep++) {
    let off = 0;
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) off += a[i]![j]! ** 2;
    if (off < 1e-22) break;
    for (let p = 0; p < n; p++)
      for (let q = p + 1; q < n; q++) {
        if (Math.abs(a[p]![q]!) < 1e-300) continue;
        const th = (a[q]![q]! - a[p]![p]!) / (2 * a[p]![q]!);
        const t = Math.sign(th || 1) / (Math.abs(th) + Math.sqrt(th * th + 1));
        const c = 1 / Math.sqrt(t * t + 1);
        const s = t * c;
        for (let k = 0; k < n; k++) {
          const akp = a[k]![p]!;
          const akq = a[k]![q]!;
          a[k]![p] = c * akp - s * akq;
          a[k]![q] = s * akp + c * akq;
        }
        for (let k = 0; k < n; k++) {
          const apk = a[p]![k]!;
          const aqk = a[q]![k]!;
          a[p]![k] = c * apk - s * aqk;
          a[q]![k] = s * apk + c * aqk;
        }
        for (let k = 0; k < n; k++) {
          const vkp = v[k]![p]!;
          const vkq = v[k]![q]!;
          v[k]![p] = c * vkp - s * vkq;
          v[k]![q] = s * vkp + c * vkq;
        }
      }
  }
  const idx = [...Array(n).keys()].sort((i, j) => a[i]![i]! - a[j]![j]!);
  return idx.map((i) => v.map((row) => row[i]!));
}

/** Gaussian elimination with partial pivoting; null when singular. */
function solve(a: number[][], b: number[]): number[] | null {
  const n = b.length;
  const m = a.map((r, i) => [...r, b[i]!]);
  for (let c = 0; c < n; c++) {
    let p = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(m[r]![c]!) > Math.abs(m[p]![c]!)) p = r;
    [m[c], m[p]] = [m[p]!, m[c]!];
    if (Math.abs(m[c]![c]!) < 1e-14) return null;
    for (let r = 0; r < n; r++)
      if (r !== c) {
        const f = m[r]![c]! / m[c]![c]!;
        for (let k = c; k <= n; k++) m[r]![k]! -= f * m[c]![k]!;
      }
  }
  return m.map((r, i) => r[n]! / r[i]!);
}

function nelderMead(f: (x: number[]) => number, x0: number[], step: number, iters: number): [number[], number] {
  const n = x0.length;
  let pts = [x0.slice()];
  for (let i = 0; i < n; i++) {
    const p = x0.slice();
    p[i]! += step;
    pts.push(p);
  }
  let vals = pts.map(f);
  for (let it = 0; it < iters; it++) {
    const ord = [...pts.keys()].sort((i, j) => vals[i]! - vals[j]!);
    pts = ord.map((i) => pts[i]!);
    vals = ord.map((i) => vals[i]!);
    if (Math.abs(vals[n]! - vals[0]!) < 1e-3 && Math.max(...pts.map((p) => Math.max(...p.map((v, k) => Math.abs(v - pts[0]![k]!))))) < 1e-5) break;
    const c = new Array<number>(n).fill(0);
    for (let i = 0; i < n; i++) for (let k = 0; k < n; k++) c[k]! += pts[i]![k]! / n;
    const at = (t: number) => c.map((v, k) => v + t * (pts[n]![k]! - v));
    const r = at(-1);
    const fr = f(r);
    if (fr < vals[0]!) {
      const e = at(-2);
      const fe = f(e);
      if (fe < fr) [pts[n], vals[n]] = [e, fe];
      else [pts[n], vals[n]] = [r, fr];
    } else if (fr < vals[n - 1]!) [pts[n], vals[n]] = [r, fr];
    else {
      const k = at(0.5);
      const fk = f(k);
      if (fk < vals[n]!) [pts[n], vals[n]] = [k, fk];
      else
        for (let i = 1; i <= n; i++) {
          pts[i] = pts[i]!.map((v, j) => pts[0]![j]! + 0.5 * (v - pts[0]![j]!));
          vals[i] = f(pts[i]!);
        }
    }
  }
  const b = vals.indexOf(Math.min(...vals));
  return [pts[b]!, vals[b]!];
}

// ---- the court model as dense polylines -----------------------------------------------------

interface Prepared {
  model: CourtModel;
  /** arcs every 10 cm (for the fit), every 30 cm (to rank starts) */
  dense: Record<string, Pt[]>;
  coarse: Record<string, Pt[]>;
}

function densify(pl: Pt[], step: number): Pt[] {
  const out: Pt[] = [];
  for (let s = 0; s < pl.length - 1; s++) {
    const [a, b] = [pl[s]!, pl[s + 1]!];
    const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / step));
    for (let i = 0; i < n; i++) out.push([a[0] + ((b[0] - a[0]) * i) / n, a[1] + ((b[1] - a[1]) * i) / n]);
  }
  out.push(pl[pl.length - 1]!);
  return out;
}

const prepared = new WeakMap<CourtModel, Prepared>();

function prepare(model: CourtModel): Prepared {
  let p = prepared.get(model);
  if (!p) {
    const dense: Record<string, Pt[]> = {};
    const coarse: Record<string, Pt[]> = {};
    for (const [name, line] of Object.entries(model.lines)) {
      if (line.kind !== "arc") continue;
      dense[name] = densify(line.court, 0.1);
      coarse[name] = dense[name]!.filter((_, i, a) => i % 3 === 0 || i === a.length - 1);
    }
    p = { model, dense, coarse };
    prepared.set(model, p);
  }
  return p;
}

/** Distance from (px, py) to the segment a-b. */
function segDist(px: number, py: number, ax: number, ay: number, bx: number, by: number): number {
  const dx = bx - ax;
  const dy = by - ay;
  const l2 = dx * dx + dy * dy;
  const t = l2 > 0 ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / l2)) : 0;
  return Math.hypot(px - ax - t * dx, py - ay - t * dy);
}

const FAR = 1e6;

/** Distance of every click to the projected court, in clickRefs order (points first). A straight
 * court line stays straight in the image (exact distance to it); an arc: distance to its
 * projected polyline, parts behind the camera left out. */
function residuals(m: M3, c: Clicks, prep: Prepared, coarse = false): number[] {
  const out: number[] = [];
  for (const [name, p] of Object.entries(c.points)) {
    const k = prep.model.points[name];
    if (!k) {
      out.push(FAR);
      continue;
    }
    const q = project(m, k[0], k[1]);
    const d = Math.hypot(q[0] - p[0], q[1] - p[1]);
    out.push(Number.isFinite(d) ? d : FAR);
  }
  for (const [name, clicks] of Object.entries(c.lines)) {
    const line = prep.model.lines[name];
    if (!line) {
      out.push(...clicks.map(() => FAR));
      continue;
    }
    if (line.kind === "line") {
      const a = project(m, line.court[0]![0], line.court[0]![1]);
      const b = project(m, line.court[1]![0], line.court[1]![1]);
      const dx = b[0] - a[0];
      const dy = b[1] - a[1];
      const n = Math.hypot(dx, dy);
      for (const p of clicks) {
        const d = Math.abs(dx * (p[1] - a[1]) - dy * (p[0] - a[0])) / n;
        out.push(Number.isFinite(d) && n > 1e-9 ? d : FAR);
      }
      continue;
    }
    const curve = (coarse ? prep.coarse : prep.dense)[name]!;
    const proj = curve.map((q) => project(m, q[0], q[1]));
    const sgn = Math.sign(project(m, 20, 10)[2]) || 1;
    for (const p of clicks) {
      let best = Infinity;
      for (let i = 0; i < proj.length - 1; i++) {
        const a = proj[i]!;
        const b = proj[i + 1]!;
        if (a[2] * sgn <= 0 || b[2] * sgn <= 0) continue;
        const d = segDist(p[0], p[1], a[0], a[1], b[0], b[1]);
        if (d < best) best = d;
      }
      out.push(Number.isFinite(best) ? best : FAR);
    }
  }
  return out;
}

/** Mean click distance, each capped at 50 px (a median would let a wrong court explain half). */
function cost(m: M3, c: Clicks, prep: Prepared): number {
  const r = residuals(m, c, prep, true);
  return r.length ? r.reduce((s, v) => s + Math.min(v, 50), 0) / r.length : 1e9;
}

/** Start homographies (flat) from the linear equations and a search over the open directions. */
function starts(c: Clicks, size: [number, number], prep: Prepared, keep = 5): M3[] {
  const [w, hgt] = size;
  const T: M3 = [2 / w, 0, -1, 0, 2 / w, -hgt / w, 0, 0, 1];
  const C: M3 = [1 / 20, 0, -1, 0, 1 / 20, -0.5, 0, 0, 1];
  const tn = (p: Pt) => [T[0]! * p[0] + T[2]!, T[4]! * p[1] + T[5]!, 1] as const;
  const cn = (p: Pt) => [C[0]! * p[0] + C[2]!, C[4]! * p[1] + C[5]!, 1] as const;
  const rows: number[][] = [];
  for (const [name, p] of Object.entries(c.points)) {
    const k = prep.model.points[name];
    if (!k) continue;
    const x = cn(k);
    const u = tn(p);
    rows.push([x[2] * u[0], x[2] * u[1], x[2] * u[2], 0, 0, 0, -x[0] * u[0], -x[0] * u[1], -x[0] * u[2]]);
    rows.push([0, 0, 0, x[2] * u[0], x[2] * u[1], x[2] * u[2], -x[1] * u[0], -x[1] * u[1], -x[1] * u[2]]);
  }
  for (const [name, clicks] of Object.entries(c.lines)) {
    const line = prep.model.lines[name];
    if (!line || line.kind !== "line") continue; // arcs only through the search below
    const a = cn(line.court[0]!);
    const b = cn(line.court[1]!);
    const l = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]] as const;
    for (const p of clicks) {
      const u = tn(p);
      rows.push([l[0] * u[0], l[0] * u[1], l[0] * u[2], l[1] * u[0], l[1] * u[1], l[1] * u[2], l[2] * u[0], l[2] * u[1], l[2] * u[2]]);
    }
  }
  if (rows.length < 4) return [];
  const ata = Array.from({ length: 9 }, (_, i) => Array.from({ length: 9 }, (_, j) => rows.reduce((s, r) => s + r[i]! * r[j]!, 0)));
  const V = jacobiEigen(ata);
  const Ti = inv3(T)!;
  const toH = (g: M3): M3 | null => {
    const gi = inv3(g);
    if (!gi) return null;
    const h = mul3(mul3(Ti, gi), C);
    return Math.abs(h[8]!) > 1e-12 ? h.map((v) => v / h[8]!) : null;
  };
  const found: [number, M3][] = [];
  const h1 = toH(V[0]!);
  if (h1) found.push([cost(h1, c, prep), h1]);
  // how many directions the clicks leave open is not clear-cut with noisy clicks: two and three
  // open directions are searched too, the clicks decide
  for (const dim of [2, 3] as const) {
    const gOf = (a: number[]): M3 =>
      dim === 2
        ? V[0]!.map((v, k) => Math.cos(a[0]!) * v + Math.sin(a[0]!) * V[1]![k]!)
        : V[0]!.map((v, k) => Math.cos(a[0]!) * v + Math.sin(a[0]!) * (Math.cos(a[1]!) * V[1]![k]! + Math.sin(a[1]!) * V[2]![k]!));
    const f = (a: number[]) => {
      const h = toH(gOf(a));
      return h ? cost(h, c, prep) : 1e9;
    };
    const grid: number[][] = [];
    if (dim === 2) for (let i = 0; i < 120; i++) grid.push([(i * Math.PI) / 120]);
    else for (let i = 0; i < 30; i++) for (let j = 0; j < 60; j++) grid.push([(i * Math.PI) / 30, (j * 2 * Math.PI) / 60]);
    const best = grid
      .map((a) => [f(a), a] as const)
      .sort((x, y) => x[0] - y[0])
      .slice(0, 2 * keep);
    for (const [, a0] of best) {
      const [a, v] = nelderMead(f, a0, dim === 2 ? 0.01 : 0.03, 400);
      const h = toH(gOf(a));
      if (h) found.push([v, h]);
    }
  }
  found.sort((x, y) => x[0] - y[0]);
  const out: M3[] = [];
  for (const [, h] of found) {
    const mx = Math.max(...h.map(Math.abs));
    if (out.every((o) => Math.max(...h.map((v, k) => Math.abs(v - o[k]!))) > 1e-3 * Math.max(mx, ...o.map(Math.abs)))) out.push(h);
    if (out.length === keep) break;
  }
  return out;
}

// court metres to roughly [-1, 1]: the solver then sees well scaled parameters
const NORM: M3 = [1 / 20, 0, -1, 0, 1 / 10, -1, 0, 0, 1];
const NORM_INV = inv3(NORM)!;
const F_SCALE = 5; // px: soft L1 like the API

function robustCost(r: number[]): number {
  return r.reduce((s, v) => s + F_SCALE * F_SCALE * 2 * (Math.sqrt(1 + (v / F_SCALE) ** 2) - 1), 0);
}

/** Robust least squares (soft L1, Levenberg-Marquardt by reweighting) from h0. */
function refine(h0: M3, c: Clicks, prep: Prepared, maxIter = 60): { h: M3; r: number[]; cost: number } {
  // H = A (I + D) N with A the start in normalised court units: D starts at zero
  let a = mul3(h0, NORM_INV);
  const amax = Math.max(...a.map(Math.abs));
  a = a.map((v) => v / amax);
  const hom = (d: number[]): M3 => mul3(mul3(a, [1 + d[0]!, d[1]!, d[2]!, d[3]!, 1 + d[4]!, d[5]!, d[6]!, d[7]!, 1]), NORM);
  let d = new Array<number>(8).fill(0);
  let r = residuals(hom(d), c, prep);
  let best = robustCost(r);
  let lam = 1e-3;
  for (let it = 0; it < maxIter; it++) {
    const wts = r.map((v) => (1 + (v / F_SCALE) ** 2) ** -0.25);
    const rw = r.map((v, i) => v * wts[i]!);
    const J: number[][] = [];
    for (let k = 0; k < 8; k++) {
      const e = 1e-6;
      const dp = d.slice();
      dp[k]! += e;
      const rp = residuals(hom(dp), c, prep);
      J.push(rp.map((v, i) => ((v - r[i]!) / e) * wts[i]!));
    }
    const A = Array.from({ length: 8 }, (_, i) => Array.from({ length: 8 }, (_, j) => J[i]!.reduce((s, v, m) => s + v * J[j]![m]!, 0)));
    const g = Array.from({ length: 8 }, (_, i) => -J[i]!.reduce((s, v, m) => s + v * rw[m]!, 0));
    let improved = false;
    for (let tries = 0; tries < 8 && !improved; tries++) {
      const Ad = A.map((row, i) => row.map((v, j) => v + (i === j ? lam * (A[i]![i]! + 1e-9) : 0)));
      const step = solve(Ad, g);
      if (!step) {
        lam *= 10;
        continue;
      }
      const dn = d.map((v, k) => v + step[k]!);
      const rn = residuals(hom(dn), c, prep);
      const cn = robustCost(rn);
      if (cn < best) {
        const gain = best - cn;
        [d, r, best] = [dn, rn, cn];
        lam = Math.max(lam / 3, 1e-9);
        improved = true;
        if (gain < 1e-9 * Math.max(1, best)) it = maxIter;
      } else lam *= 10;
    }
    if (!improved) break;
  }
  const h = hom(d);
  return { h: h.map((v) => v / h[8]!), r, cost: best };
}

export type FitStatus =
  /** not enough clicks to draw a court */
  | "too-few"
  /** a court is drawn, but too few equations to check the clicks against each other */
  | "need-more"
  /** no court explains the clicks */
  | "no-court"
  /** fitted, but the clicks do not agree with one court */
  | "disagree"
  /** passes the server's thresholds */
  | "ok";

export interface ClickFit {
  status: FitStatus;
  homography: Homography | null;
  /** per click in clickRefs order (dropped clicks included, measured against the court) */
  residualPx: number[];
  medianPx: number | null;
  maxPx: number | null;
  /** clicks left out as off-line (a click that snapped to a neighbouring line) */
  dropped: ClickRef[];
  /** the click that agrees least with the court (not dropped) */
  worst: (ClickRef & { px: number }) | null;
  equations: number;
}

const median = (v: number[]) => {
  const s = [...v].sort((a, b) => a - b);
  const n = s.length;
  return n === 0 ? 0 : n % 2 ? s[(n - 1) / 2]! : (s[n / 2 - 1]! + s[n / 2]!) / 2;
};

function without(c: Clicks, ref: ClickRef): Clicks {
  if (ref.kind === "point") {
    const points = { ...c.points };
    delete points[ref.name];
    return { points, lines: c.lines };
  }
  const lines: Record<string, Pt[]> = {};
  for (const [n, l] of Object.entries(c.lines)) {
    const kept = n === ref.name ? l.filter((_, k) => k !== ref.index) : l;
    if (kept.length) lines[n] = kept;
  }
  return { points: c.points, lines };
}

const sameRef = (a: ClickRef, b: ClickRef) => a.kind === b.kind && a.name === b.name && (a.kind === "point" || (b.kind === "line" && a.index === b.index));

/**
 * The court through the clicks (image pixels in an image of `size`) and how well each click
 * agrees with it. `from`: a homography to start from (while a click is dragged: fast, no search).
 */
export function fitClicks(clicks: Clicks, size: [number, number], model: CourtModel = LOCAL_COURT_MODEL, from?: Homography | null): ClickFit {
  const c: Clicks = {
    points: Object.fromEntries(Object.entries(clicks.points).filter(([n]) => n in model.points)),
    lines: Object.fromEntries(Object.entries(clicks.lines).filter(([n, l]) => n in model.lines && l.length > 0)),
  };
  const nEq = equations(c);
  const empty: ClickFit = { status: "too-few", homography: null, residualPx: [], medianPx: null, maxPx: null, dropped: [], worst: null, equations: nEq };
  if (nEq < PREVIEW_EQUATIONS || items(c) < 3) return empty;
  const prep = prepare(model);
  const st = from ? [flat(from)] : starts(c, size, prep);
  if (!st.length) return { ...empty, status: "no-court" };
  let best: { h: M3; r: number[]; cost: number } | null = null;
  for (const h0 of st.slice(0, 2)) {
    const f = refine(h0, c, prep, from ? 15 : 60);
    if (!best || f.cost < best.cost) best = f;
  }
  let { h, r } = best!;
  if (!r.every(Number.isFinite) || !h.every(Number.isFinite)) return { ...empty, status: "no-court" };
  if (nEq < MIN_EQUATIONS) {
    return { status: "need-more", homography: nested(h), residualPx: r, medianPx: median(r), maxPx: Math.max(...r), dropped: [], worst: null, equations: nEq };
  }
  // a click that snapped to a neighbouring line: drop the worst click beyond 15 px and fit again,
  // one at a time, at most a fifth of the clicks
  const all = clickRefs(c);
  let cur = c;
  let orig = all.slice(); // the original click of each current one
  const dropped: ClickRef[] = [];
  const maxDrop = Math.max(1, Math.floor(r.length / 5));
  const bad = (v: number[]) => median(v) > MAX_MEDIAN_PX || Math.max(...v) > MAX_CLICK_PX;
  while (bad(r) && dropped.length < maxDrop && Math.max(...r) > DROP_PX) {
    const i = r.indexOf(Math.max(...r));
    const trial = without(cur, clickRefs(cur)[i]!);
    if (equations(trial) < MIN_EQUATIONS) break;
    cur = trial;
    dropped.push(orig[i]!);
    orig = orig.filter((_, k) => k !== i);
    ({ h, r } = refine(h, cur, prep, 30));
  }
  const med = median(r);
  const mx = Math.max(...r);
  const H = nested(h);
  const full = residuals(h, c, prep);
  const kept = all.map((ref, i) => ({ ref, px: full[i]! })).filter((x) => !dropped.some((dr) => sameRef(dr, x.ref)));
  const w = kept.reduce((m, x) => (x.px > m.px ? x : m), kept[0]!);
  return {
    status: med > MAX_MEDIAN_PX || mx > MAX_CLICK_PX ? "disagree" : "ok",
    homography: H,
    residualPx: full,
    medianPx: med,
    maxPx: mx,
    dropped,
    worst: w ? { ...w.ref, px: w.px } : null,
    equations: nEq,
  };
}

/**
 * The fitted court as named points for the API's points endpoint (until it takes line clicks):
 * a 3 x 3 grid over the part of the court the clicks cover. The fit is exact through these
 * points, so the server's point fit gives back the same court. Null when the court cannot be
 * expressed so (behind the camera, far outside the image).
 */
export function courtAsPoints(h: Homography, clicks: Clicks): { image: Pt; court: Pt }[] | null {
  const image = [...Object.values(clicks.points), ...Object.values(clicks.lines).flat()];
  const court = image.map((p) => toCourt(h, p)).filter((p): p is Pt => p != null);
  if (court.length < 3) return null;
  const clampX = (v: number) => Math.max(0, Math.min(40, v));
  const clampY = (v: number) => Math.max(0, Math.min(20, v));
  let [x0, x1] = [clampX(Math.min(...court.map((p) => p[0]))), clampX(Math.max(...court.map((p) => p[0])))];
  let [y0, y1] = [clampY(Math.min(...court.map((p) => p[1]))), clampY(Math.max(...court.map((p) => p[1])))];
  // a spread of at least 6 x 6 m keeps the point fit well conditioned
  if (x1 - x0 < 6) [x0, x1] = [clampX((x0 + x1) / 2 - 3), clampX((x0 + x1) / 2 + 3)];
  if (y1 - y0 < 6) [y0, y1] = [clampY((y0 + y1) / 2 - 3), clampY((y0 + y1) / 2 + 3)];
  const m = flat(h);
  const sgn = Math.sign(project(m, 20, 10)[2]) || 1;
  const out: { image: Pt; court: Pt }[] = [];
  for (const fx of [0, 0.5, 1])
    for (const fy of [0, 0.5, 1]) {
      const cp: Pt = [x0 + fx * (x1 - x0), y0 + fy * (y1 - y0)];
      const q = project(m, cp[0], cp[1]);
      if (q[2] * sgn <= 0 || !Number.isFinite(q[0]) || !Number.isFinite(q[1]) || Math.abs(q[0]) > 20_000 || Math.abs(q[1]) > 20_000) continue;
      out.push({ image: [Math.round(q[0] * 100) / 100, Math.round(q[1] * 100) / 100], court: [Math.round(cp[0] * 1000) / 1000, Math.round(cp[1] * 1000) / 1000] });
    }
  return out.length >= 4 ? out : null;
}

/** A court line as an image polyline (parts behind the camera split it), for drawing. */
export function linePolylines(h: Homography, court: Pt[], step = 0.5): Pt[][] {
  const m = flat(h);
  const sgn = Math.sign(project(m, 20, 10)[2]) || 1;
  const out: Pt[][] = [];
  let cur: Pt[] = [];
  for (const [x, y] of densify(court, step)) {
    const q = project(m, x, y);
    if (q[2] * sgn > 0 && Math.abs(q[0]) < 1e5 && Math.abs(q[1]) < 1e5) cur.push([q[0], q[1]]);
    else if (cur.length) {
      if (cur.length > 1) out.push(cur);
      cur = [];
    }
  }
  if (cur.length > 1) out.push(cur);
  return out;
}
