"use client";

import { focusForInsight } from "@handball/tactics";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/client";
import { problemCode } from "@handball/api-client";
import { cn } from "@/lib/utils";
import type { EventFilter } from "./event-list";

interface Insight {
  id: string;
  kind: "strength" | "weakness" | "info";
  key: string;
  params: Record<string, string | number | null>;
  score: number;
  sample: number;
  evidence: EventFilter;
}
interface InsightsData {
  version: string;
  baseline_matches: number;
  insights: Insight[];
  summary: { text: string; model: string; created_at: string } | null;
}

/** Ranked insights with evidence (every statement opens the events behind it) and an optional summary. */
export function InsightsCard({
  orgId,
  matchId,
  names,
  staff,
  onEvidence,
}: {
  orgId: string;
  matchId: string;
  names: Record<string, string>;
  staff: boolean;
  onEvidence: (title: string, filter: EventFilter) => void;
}) {
  const t = useTranslations("insights");
  const tz = useTranslations("zones");
  const tg = useTranslations("goalZones");
  const te = useTranslations("events");
  const qc = useQueryClient();
  const [problem, setProblem] = useState<string | null>(null);
  const path = { org_id: orgId, match_id: matchId };
  const q = useQuery({
    queryKey: ["insights", matchId],
    queryFn: async () => ((await api.GET("/v1/orgs/{org_id}/matches/{match_id}/insights", { params: { path } })).data ?? null) as InsightsData | null,
  });
  const summarise = useMutation({
    mutationFn: async () => {
      const { error } = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/summary", { params: { path } });
      if (error) throw error;
    },
    onSuccess: () => (setProblem(null), void qc.invalidateQueries({ queryKey: ["insights", matchId] })),
    onError: (e) => setProblem(problemCode(e) ?? "generic"),
  });
  const data = q.data;
  if (!data) return null;

  function text(i: Insight): string {
    const p = { ...i.params } as Record<string, string | number>;
    const pid = i.params.player_id as string | null | undefined;
    p.who = (pid && names[pid]) || (i.params.number != null ? t("player", { number: i.params.number }) : "?");
    if (typeof p.zone === "string") p.zone = p.zone.length === 2 ? tg(p.zone as "TL") : tz(p.zone as "wing_left");
    if (typeof p.type === "string") p.type = te(`tt_${p.type}` as "tt_other");
    if (typeof p.gsax === "number") p.gsax = Math.abs(p.gsax).toFixed(1);
    delete p.player_id;
    delete p.number;
    return t(i.key.replace("insights.", "") as "drought", p as never);
  }

  return (
    <Card className="space-y-3" data-testid="insights">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-semibold">{t("title")}</h2>
        <p className="text-xs text-muted">{t("baseline", { count: data.baseline_matches })}</p>
      </div>
      {data.insights.length === 0 ? (
        <p className="text-sm text-muted">{t("none")}</p>
      ) : (
        <ul className="space-y-2">
          {data.insights.map((i) => (
            <li key={i.id} className="flex flex-wrap items-start gap-2 text-sm">
              <span
                className={cn(
                  "mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-xs font-medium",
                  i.kind === "strength" ? "border border-ok text-foreground" : i.kind === "weakness" ? "border border-error text-foreground" : "bg-surface",
                )}
              >
                {t(i.kind)}
              </span>
              <span className="min-w-0 flex-1">{text(i)}</span>
              <button className="text-xs text-accent underline" onClick={() => onEvidence(text(i), i.evidence)}>
                {t("evidence")}
              </button>
              {i.kind === "weakness" && focusForInsight(i.key, i.params.zone as string | null).length > 0 && (
                <Link className="text-xs text-accent underline" href={`/app/${orgId}/drills?focus=${focusForInsight(i.key, i.params.zone as string | null).join(",")}`}>
                  {t("drills")}
                </Link>
              )}
            </li>
          ))}
        </ul>
      )}
      {data.summary && (
        <div className="space-y-1 rounded bg-surface p-3 text-sm" data-testid="summary">
          <p className="whitespace-pre-line">{data.summary.text}</p>
          <p className="text-xs text-muted">{t("summaryGenerated")}</p>
        </div>
      )}
      {staff && data.insights.length > 0 && !data.summary && (
        <Button variant="secondary" disabled={summarise.isPending} onClick={() => summarise.mutate()}>
          {t("summarise")}
        </Button>
      )}
      {problem && (
        <p className="text-sm text-muted" aria-live="polite">
          {problem === "text-unavailable" ? t("summaryUnavailable") : t("summaryRejected")}
        </p>
      )}
      <p className="text-xs text-muted">{t("hint")}</p>
    </Card>
  );
}
