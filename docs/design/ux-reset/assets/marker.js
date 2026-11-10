/**
 * Marker strokes ("Filzstift"): hand-drawn circle, underline, highlight, strike and tick.
 * Same code as in zielbild.js, as a module to port into apps/web (e.g. components/domain/mark.tsx).
 *
 * Each stroke is a few jittered points joined by quadratic curves. The jitter comes from a
 * seeded generator, so a mark looks the same on every render (no layout shift, stable
 * screenshots) while two marks never look identical. Draw into an SVG with
 * viewBox="0 0 100 100" and preserveAspectRatio="none", stretched over the element, and set
 * vector-effect: non-scaling-stroke on the path so the line keeps its width.
 *
 * Use only where a person did something: a note, a confirmed answer, a decline, a figure the
 * coach marked. Never for text or state the system produced.
 */

/** Seeded pseudo-random numbers in [0, 1). */
export function rng(seed) {
  let s = seed >>> 0 || 1;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

/** Path data through the points, corners rounded with quadratic curves. */
export function smooth(points) {
  let d = `M${points[0][0].toFixed(1)} ${points[0][1].toFixed(1)}`;
  for (let i = 1; i < points.length - 1; i++) {
    const mx = (points[i][0] + points[i + 1][0]) / 2;
    const my = (points[i][1] + points[i + 1][1]) / 2;
    d += ` Q${points[i][0].toFixed(1)} ${points[i][1].toFixed(1)} ${mx.toFixed(1)} ${my.toFixed(1)}`;
  }
  const last = points[points.length - 1];
  return `${d} L${last[0].toFixed(1)} ${last[1].toFixed(1)}`;
}

/** Point lists in a 100 x 100 box, one function per kind of mark. */
export const MARKS = {
  /** under a word */
  under: (r) => [[2, 55 + r() * 20], [30, 38 + r() * 25], [62, 52 + r() * 25], [98, 34 + r() * 30]],
  /** highlighter behind a word: draw wide (about 9 px) in the resin yellow */
  highlight: (r) => [[1, 50 + r() * 10], [35, 46 + r() * 10], [70, 54 + r() * 8], [99, 46 + r() * 10]],
  /** around a number or a weekday: overshoots its start a little, like a real circle */
  circle: (r) => {
    const points = [];
    const n = 13;
    const start = -2.4 + r() * 0.5;
    for (let i = 0; i <= n; i++) {
      const a = start + (i / n) * Math.PI * 2.14;
      const k = 1 - i * 0.006 + (r() - 0.5) * 0.06;
      points.push([50 + Math.cos(a) * 46 * k, 50 + Math.sin(a) * 44 * k]);
    }
    return points;
  },
  /** through a jersey number: this player is out */
  strike: (r) => [[8, 78 + r() * 10], [45, 50 + r() * 8], [92, 18 + r() * 10]],
  /** in a box: a person confirmed this */
  tick: (r) => [[10, 52 + r() * 8], [36, 82 + r() * 6], [58, 44], [104, -18 + r() * 12]],
};

/** Path data for one mark. Derive the seed from something stable, e.g. the record id. */
export function markPath(kind, seed) {
  return smooth(MARKS[kind](rng(seed)));
}
