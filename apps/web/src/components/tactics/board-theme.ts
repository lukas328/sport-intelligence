/** Colours and drawing helpers of the tactics board (kept apart from the component so unit tests can import them). */
import { contrastRatio, hue, inkOn, isColor, luminance, near, reach } from "@/lib/color";

/**
 * The board's own colours (K23): a light floor with ink lines, so the board reads on a phone in the
 * sun and on a projector; never the dark court of the match screens. Own players blue with white
 * numbers, opponents orange with ink numbers: they differ in hue and in lightness, so they stay apart
 * for every common colour-vision deficiency and in black and white. Every mark has an ink rim
 * (non-text contrast 3:1 against any floor colour). Contrast is checked in board-theme.test.ts.
 */
export const BOARD_THEME = {
  surround: "#d3d9de",
  floor: "#f7f5ef",
  goalArea: "#d6e4f2",
  line: "#17191c",
  own: "#1747c4",
  ownText: "#ffffff",
  opp: "#f39a3a",
  oppText: "#17191c",
  rim: "#17191c",
  ball: "#ffd23c",
  select: "#ffd23c",
  cone: "#ffffff",
} as const;

export interface BoardColours {
  own: string;
  ownText: string;
  opp: string;
  oppText: string;
}

/** light opponents, tried in this order: the board's orange, a light sky blue, white (with the ink rim) */
const OPP_CHOICES = [BOARD_THEME.opp, "#8cc8f2", "#ffffff"] as const;

/**
 * The players in the club's colour (finding A16: «Wir» was blue while the rest of the app shows
 * the own team in the club colour), under the board's rules (K23): the own mark at least 3:1 on
 * the floor, its number 4.5:1 on it, the opponent lighter than us by 3:1 and of another hue.
 * A club colour that cannot meet them (white, a pale yellow) is darkened; a grey that would only
 * read as a shade keeps the board's blue.
 */
export function boardColours(club?: string | null): BoardColours {
  let own: string = BOARD_THEME.own;
  if (isColor(club)) {
    const c = `#${club.replace("#", "").toLowerCase()}`;
    // a grey club (white, silver) would turn into a plain grey: the board's blue says «us» better
    if (hue(c) >= 0 || luminance(c) < 0.05) {
      own = contrastRatio(c, BOARD_THEME.floor) >= 3 ? c : reach(c, BOARD_THEME.floor, 3, "#000000");
      // the number on the mark reads like text
      if (contrastRatio(inkOn(own), own) < 4.5) own = reach(own, "#ffffff", 4.5, "#000000");
    }
  }
  const opp = OPP_CHOICES.find((o) => !near(o, own) && contrastRatio(o, own) >= 3 && luminance(o) > luminance(own)) ?? "#ffffff";
  return { own, ownText: inkOn(own), opp, oppText: inkOn(opp) };
}

/**
 * Who a pass goes to (finding A16: a pass could end in empty space): the teammate of the passer
 * nearest to where the line was let go, never the passer. The passer is the player the line
 * starts on, else the one holding the ball there. Without a teammate on the board: nobody.
 */
export function passReceiver<T extends { id: string; side: string; x: number; y: number }>(start: readonly [number, number], end: readonly [number, number], tokens: readonly T[], reach = 1): T | null {
  const at = (x: number, y: number) => tokens.reduce<T | null>((best, k) => (Math.hypot(k.x - x, k.y - y) <= reach && (!best || Math.hypot(k.x - x, k.y - y) < Math.hypot(best.x - x, best.y - y)) ? k : best), null);
  const passer = at(start[0], start[1]);
  let best: T | null = null;
  for (const k of tokens) {
    if (passer && (k.id === passer.id || k.side !== passer.side)) continue;
    if (!best || Math.hypot(k.x - end[0], k.y - end[1]) < Math.hypot(best.x - end[0], best.y - end[1])) best = k;
  }
  return best;
}

export const distToSegment = (p: [number, number], a: readonly [number, number], b: readonly [number, number]) => {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const l2 = dx * dx + dy * dy || 1;
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2));
  return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
};

/** Ramer-Douglas-Peucker: a drawn run as at most `max` points (the API takes 12) */
export function simplify(points: [number, number][], tolerance = 0.35, max = 12): [number, number][] {
  if (points.length <= 2) return points;
  const rdp = (pts: [number, number][], tol: number): [number, number][] => {
    if (pts.length <= 2) return pts;
    let idx = 0;
    let best = 0;
    for (let i = 1; i < pts.length - 1; i++) {
      const d = distToSegment(pts[i]!, pts[0]!, pts[pts.length - 1]!);
      if (d > best) {
        best = d;
        idx = i;
      }
    }
    if (best <= tol) return [pts[0]!, pts[pts.length - 1]!];
    return [...rdp(pts.slice(0, idx + 1), tol).slice(0, -1), ...rdp(pts.slice(idx), tol)];
  };
  let tol = tolerance;
  let out = rdp(points, tol);
  while (out.length > max) out = rdp(points, (tol *= 1.5));
  return out;
}
