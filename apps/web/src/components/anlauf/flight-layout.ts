/** Geometry of the Flight (the run of the match in the Wurf head), without React: tested. */
import type { Pt } from "./geometry";

/** A goal of the match report: minute and side. The order of the report is the order of play. */
export interface ReportGoal {
  minute: number;
  team: "own" | "opp";
}

/** Running goal difference after each goal: [minute, difference], starting at [0, 0]. */
export function flowOf(goals: readonly ReportGoal[]): [number, number][] {
  const out: [number, number][] = [[0, 0]];
  let v = 0;
  for (const g of [...goals].sort((a, b) => a.minute - b.minute)) {
    v += g.team === "own" ? 1 : -1;
    out.push([g.minute, v]);
  }
  return out;
}

export function diffAt(flow: readonly [number, number][], m: number): number {
  let v = 0;
  for (const p of flow) if (p[0] <= m) v = p[1];
  return v;
}

export const signed = (v: number) => `${v > 0 ? "+" : ""}${v}`;

export interface FlightLabels {
  /** "{v}" is replaced by the signed difference */
  half: string;
  end: string;
  /** said instead when the difference is zero ("Halbzeit, Gleichstand") */
  halfLevel?: string;
  endLevel?: string;
}

export interface FlightLabel {
  text: string;
  /** baseline */
  x: number;
  y: number;
  anchor: "start" | "middle" | "end";
  /** the space the text takes: [x0, y0, x1, y1] */
  box: [number, number, number, number];
}

export interface FlightLayout {
  pts: Pt[];
  base: number;
  end: Pt;
  labels: FlightLabel[];
}

const LABEL_SIZE = 14; // px, the labels' font size
const LABEL_GAP = 8; // between a label and the line
const charWidth = 7.6; // a generous average for 600 14px Hanken Grotesk

/** Lowest y a point or label may reach at x: the bottom, raised along the slanted edge. */
export function floorAt(x: number, width: number, height: number, slant: number): number {
  return height - 6 - (slant * x) / width;
}

/**
 * Where the line and its labels go. The line keeps clear of the slanted lower edge of the head
 * (`slant`: how far the edge rises over the width, in the drawing's units); every label keeps
 * LABEL_GAP from the line and from the edge: above the line where it fits, else below.
 */
export function flightLayout(goals: readonly ReportGoal[], width: number, height: number, length = 60, labels?: FlightLabels, slant = 0): FlightLayout {
  const flow = flowOf(goals);
  const pad = width < 500 ? 16 : 32;
  const top = labels ? LABEL_SIZE + LABEL_GAP + 6 : 10;
  const lo = Math.min(0, ...flow.map((p) => p[1]));
  const hi = Math.max(0, ...flow.map((p) => p[1]));
  const x = (m: number) => pad + ((width - 2 * pad - 14) * Math.min(m, length)) / length;
  const steps: [number, number][] = [];
  flow.forEach((p, i) => {
    if (i) steps.push([x(p[0]), flow[i - 1]![1]]);
    steps.push([x(p[0]), p[1]]);
  });
  const endV = diffAt(flow, length);
  steps.push([x(length), endV]);
  // the scale: the whole range between the top and the slanted floor
  let U = (height - top - 6 - slant) / Math.max(10, hi - lo);
  let base = Math.min(...steps.map(([px, v]) => floorAt(px, width, height, slant) - 6 + v * U), floorAt(pad, width, height, slant) - 6);
  if (base - hi * U < top) {
    U = (base - top) / Math.max(1, hi);
    base = Math.min(...steps.map(([px, v]) => floorAt(px, width, height, slant) - 6 + v * U));
  }
  const y = (v: number) => base - v * U;
  const pts: Pt[] = steps.map(([px, v]) => [px, y(v)]);
  const end: Pt = [x(length), y(endV)];
  const out: FlightLabel[] = [];
  if (labels) {
    const half = diffAt(flow, length / 2);
    const say = (tpl: string, level: string | undefined, v: number) => (v === 0 && level ? level : tpl.replace("{v}", signed(v)));
    const place = (text: string, cx: number, anchor: FlightLabel["anchor"]) => {
      const w = text.length * charWidth;
      const x0 = anchor === "middle" ? cx - w / 2 : anchor === "end" ? cx - w : cx;
      const x1 = x0 + w;
      const near = pts.filter((p, i) => (p[0] >= x0 - LABEL_GAP && p[0] <= x1 + LABEL_GAP) || (i > 0 && pts[i - 1]![0] < x0 && p[0] > x1));
      const ys = near.length ? near.map((p) => p[1]) : [y(0)];
      const above = Math.min(...ys) - LABEL_GAP;
      const fits = above - LABEL_SIZE >= 2;
      const baseline = fits ? above - 3 : Math.max(...ys) + LABEL_GAP + LABEL_SIZE - 3;
      const box: FlightLabel["box"] = [x0, baseline - LABEL_SIZE + 3, x1, baseline + 3];
      out.push({ text, x: cx, y: baseline, anchor, box });
    };
    place(say(labels.half, labels.halfLevel, half), x(length / 2), "middle");
    // the end label to the left of the end dot, clear of it
    place(say(labels.end, labels.endLevel, endV), end[0] - 12, "end");
  }
  return { pts, base, end, labels: out };
}

