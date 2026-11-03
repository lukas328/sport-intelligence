/**
 * Spotlight (addendum 01, 4.2): a ring under the feet of one player that follows the track.
 * Tracks are foot points in court metres; the calibration homography maps court -> image pixels of
 * the analysed video. Between samples the position is interpolated; after a track loss the ring
 * fades out instead of jumping.
 */

export type Homography = number[][];
export interface Sample {
  t: number;
  x: number;
  y: number;
}

/** Court metres -> normalised image coordinates (0..1). */
export function project(h: Homography, x: number, y: number, size: [number, number]): [number, number] | null {
  const w = h[2]![0]! * x + h[2]![1]! * y + h[2]![2]!;
  if (Math.abs(w) < 1e-9) return null;
  const u = (h[0]![0]! * x + h[0]![1]! * y + h[0]![2]!) / w;
  const v = (h[1]![0]! * x + h[1]![1]! * y + h[1]![2]!) / w;
  return [u / size[0], v / size[1]];
}

/** Samples of one track from float32 rows [t_ms, track, x, y], sorted by time. */
export function trackSamples(rows: Float32Array, track: number): Sample[] {
  const out: Sample[] = [];
  for (let i = 0; i + 3 < rows.length; i += 4) if (rows[i + 1] === track) out.push({ t: rows[i]!, x: rows[i + 2]!, y: rows[i + 3]! });
  return out.sort((a, b) => a.t - b.t);
}

export const LOST_MS = 400; // gap after which the track counts as lost
export const FADE_MS = 300;

/** Position at time t with a visibility 0..1 (fades out after the last sample, in after a gap). */
export function positionAt(samples: Sample[], t: number): { x: number; y: number; alpha: number } | null {
  if (samples.length === 0) return null;
  let lo = 0;
  let hi = samples.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (samples[mid]!.t <= t) lo = mid;
    else hi = mid - 1;
  }
  const a = samples[lo]!;
  const b = samples[lo + 1];
  if (a.t > t) {
    const until = a.t - t;
    return until > FADE_MS ? null : { x: a.x, y: a.y, alpha: 1 - until / FADE_MS };
  }
  if (b && b.t - a.t <= LOST_MS) {
    const k = (t - a.t) / (b.t - a.t || 1);
    return { x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k, alpha: 1 };
  }
  const since = t - a.t;
  if (since <= LOST_MS / 2) return { x: a.x, y: a.y, alpha: 1 };
  const fade = 1 - (since - LOST_MS / 2) / FADE_MS;
  if (fade > 0) return { x: a.x, y: a.y, alpha: fade };
  // track found again: fade in at the new position (never slide across the court)
  if (b && b.t - t <= FADE_MS) return { x: b.x, y: b.y, alpha: 1 - (b.t - t) / FADE_MS };
  return null;
}

/** Recent path for the trail (last `ms` before t). */
export function trail(samples: Sample[], t: number, ms = 3000): Sample[] {
  return samples.filter((s) => s.t <= t && s.t >= t - ms);
}

/** Track nearest to a click (normalised image coordinates) at time t. */
export function nearestTrack(
  rows: Float32Array,
  t: number,
  h: Homography,
  size: [number, number],
  click: [number, number],
  maxDist = 0.06,
): number | null {
  let best: { d: number; id: number } | null = null;
  for (let i = 0; i + 3 < rows.length; i += 4) {
    if (Math.abs(rows[i]! - t) > 120) continue;
    const p = project(h, rows[i + 2]!, rows[i + 3]!, size);
    if (!p) continue;
    const d = Math.hypot(p[0] - click[0], p[1] - click[1]);
    if (d <= maxDist && (!best || d < best.d)) best = { d, id: rows[i + 1]! };
  }
  return best?.id ?? null;
}
