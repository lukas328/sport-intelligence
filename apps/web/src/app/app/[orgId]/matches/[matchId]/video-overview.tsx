"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { buttonClass } from "@/components/ui/button";
import { Sheet } from "@/components/ui/card";
import { api } from "@/lib/client";
import { formatClock } from "@/lib/format";
import { cn } from "@/lib/utils";

type Phase = { side: "own" | "opponent"; start_ms: number; end_ms: number; outcome: string | null };
type Possessions = { phases: Phase[]; summary: Record<"own" | "opponent", { count: number; avg_s: number; share: number }>; estimated: boolean };

/**
 * What a match video gives without any tagging (ADR 025): possession phases from the players'
 * positions, the way to the physical load, and the next step for shots and goals.
 */
export function VideoOverview({
  orgId,
  matchId,
  teamId,
  ownName,
  oppName,
  durationMs,
  onPlay,
  onPhysical,
  staff,
}: {
  orgId: string;
  matchId: string;
  teamId: string;
  ownName: string;
  oppName: string;
  durationMs: number | null;
  onPlay?: (ms: number) => void;
  onPhysical: () => void;
  staff: boolean;
}) {
  const t = useTranslations("videoOverview");
  const q = useQuery({
    queryKey: ["possessions", matchId],
    queryFn: async () =>
      ((await api.GET("/v1/orgs/{org_id}/matches/{match_id}/possessions", { params: { path: { org_id: orgId, match_id: matchId } } })).data ?? null) as Possessions | null,
  });
  const data = q.data;
  const phases = data?.phases ?? [];
  const end = Math.max(durationMs ?? 0, ...phases.map((p) => p.end_ms), 1);
  const own = data?.summary.own;
  const opp = data?.summary.opponent;
  return (
    <div className="space-y-10" data-testid="video-overview">
      <Sheet className="space-y-5">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-xl">{t("title")}</h2>
          <span className="text-xs text-muted">{t("estimated")}</span>
        </div>
        {phases.length === 0 ? (
          <p className="text-sm text-muted">{q.isLoading ? "…" : t("noPossessions")}</p>
        ) : (
          <>
            <div className="grid gap-6 sm:grid-cols-2">
              {([["own", ownName, own], ["opponent", oppName, opp]] as const).map(([side, name, s]) => (
                <div key={side} className="space-y-1">
                  <p className="text-sm font-semibold">{name}</p>
                  <p className="font-score text-[2.5rem] leading-none">{Math.round((s?.share ?? 0) * 100)} %</p>
                  <p className="text-sm text-muted">{t("attacks", { n: s?.count ?? 0, avg: Math.round(s?.avg_s ?? 0) })}</p>
                </div>
              ))}
            </div>
            <div className="space-y-2">
              <p className="text-sm font-semibold">{t("timeline")}</p>
              <div className="relative h-8 overflow-hidden rounded-[3px] bg-foreground/5" role="list" aria-label={t("timeline")}>
                {phases.map((p) => (
                  <button
                    key={p.start_ms}
                    type="button"
                    role="listitem"
                    disabled={!onPlay}
                    onClick={() => onPlay?.(p.start_ms)}
                    title={t("phase", { team: p.side === "own" ? ownName : oppName, from: formatClock(p.start_ms), to: formatClock(p.end_ms) })}
                    aria-label={t("phase", { team: p.side === "own" ? ownName : oppName, from: formatClock(p.start_ms), to: formatClock(p.end_ms) })}
                    className={cn("absolute inset-y-0 border-x border-raised transition-opacity hover:opacity-80", p.side === "own" ? "top-0 bottom-1/2 bg-accent" : "top-1/2 bottom-0 bg-foreground/60")}
                    style={{ left: `${(p.start_ms / end) * 100}%`, width: `${Math.max(0.4, ((p.end_ms - p.start_ms) / end) * 100)}%` }}
                  />
                ))}
              </div>
              <div className="flex justify-between text-xs text-muted tabular-nums">
                <span>0:00</span>
                <span className="flex gap-4">
                  <span className="flex items-center gap-1.5"><span aria-hidden className="size-2.5 rounded-[2px] bg-accent" />{ownName}</span>
                  <span className="flex items-center gap-1.5"><span aria-hidden className="size-2.5 rounded-[2px] bg-foreground/60" />{oppName}</span>
                </span>
                <span>{formatClock(end)}</span>
              </div>
              {onPlay && <p className="text-xs text-muted">{t("timelineHint")}</p>}
            </div>
          </>
        )}
        <button type="button" onClick={onPhysical} className="text-sm font-semibold text-accent hover:underline">
          {t("physical")}
        </button>
      </Sheet>
      {staff && (
        <Sheet className="space-y-3">
          <h2 className="text-xl">{t("moreTitle")}</h2>
          <p className="max-w-2xl text-sm text-muted">{t("moreText")}</p>
          <div className="flex flex-wrap gap-2">
            <Link href={`/app/${orgId}/matches/${matchId}/marks`} className={buttonClass("secondary", "sm")}>
              {t("marks")}
            </Link>
            <Link href={`/app/${orgId}/teams/${teamId}/paper`} className={buttonClass("secondary", "sm")}>
              {t("paper")}
            </Link>
          </div>
        </Sheet>
      )}
    </div>
  );
}
