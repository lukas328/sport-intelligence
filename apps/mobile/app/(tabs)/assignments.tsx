import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "@/session";
import { Body, Button, Card, Loading, Screen } from "@/ui";

export default function Assignments() {
  const { api, orgId, t } = useSession();
  const qc = useQueryClient();
  const list = useQuery({
    queryKey: ["my-assignments", orgId],
    enabled: !!orgId,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/me/assignments", { params: { path: { org_id: orgId! } } })).data ?? [],
  });
  const done = useMutation({
    mutationFn: async (id: string) =>
      api.PUT("/v1/orgs/{org_id}/assignments/{assignment_id}/status", { params: { path: { org_id: orgId!, assignment_id: id } }, body: { done: true } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["my-assignments", orgId] }),
  });
  if (list.isLoading) return <Loading />;
  const items = list.data ?? [];
  return (
    <Screen>
      {items.length === 0 && <Body muted>{t("noAssignments")}</Body>}
      {items.map((a) => (
        <Card key={a.id}>
          <Body>{a.title}</Body>
          {a.note ? <Body muted>{a.note}</Body> : null}
          <Button kind="secondary" label={t("done")} disabled={!!a.done_at} onPress={() => done.mutate(a.id)} />
        </Card>
      ))}
    </Screen>
  );
}
