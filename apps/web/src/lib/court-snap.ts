/**
 * Snapping a click onto the court line under the finger (manual calibration, line mode).
 *
 * The hall image's painted lines are thin and stand out from the floor around them: brighter, or
 * another colour. A pixel counts as line when its colour differs clearly from the mean colour of
 * its neighbourhood (11 x 11 px; a thin line is a minority there, so the mean is the floor). The
 * click moves to the nearest such pixel within the radius, then to the middle of the line there
 * (mean shift over the line pixels around it). Nothing found: the click stays where it is.
 */
export type Pt = [number, number];

/** RGBA pixels of an image region, as `ImageData` holds them; `x0`/`y0`: where it lies. */
export interface Pixels {
  data: Uint8ClampedArray | Uint8Array;
  width: number;
  height: number;
  x0?: number;
  y0?: number;
}

const BOX = 5; // half size of the neighbourhood
const CONTRAST = 42; // colour distance (0 to 441) that makes a line pixel
const CENTRE = 3; // half width of the window that finds the middle of the line

/** How far around the click the pixels are needed (radius plus the neighbourhoods). */
export const snapMargin = (radius: number) => Math.ceil(radius) + BOX + CENTRE + 2;

/** Line pixels in a region: 1 where the colour stands out from its neighbourhood. Two passes:
 * the second compares with the floor alone (the first pass's line pixels left out of the mean),
 * so the floor right beside a bright line does not count as line. */
export function lineMask(px: Pixels): Uint8Array {
  const { data, width: w, height: h } = px;
  const W = w + 1;
  let mask: Uint8Array | null = null;
  for (let pass = 0; pass < 2; pass++) {
    // integral images of r, g, b and the pixel count (floor pixels only in the second pass)
    const sum = [new Float64Array(W * (h + 1)), new Float64Array(W * (h + 1)), new Float64Array(W * (h + 1)), new Float64Array(W * (h + 1))];
    for (let y = 0; y < h; y++)
      for (let x = 0; x < w; x++) {
        const i = (y * w + x) * 4;
        const j = (y + 1) * W + x + 1;
        const use = mask && mask[y * w + x] ? 0 : 1;
        for (let c = 0; c < 4; c++) sum[c]![j] = (c < 3 ? data[i + c]! * use : use) + sum[c]![j - 1]! + sum[c]![j - W]! - sum[c]![j - W - 1]!;
      }
    const next = new Uint8Array(w * h);
    const box = (s: Float64Array, xa: number, xb: number, ya: number, yb: number) => s[yb * W + xb]! - s[ya * W + xb]! - s[yb * W + xa]! + s[ya * W + xa]!;
    for (let y = 0; y < h; y++) {
      const ya = Math.max(0, y - BOX);
      const yb = Math.min(h, y + BOX + 1);
      for (let x = 0; x < w; x++) {
        const xa = Math.max(0, x - BOX);
        const xb = Math.min(w, x + BOX + 1);
        const n = box(sum[3]!, xa, xb, ya, yb);
        if (n < 4) {
          next[y * w + x] = mask ? mask[y * w + x]! : 0;
          continue;
        }
        const i = (y * w + x) * 4;
        let d2 = 0;
        for (let c = 0; c < 3; c++) d2 += (data[i + c]! - box(sum[c]!, xa, xb, ya, yb) / n) ** 2;
        if (d2 > CONTRAST * CONTRAST) next[y * w + x] = 1;
      }
    }
    mask = next;
  }
  return mask!;
}

/**
 * The click `p` (image pixels) on the nearest line within `radius` px, in the middle of the line;
 * `p` itself when no line is near. `px` must cover `p` with `snapMargin(radius)` around it (or
 * be the whole image).
 */
export function snapToLine(px: Pixels, p: Pt, radius: number): Pt {
  const x0 = px.x0 ?? 0;
  const y0 = px.y0 ?? 0;
  const mask = lineMask(px);
  const { width: w, height: h } = px;
  const at = (x: number, y: number) => x >= 0 && y >= 0 && x < w && y < h && mask[y * w + x] === 1;
  const cx = Math.round(p[0] - x0);
  const cy = Math.round(p[1] - y0);
  const R = Math.ceil(radius);
  let best: Pt | null = null;
  let bd = radius * radius + 1e-9;
  for (let dy = -R; dy <= R; dy++)
    for (let dx = -R; dx <= R; dx++) {
      const d = dx * dx + dy * dy;
      if (d <= bd && at(cx + dx, cy + dy) && (d < bd || best == null)) {
        bd = d;
        best = [cx + dx, cy + dy];
      }
    }
  if (!best) return p;
  // mean shift: to the middle of the line pixels around (across a thick line too)
  let [mx, my] = best;
  for (let it = 0; it < 4; it++) {
    let sx = 0;
    let sy = 0;
    let n = 0;
    const rx = Math.round(mx);
    const ry = Math.round(my);
    for (let dy = -CENTRE; dy <= CENTRE; dy++)
      for (let dx = -CENTRE; dx <= CENTRE; dx++)
        if (at(rx + dx, ry + dy)) {
          sx += rx + dx;
          sy += ry + dy;
          n++;
        }
    if (!n) break;
    const [nx, ny] = [sx / n, sy / n];
    const moved = Math.hypot(nx - mx, ny - my);
    [mx, my] = [nx, ny];
    if (moved < 0.25) break;
  }
  // only across the line: along it the click stays where the finger put it (the direction of the
  // line from the spread of its pixels around the middle)
  let sxx = 0;
  let syy = 0;
  let sxy = 0;
  let n = 0;
  const S = CENTRE + 2;
  const rx = Math.round(mx);
  const ry = Math.round(my);
  for (let dy = -S; dy <= S; dy++)
    for (let dx = -S; dx <= S; dx++)
      if (at(rx + dx, ry + dy)) {
        const [ux, uy] = [rx + dx - mx, ry + dy - my];
        sxx += ux * ux;
        syy += uy * uy;
        sxy += ux * uy;
        n++;
      }
  const tr = sxx + syy;
  const disc = Math.sqrt(((sxx - syy) / 2) ** 2 + sxy * sxy);
  if (n >= 4 && disc > 0.3 * (tr / 2)) {
    // the larger eigenvalue's vector runs along the line; the normal is across
    const ang = 0.5 * Math.atan2(2 * sxy, sxx - syy);
    const [nx, ny] = [-Math.sin(ang), Math.cos(ang)];
    const off = (mx - (p[0] - x0)) * nx + (my - (p[1] - y0)) * ny;
    return [p[0] + off * nx, p[1] + off * ny];
  }
  return [mx + x0, my + y0];
}
