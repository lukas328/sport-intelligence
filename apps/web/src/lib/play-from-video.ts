import { TACTICS_FORMAT_VERSION, frameFromPositions, type PlayDoc, type Side } from "@handball/tactics";

export const FROM_VIDEO_KEY = "hb.newPlay";

interface TrackInfo {
  track_no: number;
  team: string | null;
  number?: number | null;
}

/**
 * Positions of all tracked players at `tMs` (main-video time) as the first phase of a new play.
 * Reads the 30 s binary chunk (float32 rows [t_ms, track, x, y]) and takes, per track, the row closest
 * to the moment (at most 200 ms away). Referees are left out; goalkeepers keep the label "TW".
 */
export async function playFromVideo(baseUrl: string, chunkMs: number, tMs: number, tracks: TrackInfo[]): Promise<PlayDoc | null> {
  const res = await fetch(`${baseUrl}/${Math.floor(tMs / chunkMs)}`, { credentials: "same-origin" });
  if (!res.ok) return null;
  const rows = new Float32Array(await res.arrayBuffer());
  const best = new Map<number, { d: number; x: number; y: number }>();
  for (let i = 0; i + 3 < rows.length; i += 4) {
    const d = Math.abs(rows[i]! - tMs);
    if (d > 200) continue;
    const id = rows[i + 1]!;
    const cur = best.get(id);
    if (!cur || d < cur.d) best.set(id, { d, x: rows[i + 2]!, y: rows[i + 3]! });
  }
  const team = new Map(tracks.map((t) => [t.track_no, t]));
  const points: { track: number; side: Side; x: number; y: number; gk: boolean; number: number | null }[] = [];
  for (const [id, p] of best) {
    const info = team.get(id);
    if (!info?.team || info.team === "referee") continue;
    const own = info.team.startsWith("home");
    points.push({ track: id, side: own ? "own" : "opp", x: p.x, y: p.y, gk: info.team.endsWith("_gk"), number: info.number ?? null });
  }
  if (points.length === 0) return null;
  points.sort((a, b) => (a.side === b.side ? a.track - b.track : a.side === "own" ? -1 : 1));
  const frame = frameFromPositions(points);
  frame.tokens = frame.tokens.map((tok, i) => ({ ...tok, label: points[i]!.gk ? "TW" : points[i]!.number != null ? String(points[i]!.number) : tok.label }));
  return { formatVersion: TACTICS_FORMAT_VERSION, court: "full", frames: [frame] };
}
