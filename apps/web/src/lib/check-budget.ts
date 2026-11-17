/** The few questions of Prüfen (second round A6): the people in the picture, bundled. */

export type PersonTrack = { track_no: number; number?: number | null; first_ms: number; last_ms: number };

const span = (t: PersonTrack) => t.last_ms - t.first_ms;

/**
 * The people to ask about: one question per person instead of one per scene. Tracks with the
 * same shirt number read by the analysis are one person; a track without a number is one person
 * of its own. Only tracks of at least `minMs`; the people seen longest first, at most `max`, each
 * group led by its longest track (the scene the question shows), in the order of the video.
 */
export function personGroups<T extends PersonTrack>(tracks: T[], minMs: number, max: number): T[][] {
  const groups = new Map<string, T[]>();
  for (const t of tracks) {
    if (span(t) < minMs) continue;
    const key = t.number != null ? `n${t.number}` : `t${t.track_no}`;
    groups.set(key, [...(groups.get(key) ?? []), t]);
  }
  const seen = (g: T[]) => g.reduce((s, t) => s + span(t), 0);
  return [...groups.values()]
    .map((g) => [...g].sort((a, b) => span(b) - span(a)))
    .sort((a, b) => seen(b) - seen(a))
    .slice(0, max)
    .sort((a, b) => a[0]!.first_ms - b[0]!.first_ms);
}

export type FileState = { state: "none" | "uploading" | "running" | "ready" | "failed" };

/** What the files of a match did together (second round A8): null for a match of one file. */
export function filesSummary(files: FileState[]): { total: number; ready: number; failed: number; running: number; uploading: number } | null {
  if (files.length < 2) return null;
  return {
    total: files.length,
    ready: files.filter((f) => f.state === "ready").length,
    failed: files.filter((f) => f.state === "failed").length,
    running: files.filter((f) => f.state === "running").length,
    uploading: files.filter((f) => f.state === "uploading").length,
  };
}
