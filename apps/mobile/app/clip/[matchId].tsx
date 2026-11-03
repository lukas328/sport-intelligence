import { useQuery } from "@tanstack/react-query";
import { Stack, useLocalSearchParams } from "expo-router";
import { useVideoPlayer, VideoView } from "expo-video";
import { useEffect } from "react";
import { API_URL, useSession } from "@/session";
import { Body, Button, Card, Loading, Screen } from "@/ui";

/** Scenes of a match in the video, from a feed or a deep link (?t=ms). */
export default function Clip() {
  const { matchId, t: start } = useLocalSearchParams<{ matchId: string; t?: string }>();
  const { api, orgId, t } = useSession();
  const path = { org_id: orgId ?? "", match_id: matchId };
  const feed = useQuery({
    queryKey: ["feed-me", matchId],
    enabled: !!orgId,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/feed/me", { params: { path } })).data ?? null,
  });
  const match = useQuery({
    queryKey: ["match", matchId],
    enabled: !!orgId,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}", { params: { path } })).data ?? null,
  });
  const videoId = feed.data?.video_id ?? match.data?.videos.find((v) => v.role === "main")?.id ?? null;
  const media = useQuery({
    queryKey: ["media-token", videoId],
    enabled: !!videoId,
    queryFn: async () =>
      (await api.POST("/v1/orgs/{org_id}/videos/{video_id}/media-token", { params: { path: { org_id: orgId!, video_id: videoId! } } })).data as
        | { base: string }
        | undefined,
  });
  const uri = media.data ? `${API_URL}${media.data.base}hls/master.m3u8` : null;
  const player = useVideoPlayer(uri ? { uri } : null, (p) => {
    p.timeUpdateEventInterval = 0;
  });
  useEffect(() => {
    const ms = Number(start ?? 0);
    if (uri && ms > 0) {
      player.currentTime = ms / 1000;
      player.play();
    }
  }, [uri, start, player]);
  const jump = (ms: number) => {
    player.currentTime = ms / 1000;
    player.play();
  };
  return (
    <Screen>
      <Stack.Screen options={{ title: match.data?.opponent?.name ?? t("clip") }} />
      {!uri ? <Loading /> : <VideoView player={player} style={{ width: "100%", aspectRatio: 16 / 9 }} nativeControls />}
      {(feed.data?.items ?? []).map((s) => (
        <Card key={s.id}>
          <Body>{s.reason}</Body>
          {s.coach_comment ? <Body muted>{s.coach_comment}</Body> : null}
          <Button kind="secondary" label={`▶ ${Math.floor(s.start_ms / 60000)}:${String(Math.floor((s.start_ms % 60000) / 1000)).padStart(2, "0")}`} onPress={() => jump(s.start_ms)} />
        </Card>
      ))}
    </Screen>
  );
}
