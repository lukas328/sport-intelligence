/**
 * API data of the Anlauf graphics (GET /matches/{id}/graphics and /scenes/{event}/camera) as the
 * props of components/anlauf. Nothing is added: a goal without a run is drawn as its spot only,
 * a scene without a confirmed court has no positions, the ball only where the analysis found it.
 */
import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import type { GoalRun } from "@/components/anlauf/bundle";
import type { ReportGoal } from "@/components/anlauf/charts";
import type { Pt } from "@/components/anlauf/geometry";
import type { CameraScene } from "@/components/anlauf/tactics-camera";
import { api } from "@/lib/client";

export type MatchGraphics = Schemas["MatchGraphicsOut"];
export type SceneCamera = Schemas["SceneCameraOut"];

export function goalRuns(g: MatchGraphics, team?: "own" | "opp"): (GoalRun & { eventId: string })[] {
  return g.goals
    .filter((x) => !team || x.team === team)
    .map((x) => ({
      eventId: x.event_id,
      team: x.team,
      minute: x.minute ?? undefined,
      run: x.run.map((p) => [p[0], p[1]] as Pt),
      shot: [x.shot[0], x.shot[1]] as Pt,
      aim: x.aim ? ([x.aim[0], x.aim[1]] as Pt) : null,
      confirmed: x.confirmed,
      zone: x.zone,
    }));
}

export function reportGoals(g: MatchGraphics): ReportGoal[] {
  return g.report_goals.filter((x): x is { minute: number; team: "own" | "opp" } => x.minute != null);
}

/** The tactics camera's scene, or null when there is nothing measured to show. */
export function cameraScene(s: SceneCamera, label?: string | null): CameraScene | null {
  if (!s.field_confirmed || s.tracks.length === 0 || s.clock_s == null) return null;
  return {
    clock: Math.round(s.clock_s),
    duration: s.duration_s,
    tracks: s.tracks.map((t) => ({ team: t.team, number: t.number, xy: t.xy.map((p) => [p[0], p[1]] as Pt) })),
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
