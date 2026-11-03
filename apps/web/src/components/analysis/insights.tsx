"use client";

import { drillsFor, focusForInsight } from "@handball/tactics";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/client";
import { problemCode } from "@handball/api-client";
import { toDrillItem } from "@/lib/drill-snapshot";
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
              {staff && i.kind === "weakness" && focusForInsight(i.key, i.params.zone as string | null).length > 0 && (
                <TrainFromInsight orgId={orgId} matchId={matchId} insight={i} label={text(i)} />
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

/** From a problem to training (addendum 01, 5.6): session, evidence playlist, assignment. */
function TrainFromInsight({ orgId, matchId, insight, label }: { orgId: string; matchId: string; insight: Insight; label: string }) {
  const t = useTranslations("insights");
  const locale = useLocale();
  const [open, setOpen] = useState(false);
  const suggestions = drillsFor(focusForInsight(insight.key, insight.params.zone as string | null)).slice(0, 4);
  const [chosen, setChosen] = useState<string[]>(suggestions.slice(0, 2).map((d) => d.id));
  const nextWeek = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
  const [day, setDay] = useState(nextWeek);
  const [playlist, setPlaylist] = useState(true);
  const [assignment, setAssignment] = useState(false);
  const create = useMutation({
    mutationFn: async () => {
      const r = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/focus", {
        params: { path: { org_id: orgId, match_id: matchId } },
        body: {
          insight_key: insight.key,
          params: insight.params,
          title: label.slice(0, 200),
          session: { on_date: day, drills: suggestions.filter((d) => chosen.includes(d.id)).map((d) => toDrillItem(d, locale)) },
          playlist,
          assignment: playlist && assignment,
        },
      });
      if (r.error) throw r.error;
      return r.data;
    },
  });
  if (!open)
    return (
      <button type="button" className="text-xs text-accent underline" onClick={() => setOpen(true)}>
        {t("train")}
      </button>
    );
  return (
    <div className="mt-2 w-full space-y-2 rounded border border-border p-3" role="group" aria-label={t("trainTitle")}>
      <p className="font-medium">{t("trainTitle")}</p>
      {create.data ? (
        <p className="text-sm">
          {t("trainDone")}{" "}
          <Link className="text-accent underline" href={`/app/${orgId}/teams/${create.data.team_id}/training`}>
            {t("trainOpen")}
          </Link>
        </p>
      ) : (
        <>
          <label className="block text-sm">
            {t("trainDate")}{" "}
            <input type="date" value={day} onChange={(e) => setDay(e.target.value)} className="rounded border border-border bg-background px-2" />
          </label>
          <fieldset className="text-sm">
            <legend>{t("trainDrills")}</legend>
            {suggestions.map((d) => (
              <label key={d.id} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={chosen.includes(d.id)}
                  onChange={() => setChosen((c) => (c.includes(d.id) ? c.filter((x) => x !== d.id) : [...c, d.id]))}
                />
                {toDrillItem(d, locale).name} ({d.minutes} min)
              </label>
            ))}
          </fieldset>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={playlist} onChange={(e) => setPlaylist(e.target.checked)} />
            {t("trainPlaylist")}
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={assignment} disabled={!playlist} onChange={(e) => setAssignment(e.target.checked)} />
            {t("trainAssignment")}
          </label>
          <Button disabled={create.isPending} onClick={() => create.mutate()}>
            {t("trainCreate")}
          </Button>
        </>
      )}
    </div>
  );
}

