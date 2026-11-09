"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ChevronDown, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Button, buttonClass } from "@/components/ui/button";
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
      <Button variant={primary ? "secondary" : "ghost"} size="sm" loading={demo.isPending} onClick={() => demo.mutate()}>
        {t("tryDemo")}
      </Button>
    ) : i.link ? (
      <Link href={i.link} className={buttonClass(primary ? "secondary" : "ghost", "sm")}>
        {t("go")}
      </Link>
    ) : null;
  return (
    <section className="space-y-3 border-y border-foreground/15 py-4" data-testid="checklist" aria-labelledby="checklist-title">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
        <p className="font-score text-[2.25rem] leading-none tabular-nums" aria-hidden>
          {done}
          <span className="text-muted">/{items.length}</span>
        </p>
        <div className="min-w-0 flex-1">
          <h2 id="checklist-title" className="font-sans text-sm font-semibold text-muted">
            {t("title")} <span className="sr-only">{t("progress", { done, total: items.length })}</span>
          </h2>
          {next && (
            <p className="font-semibold">
              <span className="sr-only">{t("nextStep")}: </span>
              {t(`step_${next.key}` as "step_team")}
            </p>
          )}
        </div>
        {next && action(next, true)}
        <button
          type="button"
          aria-label={t("hide")}
          className="grid size-8 shrink-0 place-items-center rounded-md text-muted hover:bg-surface hover:text-foreground"
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
    </section>
  );
}
