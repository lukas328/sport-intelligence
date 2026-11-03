"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/client";

/** First steps with a checklist from the club's real data and a demo match (4.11). */
export function OnboardingChecklist({ orgId, teamId }: { orgId: string; teamId: string | null }) {
  const t = useTranslations("checklist");
  const router = useRouter();
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["checklist", orgId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/onboarding/checklist", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  const demo = useMutation({
    mutationFn: async () => (await api.POST("/v1/orgs/{org_id}/teams/{team_id}/demo-match", { params: { path: { org_id: orgId, team_id: teamId! } } })).data,
    onSuccess: (m) => {
      void qc.invalidateQueries({ queryKey: ["checklist", orgId] });
      if (m) router.push(`/app/${orgId}/matches/${m.id}`);
    },
  });
  const items = q.data ?? [];
  const done = items.filter((i) => i.done).length;
  if (items.length === 0 || done === items.length) return null;
  return (
    <Card className="space-y-3" data-testid="checklist">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold">{t("title")}</h2>
        <span className="text-sm text-muted tabular-nums">{t("progress", { done, total: items.length })}</span>
      </div>
      <ol className="space-y-1.5">
        {items.map((i) => (
          <li key={i.key} className="flex flex-wrap items-center gap-2 text-sm">
            <span aria-hidden className={i.done ? "text-ok" : "text-muted"}>
              {i.done ? "✓" : "○"}
            </span>
            <span className={i.done ? "text-muted line-through" : ""}>{t(`step_${i.key}` as "step_team")}</span>
            <span className="sr-only">{i.done ? t("done") : t("open")}</span>
            {!i.done && i.key === "demo" && teamId && (
              <Button variant="secondary" className="min-h-8 px-2 py-1" loading={demo.isPending} onClick={() => demo.mutate()}>
                {t("tryDemo")}
              </Button>
            )}
            {!i.done && i.link && i.key !== "demo" && (
              <Link href={i.link} className="text-accent underline underline-offset-4">
                {t("go")}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </Card>
  );
}
