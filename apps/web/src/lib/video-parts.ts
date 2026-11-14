/**
 * One match in several files (Q-VIDEO-PARTS): the first half and the second half, or a recording
 * the phone split. The API places the parts one after the other on the match's time and plays them
 * as one video from the first part; here is what the screens need of that.
 */

export interface PartVideo {
  id: string;
  role: string;
  status: string;
  filename: string;
  duration_s: number | null;
  part?: number | null;
  part_start_ms?: number | null;
  duplicate_of?: string | null;
  error?: string | null;
}

export interface PartJob {
  id: string;
  kind: string;
  status: string;
  progress: number;
  video_asset_id: string | null;
}

/** A part this short was started by mistake (a pocket, a wrong tap). */
export const SHORT_PART_S = 60;

/** The main files of the match that are its parts, in their order. */
export function partsOf<V extends PartVideo>(videos: V[]): V[] {
  return videos.filter((v) => v.role === "main" && v.part != null).sort((a, b) => (a.part ?? 0) - (b.part ?? 0));
}

/** The main files the coach sees in the list: the parts, then files still on their way, copies and
 * failed ones (in upload order, as the API sends them). */
export function mainFiles<V extends PartVideo>(videos: V[]): V[] {
  const parts = partsOf(videos);
  return [...parts, ...videos.filter((v) => v.role === "main" && v.part == null)];
}

/**
 * The video the match plays: the first part, its length that of the whole match (all parts one
 * after the other). Without parts yet, the first main file that plays.
 */
export function timelineVideo<V extends PartVideo>(videos: V[]): V | undefined {
  const parts = partsOf(videos);
  const first = parts.find((v) => v.status === "ready") ?? videos.find((v) => v.role === "main" && v.status === "ready");
  if (!first || parts.length < 2 || first.id !== parts[0]!.id) return first;
  const known = parts.every((p) => p.duration_s != null);
  return { ...first, duration_s: known ? parts.reduce((s, p) => s + (p.duration_s ?? 0), 0) : first.duration_s };
}

/** Where each further part starts in the match video (the line between the halves). */
export function partStarts(videos: PartVideo[]): { part: number; start_ms: number; video_id: string }[] {
  return partsOf(videos)
    .filter((v) => (v.part ?? 0) > 1 && v.part_start_ms != null)
    .map((v) => ({ part: v.part!, start_ms: v.part_start_ms!, video_id: v.id }));
}

/** The part a time of the match video lies in, and the time in that file. */
export function partAt<V extends PartVideo>(videos: V[], ms: number): { video: V; local_ms: number } | null {
  const parts = partsOf(videos).filter((v) => v.part_start_ms != null);
  if (parts.length === 0) return null;
  let hit = parts[0]!;
  for (const p of parts) if (ms >= (p.part_start_ms ?? 0)) hit = p;
  return { video: hit, local_ms: ms - (hit.part_start_ms ?? 0) };
}

/** How a part is called: «1. Halbzeit» and «2. Halbzeit» for two, «Teil 3» for more. */
export type PartName = { key: "half" | "part"; n: number };

export function partName(n: number, total: number): PartName {
  return total === 2 ? { key: "half", n } : { key: "part", n };
}

export type PartState =
  | { kind: "uploading" }
  | { kind: "processing" }
  | { kind: "analysing"; progress: number }
  | { kind: "ready" }
  | { kind: "notAnalysed" }
  | { kind: "analysisFailed" }
  | { kind: "fileFailed" }
  | { kind: "duplicate" };

/** What a file of the match is doing, in the coach's words (the latest job of each kind). */
export function partState(v: PartVideo, jobs: PartJob[]): PartState {
  if (v.duplicate_of) return { kind: "duplicate" };
  if (v.status === "failed") return { kind: "fileFailed" };
  if (v.status === "uploading") return { kind: "uploading" };
  if (v.status !== "ready") return { kind: "processing" };
  const analysis = jobs.find((j) => j.video_asset_id === v.id && j.kind === "analysis");
  if (!analysis) return { kind: "notAnalysed" };
  if (analysis.status === "failed") return { kind: "analysisFailed" };
  if (analysis.status === "succeeded") return { kind: "ready" };
  return { kind: "analysing", progress: analysis.progress };
}

export function isShort(v: PartVideo): boolean {
  return v.duration_s != null && v.duration_s < SHORT_PART_S;
}

/** The newest job of each file and kind (the API sends the newest first): an analysis that failed
 * and then ran again shows its new run, not the old failure. */
export function latestJobs<J extends PartJob>(jobs: J[]): J[] {
  const seen = new Set<string>();
  return jobs.filter((j) => {
    const key = `${j.video_asset_id ?? ""}:${j.kind}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/** Several files chosen at once go up in the order they were recorded: the time the phone last
 * wrote each file, then the name (IMG_0412 before IMG_0413). The API orders by the camera clock in
 * the file when it can read it. */
export function recordingOrder<F extends { name: string; lastModified: number }>(files: F[]): F[] {
  return [...files].sort((a, b) => a.lastModified - b.lastModified || a.name.localeCompare(b.name, undefined, { numeric: true }));
}
