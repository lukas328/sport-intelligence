"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { api } from "@/lib/client";
import type { KitKey } from "@/lib/kit";
import { geometryOf, type Geometry } from "@/lib/moving-camera";

type Track = Schemas["TrackOut"];

/** The analysis' team label of each kit colour (the worker gets the kits as home, away, ...). */
export const KIT_TEAM: Record<KitKey, string> = { own: "home", own_gk: "home_gk", opponent: "away", opponent_gk: "away_gk", referee: "referee" };

/** The people the analysis put in a colour, the ones seen most first: a few are enough to see a
 * wrong colour at once (a referee among the field players, the keeper in the field colour). */
export function peopleOf(tracks: readonly Track[], key: KitKey, n = 3): Track[] {
  const team = KIT_TEAM[key];
  return tracks
    .filter((tr) => tr.team === team)
    .sort((a, b) => (b.last_ms - b.first_ms) * b.observed_share - (a.last_ms - a.first_ms) * a.observed_share)
    .slice(0, n);
}

export interface KitPictures {
  video: string; // /v1/orgs/{org}/videos/{id}
  geometry: Geometry;
  chunkMs: number;
  tracks: Track[];
}

/** What the kit fields need to show the people of each colour, once the analysis is ready and
 * positions can be put on the picture; null before (the fields then are plain colours). */
export function useKitPictures(source: { orgId: string; videoId: string } | null | undefined): KitPictures | null {
  const q = useQuery({
    queryKey: ["analysis", source?.videoId],
    enabled: Boolean(source),
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/videos/{video_id}/analysis", { params: { path: { org_id: source!.orgId, video_id: source!.videoId } } })).data ?? null,
  });
  const a = q.data;
  const video = source ? `/v1/orgs/${source.orgId}/videos/${source.videoId}` : "";
  return useMemo(() => {
    if (!source || !a || a.status !== "ready" || !a.chunk_ms || !a.tracks.length) return null;
    const geometry = geometryOf(a, video);
    return geometry ? { video, geometry, chunkMs: a.chunk_ms, tracks: a.tracks } : null;
  }, [a, source, video]);
}
