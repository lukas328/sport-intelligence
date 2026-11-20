"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/client";
import { useGoalCandidates } from "./goal-candidates";
import { useOfficialGoals } from "./official-goals";
import { useShotCandidates } from "./shot-candidates";

type Match = Schemas["MatchOut"];

/**
 * What the workbench loads for a match: notes (comments, clips, drawings), the analysis of the
 * video, the playlists, the events and the lists of the work steps. The lists share the caches of
 * their panels (same query keys).
 */
export function useWorkspaceData({
  orgId,
  match,
  videoId,
  staff,
  autoCamera,
}: {
  orgId: string;
  match: Match;
  videoId: string;
  staff: boolean;
  /** the auto camera is on with more than one camera: it needs the events too */
  autoCamera: boolean;
}) {
  const m = { org_id: orgId, match_id: match.id };
  const comments = useQuery({
    queryKey: ["comments", match.id],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/comments", { params: { path: m } })).data ?? [],
  });
  const clips = useQuery({
    queryKey: ["clips", match.id],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/clips", { params: { path: m } })).data ?? [],
  });
  const analysis = useQuery({
    queryKey: ["analysis", videoId],
    refetchInterval: (q) => (q.state.data?.status === "running" ? 10_000 : false),
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/videos/{video_id}/analysis", { params: { path: { org_id: orgId, video_id: videoId } } }))
        .data ?? null,
  });
  const annotations = useQuery({
    queryKey: ["annotations", match.id],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/annotations", { params: { path: m } })).data ?? [],
  });
  const playlists = useQuery({
    queryKey: ["playlists", match.team_id],
    enabled: staff,
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/playlists", { params: { path: { org_id: orgId, team_id: match.team_id } } }))
        .data ?? [],
  });
  const events = useQuery({
    queryKey: ["events", match.id],
    // the auto camera and the events lane of the timeline
    enabled: autoCamera || staff,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/events", { params: { path: m } })).data ?? [],
  });
  // the order of work: court, throw-off, goals, players
  const hasReport = match.report_extra?.official_report != null;
  const candidates = useGoalCandidates(orgId, match.id, staff);
  const shotCandidates = useShotCandidates(orgId, match.id, staff);
  const official = useOfficialGoals(orgId, match.id, staff && hasReport);
  return { comments, clips, analysis, annotations, playlists, events, hasReport, candidates, shotCandidates, official };
}
