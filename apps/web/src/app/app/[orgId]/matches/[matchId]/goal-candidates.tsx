"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play, RotateCcw } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Segmented } from "@/components/ui/tabs";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { formatClock } from "@/lib/format";
import {
  focusAfter,
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

/** The candidate list; the work steps read the open count from the same cache. */
export function useGoalCandidates(orgId: string, matchId: string, enabled = true) {
  return useQuery({
    queryKey: goalCandidatesKey(matchId),
    enabled,
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/goal-candidates", { params: { path: { org_id: orgId, match_id: matchId } } }))
        .data ?? null,
  });
}

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
  onActive,
  focusMode = false,
}: {
  orgId: string;
  matchId: string;
  ownName: string;
  oppName: string;
  onClip: (fromMs: number, toMs: number) => void;
  /** the candidate that is up, for the timeline's signal ring */
  onActive?: (id: string | null) => void;
  /** review mode: the active candidate large, its clip plays as soon as it is active */
  focusMode?: boolean;
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
  // the row to focus next, by id: the list changes only once the optimistic update is in
  const refocus = useRef<string | null>(null);
  const lastDecided = useRef<string | null>(null);
  const [said, setSaid] = useState<string | null>(null);
  const q = useGoalCandidates(orgId, matchId);
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
    const i = rows.findIndex((r) => r.id === refocus.current);
    if (i < 0) return; // not in the list yet: try again after the next render
    refocus.current = null;
    rowRefs.current[i]?.focus(); // the row's onFocus moves the active index
  });
  const activeRow = rows[Math.min(focus, rows.length - 1)];
  useEffect(() => {
    onActive?.(activeRow?.status === "open" ? activeRow.id : null);
  }, [activeRow?.id, activeRow?.status]); // eslint-disable-line react-hooks/exhaustive-deps
  // review mode: each candidate's clip plays when it becomes the active one
  useEffect(() => {
    if (focusMode && activeRow) onClip(activeRow.start_ms, activeRow.end_ms);
  }, [focusMode, activeRow?.id]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (focusMode) rowRefs.current[Math.min(focus, rows.length - 1)]?.focus();
  }, [focusMode]); // eslint-disable-line react-hooks/exhaustive-deps
  const undoRef = useRef<() => void>(() => {});
  useEffect(() => {
    if (!focusMode) return;
    // the last row decided leaves nothing focused: U still takes it back
    const onKey = (e: globalThis.KeyboardEvent) => {
      if ((e.key === "u" || e.key === "U") && (document.activeElement === document.body || document.activeElement == null)) undoRef.current();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [focusMode]);
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
    refocus.current = next < 0 ? null : (leaves ? rows.filter((r) => r.id !== c.id)[next]?.id : rows[next]?.id) ?? null;
    if (status !== null) lastDecided.current = c.id;
    setSaid(
      status === null
        ? t("saidUndo", { time: game(c) })
        : t("said", { time: game(c), what: status === "confirmed" ? t("goalFor", { team: team(side) ?? "" }) : t("rejected") }),
    );
    review.mutate({ id: c.id, status, side });
  };
  // the decided row has left the open list: U takes back the last decision and goes there
  function undoLast() {
    const id = lastDecided.current;
    if (!id) return;
    lastDecided.current = null;
    refocus.current = id;
    setSaid(null);
    review.mutate({ id, status: null, side: null });
  }
  undoRef.current = undoLast;
  // the match clock, as the coach says it ("1. HZ 12:55"); video time only without a throw-off
  const game = (c: Candidate) =>
    c.clock_s != null ? tr("events.at", { period: c.period ?? 1, clock: formatClock(c.clock_s * 1000) }) : formatClock(c.goal_ms);
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
    if (action === "undo") {
      if (c.status !== "open") return decide(c, index, null, null);
      return undoLast();
    }
    const to = moveFocus(action, index, rows.length);
    setFocus(to);
    rowRefs.current[to]?.focus();
  }

  const openAt = (r: number) => list.counts.open_by_rate[String(r)] ?? 0;
  const active = Math.min(focus, rows.length - 1);

  const openRows = visibleRows(list, current, "open");
  const pos = activeRow ? openRows.findIndex((r) => r.id === activeRow.id) + 1 : 0;
  const deciding = activeRow && activeRow.status === "open" && activeRow.known == null ? activeRow : null;
  const big = focusMode ? "lg" : "md";

  return (
    <section className="flex min-h-0 flex-1 flex-col gap-3" data-testid="goal-candidates" aria-labelledby={`gc-title-${matchId}`}>
      <h2 id={`gc-title-${matchId}`} className="sr-only">{t("title")}</h2>
      {/* keys only help with a keyboard; the list points at the text (aria-describedby) */}
      <p className="sr-only" id={`gc-keys-${matchId}`}>
        {t.rich("keys", { own: ownName, opp: oppName, k: (chunks) => <kbd>{chunks}</kbd> })}
      </p>

      {/* the one question first: the current candidate and its three answers */}
      {deciding && (
        <div className="space-y-3 border-y border-foreground/15 py-3" data-testid="goal-candidate-focus">
          <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className={cn("font-display leading-none", focusMode ? "text-4xl" : "text-3xl")}>{t("question")}</span>
            {/* phones: the timeline's signal ring is out of view, so the moment carries the mark */}
            <span className="font-score text-lg tabular-nums max-lg:underline max-lg:decoration-resin max-lg:decoration-[5px] max-lg:underline-offset-[5px]">
              {game(deciding)}
            </span>
            <span className="text-sm text-muted">
              {deciding.suggested_side ? t("suggested", { team: team(deciding.suggested_side) ?? "" }) : t("noSuggestion")}
            </span>
            {pos > 0 && <span className="ml-auto font-score text-sm text-muted tabular-nums">{t("position", { pos, n: openRows.length })}</span>}
          </p>
          <div className="grid grid-cols-2 gap-2">
            {(["own", "opponent"] as const).map((side, k) => (
              <Button
                key={side}
                size={big}
                variant={deciding.suggested_side === side || (!deciding.suggested_side && k === 0) ? "primary" : "secondary"}
                className="h-auto min-w-0 justify-start px-3 py-2 text-left whitespace-normal"
                aria-keyshortcuts={String(k + 1)}
                onClick={() => decide(deciding, active, "confirmed", side)}
              >
                <kbd aria-hidden className="font-score opacity-70">{k + 1}</kbd>
                {t("goalFor", { team: team(side) ?? "" })}
              </Button>
            ))}
            <Button size={big} variant="secondary" className="justify-start px-3" aria-keyshortcuts="X" onClick={() => decide(deciding, active, "rejected", null)}>
              <kbd aria-hidden className="font-score opacity-70">X</kbd>
              {t("noGoal")}
            </Button>
            <Button size={big} variant="quiet" className="justify-start px-3" aria-keyshortcuts="R" onClick={() => onClip(deciding.start_ms, deciding.end_ms)}>
              <kbd aria-hidden className="font-score opacity-70">R</kbd>
              {t("replay")}
            </Button>
          </div>
        </div>
      )}

      {/* what the last key did, and how to take it back */}
      <p className="flex min-h-8 flex-wrap items-center gap-x-3 text-sm" aria-live="polite" data-testid="goal-candidates-said">
        {said ?? <span className="text-muted">{t("undoIdle")}</span>}
        {said && lastDecided.current && (
          <Button variant="ghost" size="sm" className="-my-1" aria-keyshortcuts="U" onClick={undoLast}>
            <RotateCcw aria-hidden />
            {t("undo")}
            <kbd aria-hidden className="font-score text-muted">U</kbd>
          </Button>
        )}
      </p>

      <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm" data-testid="goal-candidates-counts">
        <span>{t("summary", { open: openAt(current), confirmed: list.counts.confirmed, rejected: list.counts.rejected, known: list.counts.known })}</span>
        <button
          type="button"
          className="font-medium text-accent underline-offset-2 hover:underline"
          aria-pressed={filter === "all"}
          onClick={() => setFilter(filter === "all" ? "open" : "all")}
        >
          {filter === "all" ? t("showOpen") : t("showAll", { n: visibleRows(list, current, "all").length })}
        </button>
      </p>
      {rows.length === 0 ? (
        <p className="text-sm text-muted">{filter === "open" ? t("nothingOpen") : t("none")}</p>
      ) : (
        <ul
          className="-mx-1.5 max-h-[28rem] min-h-0 flex-1 overflow-auto text-sm lg:max-h-none"
          aria-label={t("title")}
          aria-describedby={`gc-keys-${matchId}`}
        >
          {rows.map((c, i) => {
            const time = game(c);
            const suggested = team(c.suggested_side);
            const label = [time, suggested ? t("suggested", { team: suggested }) : null].filter(Boolean).join(", ");
            const known = c.known ? t(KNOWN_SOURCE[c.known.source] ?? "knownTagged", { team: team(c.known.side) ?? "" }) : null;
            return (
              <li
                key={c.id}
                ref={(el) => {
                  rowRefs.current[i] = el;
                }}
                tabIndex={i === active ? 0 : -1}
                aria-label={t("row", { label })}
                aria-current={i === active || undefined}
                onKeyDown={(e) => onRowKey(e, c, i)}
                onFocus={() => setFocus(i)}
                className={cn(
                  "relative flex flex-wrap items-center gap-x-3 gap-y-1 rounded-sm px-1.5 py-1.5 outline-none after:absolute after:inset-x-1.5 after:bottom-0 after:h-px after:bg-border/70 last:after:hidden focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-inset",
                  i === active && "bg-surface",
                )}
                data-testid="goal-candidate-row"
              >
                <Button
                  variant="quiet"
                  size="sm"
                  className="font-score tabular-nums"
                  tabIndex={i === active ? undefined : -1}
                  aria-label={t("play", { time })}
                  onClick={() => (setFocus(i), onClip(c.start_ms, c.end_ms))}
                >
                  <Play aria-hidden className="size-3 fill-current" />
                  {time}
                </Button>
                <span className={cn("min-w-0 flex-1", c.status === "rejected" && "text-muted line-through")}>
                  {c.status === "confirmed" ? (
                    <span className="font-medium">{t("goalFor", { team: team(c.side) ?? "" })}</span>
                  ) : c.status === "rejected" ? (
                    t("rejected")
                  ) : known ? (
                    <span className="text-muted">{known}</span>
                  ) : (
                    <span className="text-muted">{suggested ? t("suggested", { team: suggested }) : t("noSuggestion")}</span>
                  )}
                </span>
                {c.rate > 2 && <Badge>{t("extraRate")}</Badge>}
                {c.status !== "open" && (
                  <Button
                    variant="quiet"
                    size="icon-sm"
                    tabIndex={i === active ? undefined : -1}
                    aria-label={`${t("undo")}: ${label}`}
                    title={t("undo")}
                    onClick={() => decide(c, i, null, null)}
                  >
                    <RotateCcw aria-hidden />
                  </Button>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {focusMode && <p className="text-xs text-muted">{t("focusHint")}</p>}
      <details className="text-sm">
        <summary className="cursor-pointer text-muted hover:text-foreground">{t("rateMore")}</summary>
        <div className="pt-2">
          <Segmented<string>
            label={t("rate")}
            size="sm"
            value={String(current)}
            onChange={(v) => setRate(Number(v))}
            items={list.rates.map((r) => ({ value: String(r), label: t("perMinute", { n: r }) }))}
          />
          <p className="mt-1 text-xs text-muted">{t("rateHint")}</p>
        </div>
      </details>
      {error && <Alert>{tr(`errors.${error}`)}</Alert>}
    </section>
  );
}
