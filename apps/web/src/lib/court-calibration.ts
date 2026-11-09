/**
 * Marking the court by hand (ADR 020): the user picks court landmarks and clicks them on the hall
 * image (panorama of a moving camera, median frame of a fixed one). The homography court -> image
 * is fitted here only for the live preview; the worker fits it again and runs the analysis.
 */
import { COURT, type Point } from "@handball/court";
import type { Homography } from "@/lib/spotlight";

export type Pt = [number, number];

/** Court landmarks in metres (x along the court from the left goal line, y from the near sideline). */
export const COURT_LANDMARKS: readonly { id: string; court: Pt }[] = [
  { id: "cornerNearLeft", court: [0, 0] },
  { id: "cornerFarLeft", court: [0, 20] },
  { id: "cornerNearRight", court: [40, 0] },
  { id: "cornerFarRight", court: [40, 20] },
  { id: "centreNear", court: [20, 0] },
  { id: "centreFar", court: [20, 20] },
  { id: "postLeftNear", court: [0, 8.5] },
  { id: "postLeftFar", court: [0, 11.5] },
  { id: "postRightNear", court: [40, 8.5] },
  { id: "postRightFar", court: [40, 11.5] },
  { id: "sixLeftNear", court: [6, 8.5] },
  { id: "sixLeftFar", court: [6, 11.5] },
  { id: "sixRightNear", court: [34, 8.5] },
  { id: "sixRightFar", court: [34, 11.5] },
  { id: "sevenLeft", court: [7, 10] },
  { id: "sevenRight", court: [33, 10] },
];

export const MIN_POINTS = 4;

/**
 * Points only along one direction (e.g. the four goal posts: two 3 m segments 40 m apart) fit
 * exactly but leave the other direction almost free; a few pixels of clicking error then stretch
 * the court. Good sets span at least half the length and half the width.
 */
export function wellSpread(court: Pt[]): boolean {
  if (court.length < MIN_POINTS) return false;
  const xs = court.map((p) => p[0]);
  const ys = court.map((p) => p[1]);
  return Math.max(...xs) - Math.min(...xs) >= 20 && Math.max(...ys) - Math.min(...ys) >= 10;
}

function normaliser(pts: Pt[]): number[][] {
  const n = pts.length;
  const cx = pts.reduce((s, p) => s + p[0], 0) / n;
  const cy = pts.reduce((s, p) => s + p[1], 0) / n;
  const d = pts.reduce((s, p) => s + Math.hypot(p[0] - cx, p[1] - cy), 0) / n || 1;
  const k = Math.SQRT2 / d;
  return [
    [k, 0, -k * cx],
    [0, k, -k * cy],
    [0, 0, 1],
  ];
}

function apply(m: number[][], p: Pt): Pt {
  const w = m[2]![0]! * p[0] + m[2]![1]! * p[1] + m[2]![2]!;
  return [(m[0]![0]! * p[0] + m[0]![1]! * p[1] + m[0]![2]!) / w, (m[1]![0]! * p[0] + m[1]![1]! * p[1] + m[1]![2]!) / w];
}

function mul(a: number[][], b: number[][]): number[][] {
  return a.map((row) => b[0]!.map((_, j) => row.reduce((s, v, k) => s + v * b[k]![j]!, 0)));
}

function invert3(m: number[][]): number[][] | null {
  const [a, b, c] = m[0]!;
  const [d, e, f] = m[1]!;
  const [g, h, i] = m[2]!;
  const A = e! * i! - f! * h!;
  const B = -(d! * i! - f! * g!);
  const C = d! * h! - e! * g!;
  const det = a! * A + b! * B + c! * C;
  if (Math.abs(det) < 1e-12) return null;
  return [
    [A / det, -(b! * i! - c! * h!) / det, (b! * f! - c! * e!) / det],
    [B / det, (a! * i! - c! * g!) / det, -(a! * f! - c! * d!) / det],
    [C / det, -(a! * h! - b! * g!) / det, (a! * e! - b! * d!) / det],
  ];
}

/** Solves the n x n system a x = b (Gaussian elimination with partial pivoting). */
function solve(a: number[][], b: number[]): number[] | null {
  const n = b.length;
  const m = a.map((row, i) => [...row, b[i]!]);
  for (let col = 0; col < n; col++) {
    let piv = col;
    for (let r = col + 1; r < n; r++) if (Math.abs(m[r]![col]!) > Math.abs(m[piv]![col]!)) piv = r;
    if (Math.abs(m[piv]![col]!) < 1e-12) return null;
    [m[col], m[piv]] = [m[piv]!, m[col]!];
    for (let r = 0; r < n; r++) {
      if (r === col) continue;
      const f = m[r]![col]! / m[col]![col]!;
      for (let c = col; c <= n; c++) m[r]![c]! -= f * m[col]![c]!;
    }
  }
  return m.map((row, i) => row[n]! / row[i]!);
}

/** Least-squares homography court -> image from 4 or more point pairs (normalised DLT, h33 = 1). */
export function fitHomography(court: Pt[], image: Pt[]): Homography | null {
  if (court.length < MIN_POINTS || court.length !== image.length) return null;
  const tc = normaliser(court);
  const ti = normaliser(image);
  const ata = Array.from({ length: 8 }, () => new Array<number>(8).fill(0));
  const atb = new Array<number>(8).fill(0);
  court.forEach((cp, k) => {
    const [x, y] = apply(tc, cp);
    const [u, v] = apply(ti, image[k]!);
    for (const [row, rhs] of [
      [[x, y, 1, 0, 0, 0, -u * x, -u * y], u],
      [[0, 0, 0, x, y, 1, -v * x, -v * y], v],
    ] as [number[], number][]) {
      for (let i = 0; i < 8; i++) {
        atb[i]! += row[i]! * rhs;
        for (let j = 0; j < 8; j++) ata[i]![j]! += row[i]! * row[j]!;
      }
    }
  });
  const h = solve(ata, atb);
  if (!h) return null;
  const hn = [
    [h[0]!, h[1]!, h[2]!],
    [h[3]!, h[4]!, h[5]!],
    [h[6]!, h[7]!, 1],
  ];
  const tiInv = invert3(ti);
  if (!tiInv) return null;
  const out = mul(mul(tiInv, hn), tc);
  const s = out[2]![2]!;
  return Math.abs(s) < 1e-12 ? null : out.map((row) => row.map((v) => v / s));
}

/** Court metres -> image pixels; null behind the camera. */
export function toImage(h: Homography, p: Pt): Pt | null {
  const w = h[2]![0]! * p[0] + h[2]![1]! * p[1] + h[2]![2]!;
  if (w <= 1e-9) return null;
  return [(h[0]![0]! * p[0] + h[0]![1]! * p[1] + h[0]![2]!) / w, (h[1]![0]! * p[0] + h[1]![1]! * p[1] + h[1]![2]!) / w];
}

/** Mean distance in pixels between the clicked points and the fitted court. */
export function reprojectionPx(h: Homography, court: Pt[], image: Pt[]): number {
  const d = court.map((c, k) => {
    const p = toImage(h, c);
    return p ? Math.hypot(p[0] - image[k]![0], p[1] - image[k]![1]) : Infinity;
  });
  return d.reduce((s, v) => s + v, 0) / Math.max(1, d.length);
}

/** All court lines as image polylines (parts behind the camera are dropped), for SVG paths. */
export function courtPolylines(h: Homography): Pt[][] {
  const out: Pt[][] = [];
  for (const line of Object.values(COURT.lines) as readonly (readonly Point[])[]) {
    let cur: Pt[] = [];
    for (const [x, y] of line) {
      const p = toImage(h, [x, y]);
      if (p) cur.push(p);
      else if (cur.length) {
        out.push(cur);
        cur = [];
      }
    }
    if (cur.length > 1) out.push(cur);
  }
  return out;
}
