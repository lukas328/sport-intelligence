"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/client";
import { formatClock } from "@/lib/format";

export type EventFilter = {
  side?: "own" | "opponent";
  type?: string;
  outcome?: string;
  player_id?: string;
  number?: number;
  zone?: string;
  goal_zone?: string;
  turnover_type?: string;
};

type Ev = Schemas["EventOut"];

export function eventLabel(t: (k: string) => string, e: Ev): string {
  if (e.type === "shot") return t(e.outcome === "goal" ? "goal" : (e.outcome ?? "goal"));
  if (e.type === "turnover") return `${t("turnover")}${e.turnover_type ? ` (${t(`tt_${e.turnover_type}`)})` : ""}`;
  if (e.type === "suspension_2min") return t("suspension");
  if (e.type === "seven_meter_awarded") return t("sevenM");
  if (e.type === "timeout") return t("timeout");
  return e.type;
}

/** The events behind a number, each with a jump into the video (BRIEF: every number leads to video). */
export function EventList({
  orgId,
  matchId,
  filter,
  title,
  onPlay,
  names,
}: {
  orgId: string;
  matchId: string;
  filter: EventFilter;
  title: string;
  onPlay?: (t_ms: number) => void;
  names?: Record<string, string>;
}) {
  const t = useTranslations("events");
  const q = useQuery({
    queryKey: ["events", matchId, filter],
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/events", { params: { path: { org_id: orgId, match_id: matchId }, query: filter } }))
        .data ?? [],
  });
  return (
    <section aria-label={title} className="space-y-2" data-testid="event-list">
      <h3 className="font-semibold">{title}</h3>
      {q.data && q.data.length === 0 && <p className="text-sm text-muted">{t("none")}</p>}
      <ol className="divide-y divide-border text-sm">
        {(q.data ?? []).map((e) => (
          <li key={e.id} className="flex items-center justify-between gap-2 py-1.5">
            <span>
              <span className="font-mono text-xs text-muted">
                {e.clock_s != null ? t("at", { period: e.period, clock: formatClock(e.clock_s * 1000) }) : t("noClock")}
              </span>{" "}
              {eventLabel(t, e)}
              {e.player_id && names?.[e.player_id] ? ` · ${names[e.player_id]}` : e.number != null ? ` · #${e.number}` : ""}
              <span className="ml-2 text-xs text-muted">{t(`source_${e.source as "model"}`)}</span>
            </span>
            {e.t_ms != null && onPlay && (
              <Button variant="secondary" className="min-h-8 px-2 py-1" onClick={() => onPlay(Math.max(0, e.t_ms! - 4000))}>
                ▶ {t("play")}
              </Button>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
