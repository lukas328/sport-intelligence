import { flush, mark, pending } from "@handball/client-core";
import { useQuery } from "@tanstack/react-query";
import * as Haptics from "expo-haptics";
import { useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { View } from "react-native";
import { fileStore } from "@/file-store";
import { useSession } from "@/session";
import { Body, Button, Screen } from "@/ui";

/** Big buttons with device time, offline first (5.3); synced to the video after the analysis. */
export default function Marks() {
  const { matchId } = useLocalSearchParams<{ matchId: string }>();
  const { api, orgId, t } = useSession();
  const session = useRef<string | null>(null);
  const [open, setOpen] = useState(0);
  const [half, setHalf] = useState(1);
  const [last, setLast] = useState<string | null>(null);
  const match = useQuery({
    queryKey: ["match", matchId],
    enabled: !!orgId,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}", { params: { path: { org_id: orgId!, match_id: matchId } } })).data ?? null,
  });
  const keys = useQuery({
    queryKey: ["mark-keys", match.data?.team_id],
    enabled: !!match.data,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/mark-keys", { params: { path: { org_id: orgId!, team_id: match.data!.team_id } } })).data ?? [],
  });
  const sync = useCallback(async () => {
    if (!orgId) return;
    if (!session.current) session.current = fileStore.getItem(`hb.marks.session.${matchId}`);
    if (!session.current) {
      const r = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/mark-sessions", { params: { path: { org_id: orgId, match_id: matchId } }, body: { device: "app" } });
      if (!r.data) return;
      session.current = r.data.id;
      fileStore.setItem(`hb.marks.session.${matchId}`, r.data.id);
    }
    const sid = session.current;
    const left = await flush(fileStore, matchId, async (marks) => {
      const r = await api.POST("/v1/orgs/{org_id}/mark-sessions/{session_id}/marks", { params: { path: { org_id: orgId, session_id: sid } }, body: { marks } });
      return { ok: !!r.data, stored: r.data ? (r.data as { stored: { client_id: string }[] }).stored.map((s) => s.client_id) : [] };
    });
    setOpen(left);
  }, [api, orgId, matchId]);
  useEffect(() => {
    setOpen(pending(fileStore, matchId).length);
    const id = setInterval(() => void sync().catch(() => null), 15000);
    return () => clearInterval(id);
  }, [matchId, sync]);
  const tap = (key: string, label: string) => {
    mark(fileStore, matchId, key);
    if (key === "halftime") setHalf(2);
    setLast(label);
    setOpen(pending(fileStore, matchId).length);
    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    void sync().catch(() => null);
  };
  return (
    <Screen>
      <Body muted>{open > 0 ? t("pending", { n: open }) : t("synced")}</Body>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
        {(keys.data ?? []).map((k) => {
          const label = k.label || t(`key_${k.key}` as "key_good");
          return (
            <View key={k.key} style={{ width: "48%" }}>
              <Button big kind="secondary" color={k.color ?? undefined} label={label} onPress={() => tap(k.key, label)} />
            </View>
          );
        })}
      </View>
      <Button kind="secondary" label={t("halftime")} disabled={half === 2} onPress={() => tap("halftime", t("halftime"))} />
      {last && <Body>{last}</Body>}
    </Screen>
  );
}
