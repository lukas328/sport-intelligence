/**
 * The court calibration dialog's state, as a reducer: the suggestion step («Passt» or
 * correct), then the line mode (pick a line, click 2 to 3 spots on it; named points as the
 * advanced option). Every change can be undone, dragging and clearing included.
 */
import { LINE_NAMES, POINT_NAMES, type ClickRef, type Clicks, type LineName, type PointName, type Pt } from "@/lib/court-fit";

/** After this many clicks on a line the next line is chosen. */
export const CLICKS_PER_LINE = 3;

type Undo =
  | { kind: "line"; name: string }
  | { kind: "point"; name: string; prev: Pt | null }
  | { kind: "move"; ref: ClickRef; prev: Pt }
  | { kind: "clear"; prev: Clicks };

export interface FlowState {
  step: "suggest" | "mark";
  mode: "line" | "point";
  line: LineName;
  point: PointName;
  clicks: Clicks;
  history: Undo[];
  snap: boolean;
  /** the click last placed or moved (arrow keys nudge it) */
  selected: ClickRef | null;
}

export type FlowAction =
  | { type: "correct" }
  | { type: "suggest" }
  | { type: "line"; name: LineName }
  | { type: "point"; name: PointName }
  | { type: "mode"; mode: "line" | "point" }
  | { type: "place"; p: Pt }
  /** a dragged click: `prev` is where it was when the drag began (one undo for the drag) */
  | { type: "move"; ref: ClickRef; p: Pt; prev?: Pt }
  | { type: "nudge"; dx: number; dy: number }
  | { type: "select"; ref: ClickRef }
  | { type: "undo" }
  | { type: "clearLine"; name?: string }
  | { type: "clearAll" }
  | { type: "snap" };

/** The start: the suggestion to look at first, if there is one; the coach's last clicks to edit
 * again, if there are any (then straight to the clicks). */
export function initialFlow({ suggestion, clicks }: { suggestion: boolean; clicks?: Clicks | null }): FlowState {
  const start = clicks ?? { points: {}, lines: {} };
  const line = LINE_NAMES.find((n) => !start.lines[n]?.length) ?? LINE_NAMES[0];
  return {
    step: suggestion && !clicks ? "suggest" : "mark",
    mode: "line",
    line,
    point: POINT_NAMES[0],
    clicks: start,
    history: [],
    snap: true,
    selected: null,
  };
}

export function clickAt(c: Clicks, ref: ClickRef): Pt | null {
  return ref.kind === "point" ? (c.points[ref.name] ?? null) : (c.lines[ref.name]?.[ref.index] ?? null);
}

function setClick(c: Clicks, ref: ClickRef, p: Pt): Clicks {
  if (ref.kind === "point") return { ...c, points: { ...c.points, [ref.name]: p } };
  const l = (c.lines[ref.name] ?? []).slice();
  l[ref.index] = p;
  return { ...c, lines: { ...c.lines, [ref.name]: l } };
}

function nextLine(c: Clicks, after: LineName): LineName {
  const i = LINE_NAMES.indexOf(after);
  for (let k = 1; k <= LINE_NAMES.length; k++) {
    const n = LINE_NAMES[(i + k) % LINE_NAMES.length]!;
    if (!c.lines[n]?.length) return n;
  }
  return after;
}

function nextPoint(c: Clicks, after: PointName): PointName {
  const i = POINT_NAMES.indexOf(after);
  for (let k = 1; k <= POINT_NAMES.length; k++) {
    const n = POINT_NAMES[(i + k) % POINT_NAMES.length]!;
    if (!c.points[n]) return n;
  }
  return after;
}

export function flowReducer(s: FlowState, a: FlowAction): FlowState {
  switch (a.type) {
    case "correct":
      return { ...s, step: "mark" };
    case "suggest":
      return { ...s, step: "suggest" };
    case "line":
      return { ...s, step: "mark", mode: "line", line: a.name };
    case "point":
      return { ...s, step: "mark", mode: "point", point: a.name };
    case "mode":
      return { ...s, mode: a.mode };
    case "place": {
      if (s.step !== "mark") return s;
      if (s.mode === "point") {
        const name = s.point;
        const clicks = { ...s.clicks, points: { ...s.clicks.points, [name]: a.p } };
        return { ...s, clicks, history: [...s.history, { kind: "point", name, prev: s.clicks.points[name] ?? null }], selected: { kind: "point", name }, point: nextPoint(clicks, name) };
      }
      const name = s.line;
      const l = [...(s.clicks.lines[name] ?? []), a.p];
      const clicks = { ...s.clicks, lines: { ...s.clicks.lines, [name]: l } };
      return {
        ...s,
        clicks,
        history: [...s.history, { kind: "line", name }],
        selected: { kind: "line", name, index: l.length - 1 },
        line: l.length >= CLICKS_PER_LINE ? nextLine(clicks, name) : name,
      };
    }
    case "move": {
      const prev = a.prev ?? clickAt(s.clicks, a.ref);
      if (!prev) return s;
      return { ...s, clicks: setClick(s.clicks, a.ref, a.p), history: [...s.history, { kind: "move", ref: a.ref, prev }], selected: a.ref };
    }
    case "select":
      return clickAt(s.clicks, a.ref) ? { ...s, selected: a.ref } : s;
    case "nudge": {
      const ref = s.selected;
      const p = ref && clickAt(s.clicks, ref);
      if (!ref || !p) return s;
      const last = s.history[s.history.length - 1];
      // a run of nudges of the same click is one step back
      const same = last?.kind === "move" && JSON.stringify(last.ref) === JSON.stringify(ref);
      return { ...s, clicks: setClick(s.clicks, ref, [p[0] + a.dx, p[1] + a.dy]), history: same ? s.history : [...s.history, { kind: "move", ref, prev: p }] };
    }
    case "undo": {
      const h = s.history[s.history.length - 1];
      if (!h) return s;
      const history = s.history.slice(0, -1);
      if (h.kind === "clear") return { ...s, clicks: h.prev, history, selected: null };
      if (h.kind === "move") return { ...s, clicks: setClick(s.clicks, h.ref, h.prev), history, selected: h.ref };
      if (h.kind === "point") {
        const points = { ...s.clicks.points };
        if (h.prev) points[h.name] = h.prev;
        else delete points[h.name];
        return { ...s, clicks: { ...s.clicks, points }, history, mode: "point", point: h.name as PointName, selected: null };
      }
      const l = (s.clicks.lines[h.name] ?? []).slice(0, -1);
      const lines = { ...s.clicks.lines, [h.name]: l };
      if (!l.length) delete lines[h.name];
      return { ...s, clicks: { ...s.clicks, lines }, history, mode: "line", line: h.name as LineName, selected: null };
    }
    case "clearLine": {
      const name = a.name ?? (s.mode === "line" ? s.line : s.point);
      const isLine = name in s.clicks.lines;
      if (!isLine && !(name in s.clicks.points)) return s;
      const lines = { ...s.clicks.lines };
      const points = { ...s.clicks.points };
      delete lines[name];
      delete points[name];
      return { ...s, clicks: { lines, points }, history: [...s.history, { kind: "clear", prev: s.clicks }], selected: null };
    }
    case "clearAll":
      if (!Object.keys(s.clicks.lines).length && !Object.keys(s.clicks.points).length) return s;
      return { ...s, clicks: { points: {}, lines: {} }, history: [...s.history, { kind: "clear", prev: s.clicks }], selected: null, line: LINE_NAMES[0], point: POINT_NAMES[0] };
    case "snap":
      return { ...s, snap: !s.snap };
  }
}

/** How many clicks there are on a line or whether a point is set. */
export function countOn(c: Clicks, name: string): number {
  return c.lines[name]?.length ?? (c.points[name] ? 1 : 0);
}
