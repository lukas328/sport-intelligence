"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card, EmptyState } from "@/components/ui/card";
import { api } from "@/lib/client";

type Item = Schemas["ScheduleItem"];

/** Players and parents reply to sessions and matches (addendum 01, 5.7). */
export function ScheduleView({ orgId }: { orgId: string }) {
  const t = useTranslations("schedule");
  const format = useFormatter();
  const qc = useQueryClient();
  const items = useQuery({
    queryKey: ["schedule", orgId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/me/schedule", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  const reply = useMutation({
    mutationFn: async ({ item, response }: { item: Item; response: "yes" | "no" }) =>
      api.PUT("/v1/orgs/{org_id}/me/attendance", {
        params: { path: { org_id: orgId } },
        body: { kind: item.kind, id: item.id, player_id: item.player_id, response },
      }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["schedule", orgId] }),
  });
  const list = items.data ?? [];
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="text-sm text-muted">{t("hint")}</p>
      </div>
      {list.length === 0 ? (
        <EmptyState title={items.isLoading ? "…" : t("none")} />
      ) : (
        <ul className="space-y-2" data-testid="schedule">
          {list.map((i) => {
            const self = i.relation === "self";
            return (
              <li key={`${i.kind}-${i.id}-${i.player_id}`}>
                <Card className="flex flex-wrap items-center gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">
                      {i.kind === "match" ? t("match", { opponent: i.title ?? "" }) : i.title || t("training")}
                      {!self && <span className="text-muted"> {t("for", { name: i.player_name })}</span>}
                    </p>
                    <p className="text-sm text-muted">
                      {i.team} ·{" "}
                      {i.starts_at
                        ? format.dateTime(new Date(i.starts_at), { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })
                        : format.dateTime(new Date(`${i.on_date}T12:00:00`), { weekday: "short", day: "numeric", month: "short" })}
                    </p>
                  </div>
                  {i.response && <span className="text-sm">{t(`answered_${i.response}`)}</span>}
                  <div className="flex gap-2">
                    <Button
                      variant={i.response === "yes" ? "primary" : "secondary"}
                      aria-pressed={i.response === "yes"}
                      onClick={() => reply.mutate({ item: i, response: "yes" })}
                    >
                      {self ? t("yes") : t("forYes")}
                    </Button>
                    <Button
                      variant={i.response === "no" ? "primary" : "secondary"}
                      aria-pressed={i.response === "no"}
                      onClick={() => reply.mutate({ item: i, response: "no" })}
                    >
                      {self ? t("no") : t("forNo")}
                    </Button>
                  </div>
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
