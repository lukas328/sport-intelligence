"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play, RotateCcw, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, Card, CardTitle } from "@/components/ui/card";
import { Segmented } from "@/components/ui/tabs";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { formatClock } from "@/lib/format";
import {
  focusAfter,
  isOpen,
  keyAction,
  moveFocus,
  visibleRows,
  withReview,
  type Candidate,
  type CandidateFilter,
  type CandidateList,
  type CandidateReview,
  type CandidateSide,
} from "@/lib/goal-candidates";
import { cn } from "@/lib/utils";

export const goalCandidatesKey = (matchId: string) => ["goal-candidates", matchId];

const KNOWN_SOURCE: Record<string, string> = {
  scoreboard_ocr: "knownOverlay",
  official_report: "knownReport",
};

/** Moments the video analysis proposes as goals: the coach confirms each for a team or rejects
 * it, one click (or key) per candidate, so a game's goals are in after a few minutes even
 * without a score overlay or an official report. */
export function GoalCandidatesPanel({
  orgId,
  matchId,
  ownName,
  oppName,
  onClip,
}: {
  orgId: string;
  matchId: string;
  ownName: string;
  oppName: string;
  onClip: (fromMs: number, toMs: number) => void;
}) {
  const t = useTranslations("goalCandidates");
  const tr = useTranslations();
  const qc = useQueryClient();
  const key = goalCandidatesKey(matchId);
  const path = { org_id: orgId, match_id: matchId };
  const [filter, setFilter] = useState<CandidateFilter>("open");
  const [rate, setRate] = useState<number | null>(null);
  const [error, setError] = useState<ErrorKey | null>(null);
  const [focus, setFocus] = useState(0);
  const rowRefs = useRef<(HTMLLIElement | null)[]>([]);
  const refocus = useRef<number | null>(null);
  const q = useQuery({
    queryKey: key,
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/goal-candidates", { params: { path } }))
        .data ?? null,
  });
  const reviewKey = ["review", ...key];
  const review = useMutation({
    // one at a time, in key order: "1" and then "U" must reach the server in that order
    mutationKey: reviewKey,
    scope: { id: reviewKey.join(":") },
    mutationFn: async (v: {
      id: string;
      status: CandidateReview | null;
      side: CandidateSide | null;
    }) => {
      const r = await api.PUT(
        "/v1/orgs/{org_id}/matches/{match_id}/goal-candidates/{candidate_id}/review",
        {
          params: { path: { ...path, candidate_id: v.id } },
          body: { status: v.status, side: v.side },
        },
      );
      if (r.error) throw r.error;
    },
    onMutate: async ({ id, status, side }) => {
      setError(null);
      await qc.cancelQueries({ queryKey: key });
      const before = qc.getQueryData<CandidateList | null>(key);
      if (before) qc.setQueryData(key, withReview(before, id, status, side));
      return { before };
    },
    onError: (err, _v, ctx) => {
      if (ctx?.before) qc.setQueryData(key, ctx.before);
      setError(errorKey(err));
    },
    onSettled: () => {
      // the last queued review refetches; earlier ones would overwrite the optimistic rows
      if (qc.isMutating({ mutationKey: reviewKey }) > 1) return;
      void qc.invalidateQueries({ queryKey: key });
      // a confirmed goal is an event: the score, the statistics and the comparison change
      void qc.invalidateQueries({ queryKey: ["stats", matchId] });
      void qc.invalidateQueries({ queryKey: ["events", matchId] });
      void qc.invalidateQueries({ queryKey: ["official-goals", matchId] });
    },
  });

  const list = q.data;
  const current = rate ?? list?.default_rate ?? 2;
  const rows = list ? visibleRows(list, current, filter) : [];
  useEffect(() => {
    if (refocus.current == null) return;
    const i = refocus.current;
    refocus.current = null;
    if (i >= 0) rowRefs.current[i]?.focus();
  });
  if (!list || list.counts.total === 0) return null;

  const team = (side: string | null | undefined) =>
    side === "own" ? ownName : side === "opponent" ? oppName : null;
  const decide = (
    c: Candidate,
    index: number,
    status: CandidateReview | null,
    side: CandidateSide | null,
  ) => {
    // leaves the open list: the next row takes the focus
    const leaves = filter === "open" && status !== null;
    const next = focusAfter(rows.length, index, leaves);
    setFocus(Math.max(0, next));
    refocus.current = next;
    review.mutate({ id: c.id, status, side });
  };
  const confirmed = (c: Candidate, side: CandidateSide) =>
    c.status === "confirmed" && c.side === side;

  function onRowKey(e: KeyboardEvent<HTMLLIElement>, c: Candidate, index: number) {
    if (e.target !== e.currentTarget || e.metaKey || e.ctrlKey || e.altKey) return;
    const action = keyAction(e.key);
    if (!action) return;
    e.preventDefault();
    e.stopPropagation(); // the tagger's hotkeys listen on the window
    if (action === "play") return onClip(c.start_ms, c.end_ms);
    if (action === "own" || action === "opponent") {
      if (c.known) return;
      return decide(
        c,
        index,
        confirmed(c, action) ? null : "confirmed",
        confirmed(c, action) ? null : action,
      );
    }
    if (action === "reject")
      return decide(c, index, c.status === "rejected" ? null : "rejected", null);
    if (action === "undo") return c.status !== "open" ? decide(c, index, null, null) : undefined;
    const to = moveFocus(action, index, rows.length);
    setFocus(to);
    rowRefs.current[to]?.focus();
  }

  const openAt = (r: number) => list.counts.open_by_rate[String(r)] ?? 0;
  const active = Math.min(focus, rows.length - 1);

  return (
    <Card className="space-y-4" data-testid="goal-candidates">
      <div className="space-y-1">
        <CardTitle>{t("title")}</CardTitle>
        <p className="text-sm text-muted">{t("hint")}</p>
      </div>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4" data-testid="goal-candidates-counts">
        {(
          [
            ["countOpen", openAt(current)],
            ["countConfirmed", list.counts.confirmed],
            ["countRejected", list.counts.rejected],
            ["countKnown", list.counts.known],
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="rounded-md bg-surface px-3 py-2.5">
            <dt className="text-[0.8125rem] text-muted">{t(label)}</dt>
            <dd className="mt-1 font-score text-[1.75rem] leading-none tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Segmented<CandidateFilter>
            label={t("filter")}
            size="sm"
            value={filter}
            onChange={setFilter}
            items={[
              { value: "open", label: t("open", { n: openAt(current) }) },
              { value: "all", label: t("all", { n: visibleRows(list, current, "all").length }) },
            ]}
          />
          <Segmented<string>
            label={t("rate")}
            size="sm"
            value={String(current)}
            onChange={(v) => setRate(Number(v))}
            items={list.rates.map((r) => ({ value: String(r), label: t("perMinute", { n: r }) }))}
          />
        </div>
      </div>
      {/* keys only help with a keyboard; the list still points at the text (aria-describedby) */}
      <p className="text-xs text-muted pointer-coarse:hidden" id={`gc-keys-${matchId}`}>
        {t.rich("keys", {
          own: ownName,
          opp: oppName,
          k: (chunks) => (
            <kbd className="rounded-sm px-1 py-px font-sans text-[0.75rem] text-foreground ring-1 ring-border">
              {chunks}
            </kbd>
          ),
        })}
      </p>
      {rows.length === 0 ? (
        <p className="text-sm text-muted">{filter === "open" ? t("nothingOpen") : t("none")}</p>
      ) : (
        <ul
          // rows reach the scroll box's edges (focus ring drawn inside); the lines between them
          // stay in line with the card's content
          className="-mx-1.5 max-h-[28rem] overflow-auto text-sm"
          aria-label={t("title")}
          aria-describedby={`gc-keys-${matchId}`}
        >
          {rows.map((c, i) => {
            const time = formatClock(c.goal_ms);
            const clock = c.clock_s != null ? formatClock(c.clock_s * 1000) : null;
            const suggested = team(c.suggested_side);
            const label = [
              time,
              clock ? t("clock", { clock }) : null,
              suggested ? t("suggested", { team: suggested }) : null,
            ]
              .filter(Boolean)
              .join(", ");
            const known = c.known
              ? t(KNOWN_SOURCE[c.known.source] ?? "knownTagged", { team: team(c.known.side) ?? "" })
              : null;
            return (
              <li
                key={c.id}
                ref={(el) => {
                  rowRefs.current[i] = el;
                }}
                tabIndex={i === active ? 0 : -1}
                aria-label={t("row", { label })}
                onKeyDown={(e) => onRowKey(e, c, i)}
                onFocus={() => setFocus(i)}
                className="relative flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-sm px-1.5 py-2 outline-none after:absolute after:inset-x-1.5 after:bottom-0 after:h-px after:bg-border/70 last:after:hidden focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-inset"
                data-testid="goal-candidate-row"
              >
                <Button
                  variant="secondary"
                  size="sm"
                  className="w-[5.5rem] tabular-nums"
                  tabIndex={i === active ? undefined : -1}
                  aria-label={t("play", { time })}
                  aria-keyshortcuts="Enter"
                  onClick={() => onClip(c.start_ms, c.end_ms)}
                >
                  <Play aria-hidden className="size-3 fill-current" />
                  {time}
                </Button>
                <span className="w-12 font-mono text-xs tabular-nums">
                  <span className="sr-only">{t("gameTime")} </span>
                  {clock ?? "-"}
                </span>
                <span
                  className={cn(
                    "min-w-0 flex-1",
                    c.status === "rejected" && "line-through decoration-muted",
                  )}
                >
                  {c.status === "confirmed" ? (
                    <span className="font-medium">
                      {t("goalFor", { team: team(c.side) ?? "" })}
                    </span>
                  ) : suggested ? (
                    <span className="text-muted">{t("suggested", { team: suggested })}</span>
                  ) : (
                    <span className="text-muted">{t("noSuggestion")}</span>
                  )}
                </span>
                <span className="flex flex-wrap items-center gap-1.5">
                  {c.rate > 2 && <Badge>{t("extraRate")}</Badge>}
                  {known && <Badge tone="accent">{known}</Badge>}
                  {c.status === "confirmed" && <Badge tone="ok">{t("confirmed")}</Badge>}
                  {c.status === "rejected" && <Badge tone="neutral">{t("rejected")}</Badge>}
                </span>
                <span role="group" aria-label={label} className="flex flex-wrap gap-1">
                  {(["own", "opponent"] as const).map((side, k) => {
                    const on = confirmed(c, side);
                    return (
                      <Button
                        key={side}
                        variant="secondary"
                        size="sm"
                        tabIndex={i === active ? undefined : -1}
                        disabled={c.known != null}
                        aria-pressed={on}
                        aria-keyshortcuts={String(k + 1)}
                        className={cn(on && "bg-ok/12 text-ok ring-ok/50 hover:bg-ok/12")}
                        onClick={() => decide(c, i, on ? null : "confirmed", on ? null : side)}
                      >
                        {t("goalFor", { team: team(side) ?? "" })}
                      </Button>
                    );
                  })}
                  <Button
                    variant={c.status === "rejected" ? "secondary" : "quiet"}
                    size="icon-sm"
                    tabIndex={i === active ? undefined : -1}
                    aria-pressed={c.status === "rejected"}
                    aria-keyshortcuts="X"
                    aria-label={t("reject")}
                    title={t("reject")}
                    className={cn(c.status === "rejected" && "text-error")}
                    onClick={() => decide(c, i, c.status === "rejected" ? null : "rejected", null)}
                  >
                    <X aria-hidden />
                  </Button>
                  {c.status !== "open" && (
                    <Button
                      variant="quiet"
                      size="icon-sm"
                      tabIndex={i === active ? undefined : -1}
                      aria-keyshortcuts="U"
                      aria-label={t("undo")}
                      title={t("undo")}
                      onClick={() => decide(c, i, null, null)}
                    >
                      <RotateCcw aria-hidden />
                    </Button>
                  )}
                </span>
              </li>
            );
          })}
        </ul>
      )}
      {list.candidates.some((c) => !isOpen(c) && c.status === "open") && filter === "open" && (
        <p className="text-xs text-muted">{t("knownHint", { n: list.counts.known })}</p>
      )}
      {error && <Alert>{tr(`errors.${error}`)}</Alert>}
    </Card>
  );
}
