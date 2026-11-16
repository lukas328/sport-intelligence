/**
 * Court geometry for the tactics board and its templates, in court metres (the system of
 * `@handball/court`: x 0..40 along the court, y 0..20, the attacked goal on the right at x = 40,
 * facing it +y is left). A test checks these numbers against the generated court geometry.
 *
 * The goal-area line (6 m) and the free-throw line (9 m) are not circles around the goal centre:
 * they are quarter circles around each post joined by a straight line in front of the goal. Every
 * position in the templates is placed with `lineSpot`, so defenders stand in front of the 6 m line
 * in the shape of their formation and attackers around 9 m.
 */
import type { Frame, PlayDoc, Token } from "./format";

export const COURT_LENGTH = 40;
export const COURT_WIDTH = 20;
export const GOAL_X = 40;
export const POST_LOW = 8.5;
export const POST_HIGH = 11.5;
export const GOAL_AREA_M = 6;
export const FREE_THROW_M = 9;

/** Radius of a player on the board (m) and the smallest distance between two players in a template. */
export const TOKEN_RADIUS = 0.8;
export const MIN_GAP = 2 * TOKEN_RADIUS + 0.1;

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const round = (v: number) => Math.round(v * 100) / 100;

/** Distance (m) from a point to the goal mouth of the right goal (x = 40) or the left one (x = 0). */
export function distToGoal(x: number, y: number, goal: "right" | "left" = "right"): number {
  const gx = goal === "right" ? GOAL_X : 0;
  return Math.hypot(gx - x, y - clamp(y, POST_LOW, POST_HIGH));
}

/**
 * A point at distance `d` (m) from the goal mouth of the right goal, `s` along that line from the
 * right corner (-1) over the centre (0) to the left corner (+1), seen by the attacker. The arc
 * length is shared evenly, so equal steps of `s` give equal gaps between players.
 */
export function lineSpot(d: number, s: number): [number, number] {
  const flat = (POST_HIGH - POST_LOW) / 2;
  const half = flat + (Math.PI / 2) * d;
  const a = Math.abs(clamp(s, -1, 1)) * half;
  const sign = s < 0 ? -1 : 1;
  if (a <= flat) return [round(GOAL_X - d), round(10 + sign * a)];
  const phi = (a - flat) / d;
  return [round(GOAL_X - d * Math.cos(phi)), round(10 + sign * (flat + d * Math.sin(phi)))];
}

/** The same spot for the left goal (a play towards x = 0, e.g. the own half in a full-court play). */
export function mirrorX([x, y]: readonly [number, number]): [number, number] {
  return [round(COURT_LENGTH - x), round(COURT_WIDTH - y)];
}

/** Smallest distance between two tokens of a frame (Infinity with fewer than two). */
export function minTokenGap(tokens: readonly Token[]): number {
  let best = Infinity;
  for (let i = 0; i < tokens.length; i++)
    for (let j = i + 1; j < tokens.length; j++) best = Math.min(best, Math.hypot(tokens[i]!.x - tokens[j]!.x, tokens[i]!.y - tokens[j]!.y));
  return best;
}

/**
 * A free spot for a new token: near `around`, inside the court and away from the goal areas, at
 * least `MIN_GAP` from every token. Searches rings around the wanted spot.
 */
export function freeSpot(tokens: readonly Token[], around: readonly [number, number]): [number, number] {
  const ok = (x: number, y: number) =>
    x > 0.8 && x < 39.2 && y > 0.8 && y < 19.2 && distToGoal(x, y) > GOAL_AREA_M + 0.4 && distToGoal(x, y, "left") > GOAL_AREA_M + 0.4 && tokens.every((t) => Math.hypot(t.x - x, t.y - y) >= MIN_GAP);
  if (ok(around[0], around[1])) return [round(around[0]), round(around[1])];
  for (let r = 1; r <= 14; r += 0.8) {
    const steps = Math.max(8, Math.round(r * 5));
    for (let k = 0; k < steps; k++) {
      const a = (k / steps) * Math.PI * 2;
      const x = around[0] + r * Math.cos(a);
      const y = around[1] + r * Math.sin(a);
      if (ok(x, y)) return [round(x), round(y)];
    }
  }
  return [round(around[0]), round(around[1])];
}

const MIRROR_LABEL: Record<string, string> = { LA: "RA", RA: "LA", RL: "RR", RR: "RL", HL: "HR", HR: "HL" };

function mirrorFrame(f: Frame): Frame {
  const y = (v: number) => round(COURT_WIDTH - v);
  return {
    ...f,
    tokens: f.tokens.map((t) => ({ ...t, y: y(t.y), label: MIRROR_LABEL[t.label] ?? t.label })),
    ball: f.ball ? { x: f.ball.x, y: y(f.ball.y) } : null,
    arrows: f.arrows.map((a) => ({ ...a, points: a.points.map(([px, py]) => [px, y(py)] as [number, number]) })),
  };
}

/** Left and right swapped (a play for the other side): positions, runs and the wing and back labels. */
export function mirrorDoc(doc: PlayDoc): PlayDoc {
  return { ...doc, frames: doc.frames.map(mirrorFrame) };
}
