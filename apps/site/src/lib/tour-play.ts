/**
 * The play beside «So sieht es in der App aus» (components/app-tour.tsx, BEFUNDE-4 U31): four
 * attackers on the half court (metres, goal at the top, like components/anlauf/court.tsx), the
 * ball goes from one to the next as the story moves on. Pure geometry and the one rule that turns
 * the scroll into a step, so text, picture and play always follow the same number.
 */

export type Pt = readonly [number, number];

/** the part of the half court the play shows: goal line to about 14 m, in metres */
export const PLAY_BOX = [-0.6, -1.2, 21.2, 15.4] as const;

/** the four players in passing order: back left, centre back, back right, right wing */
export const PLAYERS: readonly Pt[] = [
  [4.2, 9.6],
  [10, 11.2],
  [15.8, 9.6],
  [18.9, 4.4],
];

/** a 6:0 defence in front of them, drawn faintly so the court reads as a match */
export const DEFENCE: readonly Pt[] = [
  [2.6, 2.4],
  [5.2, 5.4],
  [8.4, 6.6],
  [11.6, 6.6],
  [14.8, 5.4],
  [17.4, 2.4],
];

/** a point of the court in per cent of the play's box, for the HTML laid over the drawing */
export function percent([x, y]: Pt): { left: string; top: string } {
  const [x0, y0, w, h] = PLAY_BOX;
  return { left: `${(((x - x0) / w) * 100).toFixed(3)}%`, top: `${(((y - y0) / h) * 100).toFixed(3)}%` };
}

/** the bend of a pass: the ball curves a little towards the goal, like a real one over the arms */
function control(a: Pt, b: Pt): Pt {
  const mx = (a[0] + b[0]) / 2;
  const my = (a[1] + b[1]) / 2;
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  // the normal on the side of the goal (smaller y)
  let nx = dy;
  let ny = -dx;
  if (ny > 0) {
    nx = -nx;
    ny = -ny;
  }
  const len = Math.hypot(nx, ny) || 1;
  const k = 0.16 * Math.hypot(dx, dy);
  return [mx + (nx / len) * k, my + (ny / len) * k];
}

/** the passing line from player i to player i + 1, as an SVG path */
export function passPath(i: number): string {
  const a = PLAYERS[i]!;
  const b = PLAYERS[i + 1]!;
  const c = control(a, b);
  const f = (v: number) => v.toFixed(2);
  return `M${f(a[0])} ${f(a[1])}Q${f(c[0])} ${f(c[1])} ${f(b[0])} ${f(b[1])}`;
}

function onCurve(a: Pt, c: Pt, b: Pt, t: number): Pt {
  const u = 1 - t;
  return [u * u * a[0] + 2 * u * t * c[0] + t * t * b[0], u * u * a[1] + 2 * u * t * c[1] + t * t * b[1]];
}

/**
 * The ball's way from player `from` to player `to`, along the passing lines in between (backwards
 * too, when a visitor jumps back), as points with their share of the way, for the animation.
 */
export function ballPath(from: number, to: number, samples = 10): { at: Pt; offset: number }[] {
  if (from === to) return [{ at: PLAYERS[to]!, offset: 0 }, { at: PLAYERS[to]!, offset: 1 }];
  const dir = to > from ? 1 : -1;
  const legs = Math.abs(to - from);
  const out: { at: Pt; offset: number }[] = [];
  for (let l = 0; l < legs; l++) {
    const i = from + l * dir;
    const a = PLAYERS[i]!;
    const b = PLAYERS[i + dir]!;
    // the same curve both ways
    const c = dir > 0 ? control(a, b) : control(b, a);
    for (let s = l === 0 ? 0 : 1; s <= samples; s++) {
      out.push({ at: onCurve(a, c, b, s / samples), offset: (l + s / samples) / legs });
    }
  }
  return out;
}

/**
 * The step shown for how far the stage has travelled through its track (0 at the start, 1 at the
 * end): each of the n steps gets the same stretch of scrolling.
 */
export function stepAt(progress: number, n: number): number {
  if (!(progress > 0)) return 0;
  return Math.min(n - 1, Math.floor(progress * n));
}

/** Where in the track (0 to 1) a jump to step i lands: a little inside its stretch. */
export function progressFor(i: number, n: number): number {
  return i === 0 ? 0 : (i + 0.08) / n;
}
