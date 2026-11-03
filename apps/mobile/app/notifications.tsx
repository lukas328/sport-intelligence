import { parse } from "@handball/client-core";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { pathFor } from "@/routes";
import { useSession } from "@/session";
import { Body, Button, Card, Loading, Screen } from "@/ui";

export default function Notifications() {
  const { api, orgId, t } = useSession();
  const router = useRouter();
  const list = useQuery({
    queryKey: ["notifications", orgId],
    enabled: !!orgId,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/me/notifications", { params: { path: { org_id: orgId! } } })).data,
  });
  if (list.isLoading) return <Loading />;
  const items = list.data?.items ?? [];
  return (
    <Screen>
      {items.length === 0 && <Body muted>{t("noNotifications")}</Body>}
      {items.map((n) => (
        <Card key={n.id}>
          <Body>{n.kind}</Body>
          <Body muted>{new Date(n.created_at).toLocaleString()}</Body>
          {n.link ? <Button kind="secondary" label={t("open")} onPress={() => router.push(pathFor(parse(n.link)))} /> : null}
        </Card>
      ))}
    </Screen>
  );
}
