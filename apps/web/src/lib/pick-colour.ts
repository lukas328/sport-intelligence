/** Colour picking from a still of the video (the kit at the upload, before any analysis). */

/** The video pixel under a point of an element showing it with object-fit: contain. */
export function videoPoint(px: number, py: number, boxW: number, boxH: number, vw: number, vh: number): { x: number; y: number } | null {
  if (!(boxW > 0 && boxH > 0 && vw > 0 && vh > 0)) return null;
  const s = Math.min(boxW / vw, boxH / vh);
  const ox = (boxW - vw * s) / 2;
  const oy = (boxH - vh * s) / 2;
  const x = (px - ox) / s;
  const y = (py - oy) / s;
  if (x < 0 || y < 0 || x >= vw || y >= vh) return null; // on the black bars
  return { x: Math.floor(x), y: Math.floor(y) };
}

/** The mean colour of RGBA pixels as #rrggbb (a few pixels around the tap: one pixel is noise);
 * null without pixels. */
export function meanHex(data: Uint8ClampedArray | number[]): string | null {
  let r = 0;
  let g = 0;
  let b = 0;
  let n = 0;
  for (let i = 0; i + 3 < data.length; i += 4) {
    r += data[i]!;
    g += data[i + 1]!;
    b += data[i + 2]!;
    n++;
  }
  if (!n) return null;
  const hex = (v: number) => Math.round(v / n).toString(16).padStart(2, "0");
  return `#${hex(r)}${hex(g)}${hex(b)}`;
}
