/**
 * Tactics board data format, interpolation and templates (BRIEF 8.3, M6).
 * The format is versioned; every document carries `formatVersion`. Coordinates are court metres
 * (x 0..40 along the court, y 0..20), the same system as `@handball/court` and the tracking data.
 */
export const TACTICS_FORMAT_VERSION = 1 as const;

export type Side = "own" | "opp";
export type ArrowKind = "run" | "pass" | "screen" | "dribble";

export interface Token {
  id: string;
  side: Side;
  label: string; // position (LA, RL, ...) or jersey number, max 3 characters
  x: number;
  y: number;
}

export interface Arrow {
  kind: ArrowKind;
  points: [number, number][];
}

export interface Frame {
  tokens: Token[];
  ball: { x: number; y: number } | null;
  arrows: Arrow[];
  note: string;
  duration_ms: number;
}

export interface PlayDoc {
  formatVersion: typeof TACTICS_FORMAT_VERSION;
  court: "half" | "full";
  frames: Frame[];
}

export const LIMITS = { frames: 30, tokens: 16, arrows: 20, note: 300, minDuration: 300, maxDuration: 10_000 } as const;

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const round = (v: number) => Math.round(v * 100) / 100;

export function clampToCourt(x: number, y: number): [number, number] {
  return [round(clamp(x, -1, 41)), round(clamp(y, -1, 21))];
}

/** A copy of the frame as the start of the next one: tokens move to the end of their run arrows. */
export function nextFrame(f: Frame): Frame {
  const ends = new Map<string, [number, number]>();
  for (const a of f.arrows) {
    if (a.kind !== "run" && a.kind !== "dribble") continue;
    const [sx, sy] = a.points[0]!;
    const near = f.tokens.find((t) => Math.hypot(t.x - sx, t.y - sy) < 1.2);
    if (near) ends.set(near.id, a.points[a.points.length - 1]!);
  }
  const pass = f.arrows.find((a) => a.kind === "pass");
  return {
    tokens: f.tokens.map((t) => {
      const e = ends.get(t.id);
      return e ? { ...t, x: e[0], y: e[1] } : { ...t };
    }),
    ball: pass ? { x: pass.points[pass.points.length - 1]![0], y: pass.points[pass.points.length - 1]![1] } : f.ball ? { ...f.ball } : null,
    arrows: [],
    note: "",
    duration_ms: f.duration_ms,
  };
}

export function totalDuration(doc: PlayDoc): number {
  return doc.frames.reduce((s, f) => s + f.duration_ms, 0);
}

const ease = (t: number) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);

/**
 * State at time `ms` of the animation: each frame holds for the first 30 % of its duration, then
 * tokens and ball move (eased) to their positions in the next frame. Tokens that only exist in one of
 * the two frames appear or disappear at the switch.
 */
export function stateAt(doc: PlayDoc, ms: number): { frame: number; tokens: Token[]; ball: { x: number; y: number } | null } {
  const frames = doc.frames;
  if (frames.length === 0) return { frame: 0, tokens: [], ball: null };
  let t = clamp(ms, 0, totalDuration(doc));
  for (let i = 0; i < frames.length; i++) {
    const f = frames[i]!;
    const next = frames[i + 1];
    if (t <= f.duration_ms || !next) {
      if (!next) return { frame: i, tokens: f.tokens, ball: f.ball };
      const hold = f.duration_ms * 0.3;
      const p = t <= hold ? 0 : ease((t - hold) / (f.duration_ms - hold));
      const by = new Map(next.tokens.map((n) => [n.id, n]));
      const tokens = f.tokens.map((a) => {
        const b = by.get(a.id);
        return b ? { ...a, x: a.x + (b.x - a.x) * p, y: a.y + (b.y - a.y) * p } : a;
      });
      const ball =
        f.ball && next.ball ? { x: f.ball.x + (next.ball.x - f.ball.x) * p, y: f.ball.y + (next.ball.y - f.ball.y) * p } : f.ball;
      return { frame: i, tokens, ball };
    }
    t -= f.duration_ms;
  }
  const last = frames[frames.length - 1]!;
  return { frame: frames.length - 1, tokens: last.tokens, ball: last.ball };
}

/** Problems that make a document unusable (mirrors the API validation). Empty list = valid. */
export function validate(doc: PlayDoc): string[] {
  const errors: string[] = [];
  if (doc.formatVersion !== TACTICS_FORMAT_VERSION) errors.push("formatVersion");
  if (doc.frames.length === 0 || doc.frames.length > LIMITS.frames) errors.push("frames");
  doc.frames.forEach((f, i) => {
    if (f.tokens.length > LIMITS.tokens) errors.push(`frame ${i}: tokens`);
    if (new Set(f.tokens.map((t) => t.id)).size !== f.tokens.length) errors.push(`frame ${i}: duplicate token`);
    if (f.arrows.length > LIMITS.arrows) errors.push(`frame ${i}: arrows`);
    if (f.arrows.some((a) => a.points.length < 2)) errors.push(`frame ${i}: arrow points`);
    if (f.note.length > LIMITS.note) errors.push(`frame ${i}: note`);
    if (f.duration_ms < LIMITS.minDuration || f.duration_ms > LIMITS.maxDuration) errors.push(`frame ${i}: duration`);
  });
  return errors;
}

/** Positions from tracking (court metres) as a first frame: own team as `own`, opponent as `opp`. */
export function frameFromPositions(points: { track: number; side: Side; x: number; y: number }[], ownLabel = "", oppLabel = ""): Frame {
  return {
    tokens: points.slice(0, LIMITS.tokens).map((p, i) => ({
      id: `${p.side[0]}${i + 1}`,
      side: p.side,
      label: (p.side === "own" ? ownLabel : oppLabel) || String(i + 1),
      x: round(p.x),
      y: round(p.y),
    })),
    ball: null,
    arrows: [],
    note: "",
    duration_ms: 1500,
  };
}

