/**
 * API data of the Anlauf graphics (GET /matches/{id}/graphics and /scenes/{event}/camera) as the
 * props of components/anlauf. Nothing is added: a goal without a run is drawn as its spot only,
 * a scene without a confirmed court has no positions, the ball only where the analysis found it.
 */
import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import type { GoalRun } from "@/components/anlauf/bundle";
import type { ReportGoal } from "@/components/anlauf/charts";
import { type Pt, ZONE_AT } from "@/components/anlauf/geometry";
import type { CameraScene } from "@/components/anlauf/tactics-camera";
import { api } from "@/lib/client";

export type MatchGraphics = Schemas["MatchGraphicsOut"];
export type SceneCamera = Schemas["SceneCameraOut"];

/**
 * The goals that can be drawn: those with a shot spot, or with a place the coach gave without a
 * point (tapped by keyboard, «Gegenstoss»): drawn at the zone's point, counted in the three things
 * (fourth real-video test H7). A confirmed goal without either counts in the score, the course and
 * the goal list (`spotless`), not in bundles and Minifelder (real-video test E01).
 */
export function goalRuns(g: MatchGraphics, team?: "own" | "opp"): (GoalRun & { eventId: string })[] {
  return spreadSpots(goalRunsAsGiven(g, team));
}

const SPREAD_M = 1.1; // distance between goals that share one point, in metres of the half court

/**
 * Goals on the same point (several drawn at their zone's point, or tapped on the same spot) are
 * set apart in a small ring, fixed by their order (event id), so three goals read as three dots
 * and the numeral above matches the picture. Only goals without a run move: a run ends where it
 * ends.
 */
export function spreadSpots<T extends GoalRun & { eventId: string }>(runs: T[]): T[] {
  const groups = new Map<string, T[]>();
  for (const r of runs) {
    if (r.run.length > 1) continue;
    const key = `${Math.round(r.shot[0] * 4)}:${Math.round(r.shot[1] * 4)}`;
    groups.set(key, [...(groups.get(key) ?? []), r]);
  }
  const moved = new Map<T, Pt>();
  for (const list of groups.values()) {
    if (list.length < 2) continue;
    const sorted = [...list].sort((a, b) => a.eventId.localeCompare(b.eventId));
    sorted.forEach((r, i) => {
      const angle = -Math.PI / 2 + (2 * Math.PI * i) / sorted.length;
      const radius = SPREAD_M * (sorted.length > 6 ? 1.6 : 1);
      moved.set(r, [Math.min(20, Math.max(0, r.shot[0] + radius * Math.cos(angle))), Math.max(0.3, r.shot[1] + radius * Math.sin(angle))]);
    });
  }
  return runs.map((r) => (moved.has(r) ? { ...r, shot: moved.get(r)! } : r));
}

/**
 * The zone a goal counts with: only a place a person gave (real-clip test of «Von wo?», V1). An
 * estimated spot is still drawn (hollow, «geschätzt») but counts in no thing and no zone tally.
 */
export function coachZone(x: Pick<MatchGraphics["goals"][number], "zone" | "by_coach">): string | null {
  return x.by_coach === true ? (x.zone ?? null) : null;
}

function goalRunsAsGiven(g: MatchGraphics, team?: "own" | "opp"): (GoalRun & { eventId: string })[] {
  return g.goals
    .filter((x) => (x.shot != null || (coachZone(x) != null && ZONE_AT[coachZone(x)!] != null)) && (!team || x.team === team))
    .map((x) => ({
      eventId: x.event_id,
      team: x.team,
      minute: x.minute ?? undefined,
      run: x.run.map((p) => [p[0], p[1]] as Pt),
      shot: (x.shot ? [x.shot[0], x.shot[1]] : ZONE_AT[coachZone(x)!]!) as Pt,
      aim: x.aim ? ([x.aim[0], x.aim[1]] as Pt) : null,
      // an estimate is never a coach's spot: hollow in the drawing
      confirmed: x.confirmed && x.by_coach === true,
      zone: coachZone(x),
    }));
}

/** Goals without a shot spot: counted and listed, said honestly where drawings would be. */
export function spotless(g: MatchGraphics, team?: "own" | "opp"): MatchGraphics["goals"] {
  return g.goals.filter((x) => x.shot == null && coachZone(x) == null && (!team || x.team === team));
}

/** The score the video's goals give, when the match itself has none (real-video test E10). */
export function videoScore(g: MatchGraphics): { own: number; opp: number } | null {
  const seen = videoGoals(g);
  if (seen.length === 0) return null;
  return { own: seen.filter((x) => x.team === "own").length, opp: seen.filter((x) => x.team === "opp").length };
}

/**
 * Goal moments still open in Prüfen, the most important and the further ones: while there are
 * any, the score from the video is an interim one (third real-video test G1).
 */
export function openMoments(g: MatchGraphics): number {
  return g.checks.filter((c) => c.kind === "goal").length + (g.more_checks ?? []).length;
}

/** The count next to «Prüfen»: the most important questions, then the further moments. */
export function checkCount(g: MatchGraphics): number {
  return g.checks.length > 0 ? g.checks.length : (g.more_checks ?? []).length;
}

/** The goals that have a place in the video (confirmed there or pinned to it). */
export function videoGoals(g: MatchGraphics): MatchGraphics["goals"] {
  return g.goals.filter((x) => x.has_video);
}

export function reportGoals(g: MatchGraphics): ReportGoal[] {
  return g.report_goals.filter((x): x is { minute: number; team: "own" | "opp" } => x.minute != null);
}

/** The tactics camera's scene, or null when there is nothing measured to show. */
export function cameraScene(s: SceneCamera, label?: string | null): CameraScene | null {
  // positions as soon as the court is confirmed and the scene has tracks; without the throw-off
  // the clock is the video time (real-video test E02), never «no positions» when there are some
  if (!s.field_confirmed || s.tracks.length === 0) return null;
  const videoTime = s.clock_s == null;
  return {
    clock: Math.round(s.clock_s ?? s.video_s ?? 0),
    videoTime,
    duration: s.duration_s,
    tracks: s.tracks.map((t) => ({ team: t.team, number: t.number, xy: t.xy.map((p) => [p[0], p[1]] as Pt), ts: t.ts ?? null })),
    right: s.right ?? false,
    ball: s.ball.map((b) => ({ from: b.from_s, to: b.to_s, team: b.team, number: b.number })),
    scorer: s.scorer,
    shot: s.shot ? ([s.shot[0], s.shot[1]] as Pt) : null,
    aim: null,
    confirmed: s.confirmed,
    label: label ?? null,
  };
}

export function useMatchGraphics(orgId: string, matchId: string) {
  return useQuery({
    queryKey: ["graphics", matchId],
    enabled: matchId !== "",
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/graphics", { params: { path: { org_id: orgId, match_id: matchId } } })).data ?? null,
    staleTime: 60_000,
  });
}

export function useSceneCamera(orgId: string, matchId: string, eventId: string | null) {
  return useQuery({
    queryKey: ["scene-camera", matchId, eventId],
    enabled: eventId != null,
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/scenes/{event_id}/camera", { params: { path: { org_id: orgId, match_id: matchId, event_id: eventId! } } })).data ?? null,
    staleTime: 300_000,
  });
}

/**
 * The scenes of thing `n` (1 to 3, as in ?thing=n): exactly its goals that have a video time,
 * in the order of the match, no other goal of the window (UX test B01).
 */
export function thingSequence(g: MatchGraphics, n: number, things: { goals: { eventId?: string }[] }[]): MatchGraphics["goals"] {
  const thing = things[n - 1];
  if (!thing) return [];
  const playable = g.goals.filter((x) => (x.has_video || x.source === "demo") && x.t_ms != null);
  const ids = new Set(thing.goals.map((x) => x.eventId).filter(Boolean));
  return playable.filter((x) => ids.has(x.event_id)).sort((a, b) => (a.t_ms ?? 0) - (b.t_ms ?? 0));
}
