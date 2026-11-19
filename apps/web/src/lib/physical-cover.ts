/** Below this much of the video the running figures of a team say nothing (app review BUG-11). */
export const MIN_COVERED_S = 120;

type Covered = { players: { team: string | null; duration_s: number }[]; tracks: { team: string | null; first_ms: number; last_ms: number }[] };

/**
 * The seconds of video a side's running figures cover: from the first to the last moment one of
 * its unnamed tracks is seen, at least as long as its longest named player. Not the longest single
 * track: the team row read «Erfasst 1 min · 2.29 km» for eight minutes of short tracks (BUG-11).
 */
export function teamCovered(data: Covered, pick: (team: string | null | undefined) => boolean): number {
  const tracks = data.tracks.filter((tr) => pick(tr.team));
  const span = tracks.length ? (Math.max(...tracks.map((tr) => tr.last_ms)) - Math.min(...tracks.map((tr) => tr.first_ms))) / 1000 : 0;
  const players = data.players.filter((p) => pick(p.team)).map((p) => p.duration_s);
  return Math.max(span, ...players, 0);
}
