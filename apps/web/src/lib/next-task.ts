/**
 * The one next task at the top of a match page (Lukas' notes L5, 19.11.2026: «what do I have to
 * do here?»): open questions first, then the missing shot spots, then the video; before the match
 * the preparation. Nothing while the analysis runs (its progress says so) or when all is done.
 */
export type NextTask =
  | { kind: "checks"; n: number }
  | { kind: "spots"; n: number }
  | { kind: "upload" }
  | { kind: "prepare" }
  | null;

export function nextTask(m: {
  staff: boolean;
  example: boolean;
  upcoming: boolean;
  hasOpponent: boolean;
  running: boolean;
  checks: number;
  spotsMissing: number;
  hasVideo: boolean;
  /** a match made from a paper report has no video to ask for */
  paper: boolean;
}): NextTask {
  if (!m.staff || m.example) return null;
  if (m.upcoming) return m.hasOpponent ? { kind: "prepare" } : null;
  if (m.running) return null;
  if (m.checks > 0) return { kind: "checks", n: m.checks };
  if (m.spotsMissing > 0) return { kind: "spots", n: m.spotsMissing };
  if (!m.hasVideo && !m.paper) return { kind: "upload" };
  return null;
}
