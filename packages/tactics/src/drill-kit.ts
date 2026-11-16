/** Small helpers to write the drill library: texts in three languages and court sketches. */
import type { Arrow, Side, Token } from "./format";
import type { DrillSketch, Text } from "./drills";
import { GOAL_X } from "./geometry";

export type P = readonly [number, number];

export const L = (de: string, fr: string, en: string): Text => ({ "de-CH": de, fr, en });

const counters = new Map<string, number>();
function token(side: Side, label: string, [x, y]: P, id?: string): Token {
  const key = side === "own" ? "a" : "d";
  const n = (counters.get(key) ?? 0) + 1;
  counters.set(key, n);
  return { id: id ?? `${key}${n}`, side, label, x, y };
}

/** a player who practises (blue) */
export const me = (label: string, p: P, id?: string) => token("own", label, p, id);
/** an opponent or defender (orange) */
export const op = (label: string, p: P, id?: string) => token("opp", label, p, id);
/** goalkeepers in the right goal (and the left one for full-court drills) */
export const keeper = (side: Side = "own", left = false): Token => ({ id: side === "own" ? "tw" : "otw", side, label: "TW", x: left ? 0.7 : GOAL_X - 0.7, y: 10 });

const arrow = (kind: Arrow["kind"]) => (...pts: P[]): Arrow => ({ kind, points: pts.map(([x, y]) => [x, y] as [number, number]) });
export const run = arrow("run");
export const pass = arrow("pass");
export const dribble = arrow("dribble");
export const screen = arrow("screen");
/** a shot is drawn as a pass into the goal */
export const shot = (from: P, high = true): Arrow => pass(from, [GOAL_X - 0.4, high ? 11.1 : 8.9]);
export const shotLeft = (from: P): Arrow => pass(from, [0.4, 10.9]);

/** A sketch; token ids restart for every sketch. */
export function sketch(build: () => { tokens: Token[]; arrows?: Arrow[]; ball?: P | null; cones?: P[]; court?: "half" | "full" }): DrillSketch {
  counters.clear();
  const s = build();
  return {
    court: s.court ?? "half",
    tokens: s.tokens,
    arrows: s.arrows ?? [],
    ball: s.ball ? { x: s.ball[0], y: s.ball[1] } : null,
    cones: (s.cones ?? []).map(([x, y]) => [x, y] as [number, number]),
  };
}
