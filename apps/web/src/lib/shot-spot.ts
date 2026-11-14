/**
 * Where the shot of a goal came from (fourth real-video test H7). Prüfen asks «Von wo?» with one
 * tap on a small court of the attacked half, goal at the top, as in the bundles of the three
 * things. Left and right are the attacker's: facing the goal, «Aussen links» is on the left of the
 * picture (half court u from the attacker's left, API: graphics.to_half, zones.json).
 */
import type { Pt } from "@/components/anlauf/geometry";
import type { MatchGraphics } from "@/lib/graphics";

/** the six places on the court, in reading order of the picture (top row, then the back court) */
export const COURT_ZONES = ["la", "kr", "ra", "rl", "rm", "rr"] as const;
/** the two kinds that replace the place: Siebenmeter and Gegenstoss */
export const KIND_ZONES = ["m7", "gs"] as const;
export type SpotZone = (typeof COURT_ZONES)[number] | (typeof KIND_ZONES)[number];
export type SpotAnswer = SpotZone | "unknown";

/** half court (u across from the attacker's left, v from the goal line) to court metres with the attacked goal at x = 40 */
export function halfToCourt(p: Pt): Pt {
  return [round(40 - p[1]), round(20 - p[0])];
}

function round(n: number): number {
  return Math.round(n * 100) / 100;
}

/** the 9 m line at u (half court): where the circle ends and the back court begins */
export function nineAt(u: number): number {
  if (u <= 8.5) return Math.sqrt(Math.max(0, 81 - (8.5 - u) ** 2));
  if (u >= 11.5) return Math.sqrt(Math.max(0, 81 - (u - 11.5) ** 2));
  return 9;
}

const DEEP = 16; // the lower edge of the drawn half court
const WING = 4; // the wings: the outer 4 m from the goal line to the 9 m line's height
const BACK = 7; // the back court: left and right of the middle 6 m

function arc(from: number, to: number): Pt[] {
  const out: Pt[] = [];
  const n = 12;
  for (let i = 0; i <= n; i++) {
    const u = from + ((to - from) * i) / n;
    out.push([u, nineAt(u)]);
  }
  return out;
}

/** the tap area of each place on the half court, as a closed polygon */
export const ZONE_AREA: Record<(typeof COURT_ZONES)[number], Pt[]> = {
  la: [[0, 0], [WING, 0], [WING, 9], [0, 9]],
  ra: [[20 - WING, 0], [20, 0], [20, 9], [20 - WING, 9]],
  kr: [[WING, 0], [20 - WING, 0], ...arc(20 - WING, WING)],
  rl: [[0, 9], [WING, 9], ...arc(WING, BACK), [BACK, DEEP], [0, DEEP]],
  rm: [...arc(BACK, 20 - BACK), [20 - BACK, DEEP], [BACK, DEEP]],
  rr: [...arc(20 - BACK, 20 - WING), [20 - WING, 9], [20, 9], [20, DEEP], [20 - BACK, DEEP]],
};

/** where the name of a place stands in its area (two lines: «Rückraum» / «links») */
export const ZONE_LABEL_AT: Record<(typeof COURT_ZONES)[number], Pt> = {
  la: [2, 3.6],
  ra: [18, 3.6],
  kr: [10, 3.4],
  rl: [3.5, 12.2],
  rm: [10, 12.2],
  rr: [16.5, 12.2],
};

export function polygonPath(pts: readonly Pt[]): string {
  return `${pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join("")}Z`;
}

/** Which place a point of the half court lies in (the same areas as the picture). */
export function zoneAtHalf(p: Pt): (typeof COURT_ZONES)[number] {
  const [u, v] = p;
  const inside = v <= nineAt(u);
  if (v <= 9 && u <= WING) return "la";
  if (v <= 9 && u >= 20 - WING) return "ra";
  if (inside) return "kr";
  if (u < BACK) return "rl";
  if (u > 20 - BACK) return "rr";
  return "rm";
}

type Goal = MatchGraphics["goals"][number];

/** The goals in the video that still miss where they were thrown from, in the order of the video. */
export function goalsWithoutSpot(g: MatchGraphics): Goal[] {
  return g.goals.filter((x) => x.spot_missing && x.t_ms != null).sort((a, b) => (a.t_ms ?? 0) - (b.t_ms ?? 0));
}

/** How far the places of a match's goals are: given by the coach, missing (askable, an estimate or «Weiss nicht» included), all (V1). */
export function spotCounts(g: MatchGraphics): { placed: number; missing: number; total: number } {
  const goals = g.goals.filter((x) => x.has_video || x.zone != null);
  return { placed: goals.filter((x) => x.spot_by_coach === true).length, missing: goalsWithoutSpot(g).length, total: goals.length };
}

/** Minutes for Prüfen: goal moments with «Von wo?» about 23 s, other questions about 18 s, a place alone about 7 s (measured without the place: 22 questions in 6 to 7 minutes). */
export function checkMinutes(goalQuestions: number, otherQuestions: number, placesOnly = 0): number {
  const s = goalQuestions * 23 + otherQuestions * 18 + placesOnly * 7;
  return Math.max(1, Math.round(s / 60));
}

/**
 * How the small court of «Von wo?» lies (real-clip test of «Von wo?»): with the goal at the top
 * (no confirmed court), or as the camera sees it: the attacked goal on the left or the right as in
 * the video, the far sideline at the top. Facing the goal on the right, the attacker's left is the
 * top of the picture; facing the goal on the left, it is the bottom. So the side of the goal in the
 * video is all it takes, whichever long side the camera stands on.
 */
export type SpotOrientation = "top" | "left" | "right";

/** half court (u, v) to the picture, as an SVG matrix [a, b, c, d, e, f] */
export function orientationMatrix(o: SpotOrientation): [number, number, number, number, number, number] {
  if (o === "right") return [0, 1, -1, 0, 16, 0]; // x = 16 - v, y = u
  if (o === "left") return [0, -1, 1, 0, 0, 20]; // x = v, y = 20 - u
  return [1, 0, 0, 1, 0, 0];
}

/** the visible box of the picture: the half court and the goal behind its line */
export function orientationBox(o: SpotOrientation): [number, number, number, number] {
  if (o === "right") return [-0.6, -0.6, 17.9, 21.2];
  if (o === "left") return [-1.3, -0.6, 17.9, 21.2];
  return [-0.6, -1.2, 21.2, 17.4];
}

export function toPicture(o: SpotOrientation, p: Pt): Pt {
  const [a, b, c, d, e, f] = orientationMatrix(o);
  return [a * p[0] + c * p[1] + e, b * p[0] + d * p[1] + f];
}

export function fromPicture(o: SpotOrientation, q: Pt): Pt {
  if (o === "right") return [q[1], 16 - q[0]];
  if (o === "left") return [20 - q[1], q[0]];
  return q;
}

/** Which place a point of the picture lies in, in any orientation. */
export function zoneAtPicture(o: SpotOrientation, q: Pt): (typeof COURT_ZONES)[number] {
  return zoneAtHalf(fromPicture(o, q));
}

/** where a place's name stands when the court lies on its side (centres of the areas) */
export const ZONE_LABEL_SIDE: Record<(typeof COURT_ZONES)[number], Pt> = {
  la: [2, 4.5],
  ra: [18, 4.5],
  kr: [10, 3.6],
  rl: [3.5, 12.6],
  rm: [10, 12.6],
  rr: [16.5, 12.6],
};
