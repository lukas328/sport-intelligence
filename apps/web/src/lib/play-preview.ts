import type { PlayDoc } from "@handball/tactics";

const MARGIN_M = 2; // a token's radius and some air in front of the farthest player

/**
 * Where a small picture of a half-court play starts (court metres along the court): just in
 * front of the farthest player, ball or arrow of the first frame, so a thumbnail shows the play
 * and not an empty half court (review R12). The board keeps it between 20 (the centre line) and
 * 30 (the 10 m in front of the goal). Undefined for a full court or an empty board.
 */
export function previewFrom(doc: PlayDoc): number | undefined {
  if (doc.court !== "half") return undefined;
  const f = doc.frames[0];
  if (!f) return undefined;
  const xs = [
    ...f.tokens.map((t) => t.x),
    ...(f.ball ? [f.ball.x] : []),
    ...f.arrows.flatMap((a) => a.points.map((p) => p[0])),
  ];
  if (xs.length === 0) return undefined;
  return Math.floor(Math.min(...xs) - MARGIN_M);
}

/** One start for a grid of pictures, so they line up at the same height: the farthest of all. */
export function commonFrom(docs: readonly PlayDoc[]): number | undefined {
  const all = docs.map(previewFrom).filter((x): x is number => x != null);
  return all.length ? Math.min(...all) : undefined;
}
