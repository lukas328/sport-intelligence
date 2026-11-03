import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { View } from "react-native";
import { useSession } from "@/session";
import { Body, Button, Card, Loading, Screen } from "@/ui";

/** Sessions and matches of the next 30 days; reply for yourself or your child (5.7). */
export default function Schedule() {
  const { api, orgId, t } = useSession();
  const qc = useQueryClient();
  const items = useQuery({
    queryKey: ["schedule", orgId],
    enabled: !!orgId,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/me/schedule", { params: { path: { org_id: orgId! } } })).data ?? [],
  });
  const reply = useMutation({
    mutationFn: async (v: { kind: "session" | "match"; id: string; player_id: string; response: "yes" | "no" }) =>
      api.PUT("/v1/orgs/{org_id}/me/attendance", { params: { path: { org_id: orgId! } }, body: v }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["schedule", orgId] }),
  });
  if (items.isLoading) return <Loading />;
  const list = items.data ?? [];
  return (
    <Screen>
      {list.length === 0 && <Body muted>{t("noSchedule")}</Body>}
      {list.map((i) => (
        <Card key={`${i.kind}-${i.id}-${i.player_id}`}>
          <Body>
            {i.kind === "match" ? t("matchAgainst", { opponent: i.title ?? "" }) : i.title || t("training")}
            {i.relation === "guardian" ? ` · ${t("forPlayer", { name: i.player_name })}` : ""}
          </Body>
          <Body muted>
            {i.team} · {i.starts_at ? new Date(i.starts_at).toLocaleString() : new Date(`${i.on_date}T12:00:00`).toLocaleDateString()}
          </Body>
          {i.response && <Body>{i.response === "yes" ? t("answeredYes") : t("answeredNo")}</Body>}
          <View style={{ flexDirection: "row", gap: 8 }}>
            <View style={{ flex: 1 }}>
              <Button kind={i.response === "yes" ? "primary" : "secondary"} label={t("yes")} onPress={() => reply.mutate({ kind: i.kind, id: i.id, player_id: i.player_id, response: "yes" })} />
            </View>
            <View style={{ flex: 1 }}>
              <Button kind={i.response === "no" ? "primary" : "secondary"} label={t("no")} onPress={() => reply.mutate({ kind: i.kind, id: i.id, player_id: i.player_id, response: "no" })} />
            </View>
          </View>
        </Card>
      ))}
    </Screen>
  );
}
