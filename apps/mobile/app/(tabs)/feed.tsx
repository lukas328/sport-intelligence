import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { useSession } from "@/session";
import { Body, Button, Card, Loading, Screen } from "@/ui";

/** Player feed: matches with personal scenes (also for parents with their children). */
export default function Feed() {
  const { api, orgId, t } = useSession();
  const router = useRouter();
  const feeds = useQuery({
    queryKey: ["feeds", orgId],
    enabled: !!orgId,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/me/feeds", { params: { path: { org_id: orgId! } } })).data ?? [],
  });
  if (feeds.isLoading) return <Loading />;
  const list = feeds.data ?? [];
  return (
    <Screen>
      {list.length === 0 && <Body muted>{t("noFeed")}</Body>}
      {list.map((f) => (
        <Card key={`${f.match_id}-${f.player_id}`}>
          <Body>{t("matchAgainst", { opponent: f.opponent ?? "" })}</Body>
          <Body muted>
            {new Date(f.kickoff_at).toLocaleDateString()}
            {f.relation !== "self" ? ` · ${t("forPlayer", { name: f.player_first_name })}` : ""}
          </Body>
          <Button kind="secondary" label={t("open")} onPress={() => router.push(`/clip/${f.match_id}?player=${f.player_id}`)} />
        </Card>
      ))}
    </Screen>
  );
}
