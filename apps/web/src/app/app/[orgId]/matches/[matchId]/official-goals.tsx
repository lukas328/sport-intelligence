"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Play, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Badge, type Tone } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Segmented } from "@/components/ui/tabs";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import {
  gameTime,
  goalRows,
  jumpTarget,
  nextReview,
  withReview,
  type GoalComparison,
  type GoalFilter,
  type GoalRow,
  type Review,
} from "@/lib/official-goals";
import type { Span } from "@/lib/match-workflow";
import { playerLabel, reportName } from "@/lib/player-name";
import { cn } from "@/lib/utils";

const TONE: Record<GoalRow["kind"], Tone> = {
  found: "ok",
  missing: "warn",
  outside: "neutral",
  extra: "accent",
};

export const officialGoalsKey = (matchId: string) => ["official-goals", matchId];

/** The comparison with the official report; the work steps and the timeline share the cache. */
export function useOfficialGoals(orgId: string, matchId: string, enabled = true) {
  return useQuery({
    queryKey: officialGoalsKey(matchId),
    enabled,
    queryFn: async () =>
      (
        await api.GET("/v1/orgs/{org_id}/matches/{match_id}/official-report/comparison", {
          params: { path: { org_id: orgId, match_id: matchId } },
        })
      ).data ?? null,
  });
}

/** The goals of the imported official match report next to the goals the video analysis found:
 * how far the video timeline can be trusted, and a jump to each gap to check it. */
export function OfficialGoalsPanel({
  orgId,
  matchId,
  ownName,
  oppName,
  isHome,
  names,
  covers = null,
  onPlay,
}: {
  orgId: string;
  matchId: string;
  ownName: string;
  oppName: string;
  isHome: boolean;
  names: Record<string, string>;
  /** what the video covers of the match: goals beyond it are not missing */
  covers?: Span[] | null;
  onPlay: (ms: number) => void;
}) {
  const t = useTranslations("officialGoals");
  const tr = useTranslations();
  const qc = useQueryClient();
  const key = officialGoalsKey(matchId);
  const path = { org_id: orgId, match_id: matchId };
  const [filter, setFilter] = useState<GoalFilter>("all");
  const [showOutside, setShowOutside] = useState(false);
  const [error, setError] = useState<ErrorKey | null>(null);
  const q = useOfficialGoals(orgId, matchId);
  const reviewKey = ["review", ...key];
  const review = useMutation({
    // one at a time, in click order: a confirm and its undo must reach the server in that order
    mutationKey: reviewKey,
    scope: { id: reviewKey.join(":") },
    mutationFn: async ({ id, status }: { id: string; status: Review | null }) => {
      const r = await api.PUT("/v1/orgs/{org_id}/matches/{match_id}/official-report/review", {
        params: { path },
        body: { event_id: id, status },
      });
      if (r.error) throw r.error;
    },
    onMutate: async ({ id, status }) => {
      setError(null);
      await qc.cancelQueries({ queryKey: key });
      const before = qc.getQueryData<GoalComparison | null>(key);
      if (before) qc.setQueryData(key, withReview(before, id, status));
      return { before };
    },
    onError: (err, _v, ctx) => {
      if (ctx?.before) qc.setQueryData(key, ctx.before);
      setError(errorKey(err));
    },
    onSettled: () => {
      // the last queued review refetches; earlier ones would overwrite the optimistic rows
      if (qc.isMutating({ mutationKey: reviewKey }) <= 1)
        void qc.invalidateQueries({ queryKey: key });
    },
  });

  const cmp = q.data;
  if (!cmp?.imported) return null;
  const rows = goalRows(cmp, filter, showOutside, covers);
  const every = goalRows(cmp, "all", true, covers);
  const outside = every.filter((r) => r.kind === "outside").length;
  const missing = every.filter((r) => r.kind === "missing").length;
  const openRows = goalRows(cmp, "open", false, covers);
  const open = openRows.length;
  // the one mark of the list: the first goal still to check
  const firstOpen = openRows.find((r) => jumpTarget(r) != null)?.id;
  const inVideo = cmp.counts.official - outside;
  const team = (side: string) => (side === "own" ? ownName : oppName);
  const score = (s: number[] | null) =>
    s && s.length === 2 ? (isHome ? `${s[0]}:${s[1]}` : `${s[1]}:${s[0]}`) : null;
  // the roster name, else the report's name in the same form ("#7 Lisa Zimmerli")
  const who = (r: GoalRow) =>
    (r.playerId && names[r.playerId]) || playerLabel(r.number, reportName(r.name));

  return (
    <section className="flex min-h-0 flex-1 flex-col gap-3" data-testid="official-goals" aria-labelledby={`og-title-${matchId}`}>
      <div className="space-y-1">
        <h2 id={`og-title-${matchId}`} className="sr-only">{t("title")}</h2>
        {/* counts read against what the video covers: goals before or after a clip are no gap */}
        <p className="text-sm" data-testid="official-goals-counts">
          {inVideo > 0
            ? t("summary", { inVideo, found: cmp.counts.found, missing })
            : t("summaryNone", { n: cmp.counts.official })}
          {cmp.counts.extra > 0 && ` ${t("summaryExtra", { n: cmp.counts.extra })}`}
        </p>
        <p className="text-xs text-muted">{t("hint", { window: Math.round(cmp.window_s) })}</p>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Segmented<GoalFilter>
          label={t("filter")}
          size="sm"
          value={filter}
          onChange={setFilter}
          items={[
            {
              value: "all",
              label: t("all", {
                n: cmp.counts.official + cmp.counts.extra - (showOutside ? 0 : outside),
              }),
            },
            { value: "open", label: t("open", { n: open }) },
          ]}
        />
        <p className="text-xs text-muted">{t("reviewHint")}</p>
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-muted">{filter === "open" ? t("nothingOpen") : t("noGoals")}</p>
      ) : (
        <ul
          // the padding keeps the focus outlines of the buttons at the edges inside the scroll box
          className="-mx-1.5 max-h-[28rem] min-h-0 flex-1 divide-y divide-border/70 overflow-auto px-1.5 text-sm lg:max-h-none"
          aria-label={t("title")}
        >
          {rows.map((r) => {
            const target = jumpTarget(r);
            const time = gameTime(r);
            const label = [time, team(r.side), who(r)].filter(Boolean).join(", ");
            const away = r.kind === "outside";
            // the match clock as the coach says it ("1. HZ 13:21")
            const clockLabel = time ? tr("events.at", { period: r.period, clock: time }) : "-";
            return (
              <li
                key={r.id}
                // phone: time and checks on top, the goal below; wider: one line
                className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1.5 py-2 sm:flex sm:flex-wrap"
                data-testid="official-goal-row"
              >
                {target != null ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    className="font-score tabular-nums"
                    aria-label={t("jump", { time: clockLabel, goal: label })}
                    onClick={() => onPlay(target)}
                  >
                    <Play aria-hidden className="size-3 fill-current" />
                    <span className={cn(r.id === firstOpen && "underline decoration-resin decoration-[5px] underline-offset-[5px]")}>{clockLabel}</span>
                  </Button>
                ) : (
                  <span className="inline-flex items-baseline gap-2 text-sm">
                    <span className="font-score tabular-nums">{clockLabel}</span>
                    <span className="text-xs text-muted">{away ? t("outside") : t("noTime")}</span>
                  </span>
                )}
                <span
                  className={cn(
                    "col-span-full row-start-2 min-w-0 sm:min-w-48 sm:flex-1",
                    away && "text-muted",
                    r.review === "dismissed" && "line-through decoration-muted",
                  )}
                >
                  <span className="font-medium">{team(r.side)}</span>
                  {who(r) && <span className="text-muted">{` · ${who(r)}`}</span>}
                  {r.penalty && <span className="text-muted">{` · ${t("penalty")}`}</span>}
                  {score(r.score) && (
                    <span className="ml-1.5 font-score text-xs tabular-nums text-muted">
                      {score(r.score)}
                    </span>
                  )}
                </span>
                {!away && (
                  <span className="col-span-full row-start-3 flex flex-wrap items-center gap-1.5">
                    <Badge tone={TONE[r.kind]}>{t(r.kind)}</Badge>
                    {r.kind === "missing" && r.estimated && target != null && (
                      <Badge>{t("estimated")}</Badge>
                    )}
                    {r.review && <Badge tone="neutral">{t(r.review)}</Badge>}
                  </span>
                )}
                {!away && (
                  <span
                    role="group"
                    aria-label={label}
                    className="col-start-3 row-start-1 flex gap-1 justify-self-end"
                  >
                    {(["confirmed", "dismissed"] as const).map((s) => {
                      const Icon = s === "confirmed" ? Check : X;
                      const active = r.review === s;
                      return (
                        <Button
                          key={s}
                          variant={active ? "secondary" : "quiet"}
                          size="icon-sm"
                          aria-pressed={active}
                          aria-label={t(s === "confirmed" ? "confirm" : "dismiss")}
                          title={t(s === "confirmed" ? "confirm" : "dismiss")}
                          className={cn(active && (s === "confirmed" ? "text-ok" : "text-error"))}
                          onClick={() =>
                            review.mutate({ id: r.id, status: nextReview(r.review, s) })
                          }
                        >
                          <Icon aria-hidden />
                        </Button>
                      );
                    })}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {outside > 0 && filter === "all" && (
        <p className="flex flex-wrap items-center gap-x-2 text-xs text-muted">
          {t("outsideHint", { n: outside })}
          <Button
            variant="ghost"
            size="sm"
            className="-my-1"
            aria-expanded={showOutside}
            onClick={() => setShowOutside((v) => !v)}
          >
            {showOutside ? t("hideOutside") : t("showOutside")}
          </Button>
        </p>
      )}
      {error && <Alert>{tr(`errors.${error}`)}</Alert>}
    </section>
  );
}
