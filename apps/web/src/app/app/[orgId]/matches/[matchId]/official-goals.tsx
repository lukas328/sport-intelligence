"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Play, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Badge, type Tone } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, Card, CardTitle } from "@/components/ui/card";
import { Segmented } from "@/components/ui/tabs";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { formatClock } from "@/lib/format";
import {
  goalRows,
  jumpTarget,
  nextReview,
  withReview,
  type GoalComparison,
  type GoalFilter,
  type GoalRow,
  type Review,
} from "@/lib/official-goals";
import { cn } from "@/lib/utils";

const TONE: Record<GoalRow["kind"], Tone> = {
  found: "ok",
  missing: "warn",
  outside: "neutral",
  extra: "accent",
};

export const officialGoalsKey = (matchId: string) => ["official-goals", matchId];

/** The goals of the imported official match report next to the goals the video analysis found:
 * how far the video timeline can be trusted, and a jump to each gap to check it. */
export function OfficialGoalsPanel({
  orgId,
  matchId,
  ownName,
  oppName,
  isHome,
  names,
  onPlay,
}: {
  orgId: string;
  matchId: string;
  ownName: string;
  oppName: string;
  isHome: boolean;
  names: Record<string, string>;
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
  const q = useQuery({
    queryKey: key,
    queryFn: async () =>
      (
        await api.GET("/v1/orgs/{org_id}/matches/{match_id}/official-report/comparison", {
          params: { path },
        })
      ).data ?? null,
  });
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
  const rows = goalRows(cmp, filter, showOutside);
  const outside = cmp.counts.outside;
  const team = (side: string) => (side === "own" ? ownName : oppName);
  const score = (s: number[] | null) =>
    s && s.length === 2 ? (isHome ? `${s[0]}:${s[1]}` : `${s[1]}:${s[0]}`) : null;
  const who = (r: GoalRow) =>
    (r.playerId && names[r.playerId]) ||
    [r.number != null ? `#${r.number}` : null, r.name].filter(Boolean).join(" ");

  return (
    <Card className="space-y-4" data-testid="official-goals">
      <div className="space-y-1">
        <CardTitle>{t("title")}</CardTitle>
        <p className="text-sm text-muted">{t("hint", { window: Math.round(cmp.window_s) })}</p>
      </div>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4" data-testid="official-goals-counts">
        {(
          [
            ["countOfficial", cmp.counts.official],
            ["countFound", cmp.counts.found],
            ["countMissing", cmp.counts.missing],
            ["countExtra", cmp.counts.extra],
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="rounded-md bg-surface px-3 py-2.5">
            <dt className="text-[0.8125rem] text-muted">{t(label)}</dt>
            <dd className="mt-1 font-score text-[1.75rem] leading-none tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
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
            { value: "open", label: t("open", { n: cmp.counts.open }) },
          ]}
        />
        <p className="text-xs text-muted">{t("reviewHint")}</p>
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-muted">{filter === "open" ? t("nothingOpen") : t("noGoals")}</p>
      ) : (
        <ul
          // the padding keeps the focus outlines of the buttons at the edges inside the scroll box
          className="-mx-1.5 max-h-[28rem] divide-y divide-border/70 overflow-auto px-1.5 text-sm"
          aria-label={t("title")}
        >
          {rows.map((r) => {
            const target = jumpTarget(r);
            const label = [r.time, team(r.side), who(r)].filter(Boolean).join(", ");
            const away = r.kind === "outside";
            return (
              <li
                key={r.id}
                // phone: time and checks on top, the goal below; wider: one line
                className="grid grid-cols-[auto_auto_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1.5 py-2 sm:flex sm:flex-wrap"
                data-testid="official-goal-row"
              >
                {target != null ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    className="w-[5.5rem] tabular-nums"
                    aria-label={t("jump", { time: formatClock(r.tMs!), goal: label })}
                    onClick={() => onPlay(target)}
                  >
                    <Play aria-hidden className="size-3 fill-current" />
                    {formatClock(r.tMs!)}
                  </Button>
                ) : (
                  <span className="inline-flex w-[5.5rem] text-xs text-muted">
                    {away ? t("outside") : t("noTime")}
                  </span>
                )}
                <span className="w-12 font-mono text-xs tabular-nums">
                  <span className="sr-only">{t("gameTime")} </span>
                  {r.time ?? "-"}
                </span>
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
                    <span className="ml-1.5 font-mono text-xs tabular-nums text-muted">
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
                    className="col-start-4 row-start-1 flex gap-1 justify-self-end"
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
    </Card>
  );
}
