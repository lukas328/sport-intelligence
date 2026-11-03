"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ChevronDown, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Button, buttonClass } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";

const HIDDEN_KEY = "hb_checklist_hidden";

/** First steps from the club's real data and a demo match (4.11): one next step, the rest folded. */
export function OnboardingChecklist({ orgId, teamId }: { orgId: string; teamId: string | null }) {
  const t = useTranslations("checklist");
  const router = useRouter();
  const qc = useQueryClient();
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    try {
      setHidden(window.localStorage.getItem(`${HIDDEN_KEY}:${orgId}`) === "1");
    } catch {
      /* storage unavailable: keep showing */
    }
  }, [orgId]);
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
  if (hidden || items.length === 0 || done === items.length) return null;
  const next = items.find((i) => !i.done && (i.link || (i.key === "demo" && teamId)));
  const action = (i: (typeof items)[number], primary: boolean) =>
    i.key === "demo" && teamId ? (
      <Button variant={primary ? "primary" : "secondary"} size="sm" loading={demo.isPending} onClick={() => demo.mutate()}>
        {t("tryDemo")}
      </Button>
    ) : i.link ? (
      <Link href={i.link} className={buttonClass(primary ? "primary" : "secondary", "sm")}>
        {t("go")}
      </Link>
    ) : null;
  return (
    <Card className="space-y-5" data-testid="checklist">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="font-semibold">{t("title")}</h2>
            <span className="text-[0.8125rem] text-muted tabular-nums">{t("progress", { done, total: items.length })}</span>
          </div>
          <div className="flex gap-1" aria-hidden>
            {items.map((i) => (
              <span key={i.key} className={cn("h-1.5 flex-1 rounded-full", i.done ? "bg-accent" : "bg-surface")} />
            ))}
          </div>
        </div>
        <button
          type="button"
          aria-label={t("hide")}
          className="-mt-1 -mr-2 grid size-8 shrink-0 place-items-center rounded-md text-muted hover:bg-surface hover:text-foreground"
          onClick={() => {
            setHidden(true);
            try {
              window.localStorage.setItem(`${HIDDEN_KEY}:${orgId}`, "1");
            } catch {
              /* ignore */
            }
          }}
        >
          <X aria-hidden className="size-4" />
        </button>
      </div>
      {next && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md bg-surface px-4 py-3">
          <p className="text-sm">
            <span className="text-muted">{t("nextStep")}: </span>
            <span className="font-semibold">{t(`step_${next.key}` as "step_team")}</span>
          </p>
          {action(next, true)}
        </div>
      )}
      <details className="group">
        <summary className="flex cursor-pointer list-none items-center gap-1.5 text-[0.8125rem] font-medium text-muted hover:text-foreground [&::-webkit-details-marker]:hidden">
          {t("allSteps")}
          <ChevronDown aria-hidden className="size-4 transition-transform group-open:rotate-180" />
        </summary>
        <ol className="mt-3 space-y-2">
          {items.map((i) => (
            <li key={i.key} className="flex flex-wrap items-center gap-3 text-sm">
              <span aria-hidden className={cn("grid size-5 place-items-center rounded-full", i.done ? "bg-accent text-accent-contrast" : "ring-1 ring-border")}>
                {i.done && <Check className="size-3" strokeWidth={3} />}
              </span>
              <span className={cn("flex-1", i.done && "text-muted line-through")}>{t(`step_${i.key}` as "step_team")}</span>
              <span className="sr-only">{i.done ? t("done") : t("open")}</span>
              {!i.done && i !== next && action(i, false)}
            </li>
          ))}
        </ol>
      </details>
    </Card>
  );
}
