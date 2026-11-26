/**
 * Drawing on the picture of a moving camera (ADR 020 follow-up).
 *
 * The court calibration of a moving camera maps court metres onto the hall image (panorama), not
 * onto the frame. The analysis stores, per frame, where the camera looked: the homography hall
 * image -> frame (`GET .../views/{n}`, 30 s per file, float32 rows [t_ms, h00 .. h22], h22 = 1).
 * Court -> frame at time t is then view(t) · calibration. Between two frames the view is
 * interpolated; where the motion pass could not place the camera, nothing is drawn rather than
 * something in the wrong place.
 */
import type { Homography } from "./spotlight";

const ROW = 10;
/** two neighbouring view samples further apart than this are not interpolated (a gap) */
const MAX_SPAN_MS = 100;
/** without a neighbour, a sample this close still counts */
const NEAR_MS = 50;

export interface ViewSource {
  baseUrl: string; // .../videos/{id}/views
  frameSize: [number, number];
}

/** What an overlay needs to put court positions onto the video. */
export interface Geometry {
  homography: Homography;
  imageSize: [number, number];
  /** moving camera: court -> hall image, composed per frame with these view files */
  view?: ViewSource;
}

interface AnalysisLike {
  calibration?: { homography: number[][]; image_size: number[] } | null;
  camera?: string | null;
  chunk_ms?: number | null;
  view_chunks?: number | null;
  frame_size?: number[] | null;
  panorama?: { width: number; height: number } | null;
}

/**
 * The geometry for overlays of one analysis, or null when positions cannot be put on the
 * picture: no court, or a moving camera whose analysis has no view files yet (an analysis from
 * before, or a court in another space than the hall image).
 */
export function geometryOf(a: AnalysisLike | null | undefined, videoBase: string): Geometry | null {
  const cal = a?.calibration;
  if (!a || !cal || !a.chunk_ms || cal.image_size.length !== 2) return null;
  const imageSize = [cal.image_size[0]!, cal.image_size[1]!] as [number, number];
  if (a.camera !== "moving") return { homography: cal.homography, imageSize };
  const pano = a.panorama;
  const frame = a.frame_size;
  const onPanorama = pano && pano.width === imageSize[0] && pano.height === imageSize[1];
  if (!a.view_chunks || !frame || frame.length !== 2 || !onPanorama) return null;
  return {
    homography: cal.homography,
    imageSize,
    view: { baseUrl: `${videoBase}/views`, frameSize: [frame[0]!, frame[1]!] },
  };
}

/** a · b for 3x3 matrices. */
export function compose(a: Homography, b: Homography): Homography {
  return [0, 1, 2].map((r) => [0, 1, 2].map((c) => a[r]![0]! * b[0]![c]! + a[r]![1]! * b[1]![c]! + a[r]![2]! * b[2]![c]!));
}

function rowAt(rows: Float32Array, i: number): Homography {
  const o = i * ROW + 1;
  return [
    [rows[o]!, rows[o + 1]!, rows[o + 2]!],
    [rows[o + 3]!, rows[o + 4]!, rows[o + 5]!],
    [rows[o + 6]!, rows[o + 7]!, rows[o + 8]!],
  ];
}

/** The hall image -> frame homography at time t from one view file, or null (a gap). */
export function viewAt(rows: Float32Array, t: number): Homography | null {
  const n = Math.floor(rows.length / ROW);
  if (!n) return null;
  // last row at or before t
  let lo = 0;
  let hi = n - 1;
  if (rows[0]! > t) hi = -1;
  else
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (rows[mid * ROW]! <= t) lo = mid;
      else hi = mid - 1;
    }
  const i = hi;
  const ti = i >= 0 ? rows[i * ROW]! : -Infinity;
  const tj = i + 1 < n ? rows[(i + 1) * ROW]! : Infinity;
  if (i >= 0 && i + 1 < n && tj - ti <= MAX_SPAN_MS) {
    const f = tj > ti ? (t - ti) / (tj - ti) : 0;
    const a = rowAt(rows, i);
    const b = rowAt(rows, i + 1);
    return a.map((r, y) => r.map((v, x) => v + (b[y]![x]! - v) * f));
  }
  if (t - ti <= NEAR_MS) return rowAt(rows, i);
  if (tj - t <= NEAR_MS) return rowAt(rows, i + 1);
  return null;
}

/** View files by chunk, fetched once each; `at` answers undefined while one is loading. */
export class ViewChunks {
  private files = new Map<number, Float32Array | "loading" | "missing">();
  constructor(
    private readonly baseUrl: string,
    private readonly chunkMs: number,
    private readonly onLoad?: () => void,
  ) {}

  at(t: number): Homography | null | undefined {
    const n = Math.floor(t / this.chunkMs);
    const hit = this.files.get(n);
    if (hit instanceof Float32Array) return viewAt(hit, t);
    if (hit === "missing") return null;
    if (!hit) {
      this.files.set(n, "loading");
      void fetch(`${this.baseUrl}/${n}`, { credentials: "same-origin" })
        .then((r) => (r.ok ? r.arrayBuffer() : null))
        .catch(() => null)
        .then((buf) => {
          this.files.set(n, buf ? new Float32Array(buf) : "missing");
          this.onLoad?.();
        });
    }
    return undefined;
  }
}

/**
 * Court -> picture at time t: the calibration itself for a fixed camera, composed with where the
 * camera looked for a moving one; null where that is not known (yet).
 */
export function courtToPicture(g: Geometry, views: ViewChunks | null, t: number): { homography: Homography; size: [number, number] } | null {
  if (!g.view) return { homography: g.homography, size: g.imageSize };
  const v = views?.at(t);
  if (!v) return null;
  return { homography: compose(v, g.homography), size: g.view.frameSize };
}
