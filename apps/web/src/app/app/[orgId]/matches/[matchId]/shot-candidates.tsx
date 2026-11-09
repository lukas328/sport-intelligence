"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play, RotateCcw } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Segmented } from "@/components/ui/tabs";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { formatClock } from "@/lib/format";
import { focusAfter, moveFocus, type CandidateList, type CandidateSide } from "@/lib/goal-candidates";
import { playerLabel, reportName } from "@/lib/player-name";
import {
  defaultSide,
  OUTCOME_KEY,
  OUTCOMES,
  shotAnswer,
  shotKeyAction,
  visibleShots,
  withShotReview,
  type ShotCandidate,
  type ShotFilter,
  type ShotOutcome,
  type ShotReviewBody,
} from "@/lib/shot-candidates";
import { cn } from "@/lib/utils";

export const shotCandidatesKey = (matchId: string) => ["shot-candidates", matchId];

/** The shot candidate list; the tool's tab reads its count from the same cache. */
export function useShotCandidates(orgId: string, matchId: string, enabled = true) {
  return useQuery({
    queryKey: shotCandidatesKey(matchId),
    enabled,
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/shot-candidates", { params: { path: { org_id: orgId, match_id: matchId } } }))
        .data ?? null,
  });
}

/** Moments the video analysis proposes as shots. With an official report most of them come with
 * the report's entry for that moment: Enter takes it (player, outcome and all). Otherwise the
 * coach says the team (1, 2) and the outcome with the tagger's letters (G, S, M, P, B). */
export function ShotCandidatesPanel({
  orgId,
  matchId,
  ownName,
  oppName,
  names,
  onClip,
  onActive,
  onSeek,
  onSetKickoff,
  focusMode = false,
}: {
  orgId: string;
  matchId: string;
  ownName: string;
  oppName: string;
  names: Record<string, string>;
  onClip: (fromMs: number, toMs: number) => void;
  /** the moment that is up, for the timeline's signal ring */
  onActive?: (id: string | null) => void;
  /** the video goes to the moment that is up (paused, with its lead-in) */
  onSeek?: (ms: number) => void;
  /** set when the throw-off is missing: the game times come from the report alone */
  onSetKickoff?: () => void;
  /** full-screen review: each moment's clip plays when it comes up, the keys work right away */
  focusMode?: boolean;
}) {
  const t = useTranslations("shotCandidates");
  const te = useTranslations("events");
  const tr = useTranslations();
  const qc = useQueryClient();
  const key = shotCandidatesKey(matchId);
  const path = { org_id: orgId, match_id: matchId };
  const q = useShotCandidates(orgId, matchId);
  const list = q.data;
  const [filter, setFilter] = useState<ShotFilter | null>(null);
  const [rate, setRate] = useState<number | null>(null);
  const [focus, setFocus] = useState(0);
  // the team picked for the moment that is up (1 / 2), before its outcome
  const [side, setSide] = useState<{ id: string; side: CandidateSide } | null>(null);
  const [said, setSaid] = useState<string | null>(null);
  const [error, setError] = useState<ErrorKey | "needSide" | null>(null);
  const rowRefs = useRef<(HTMLLIElement | null)[]>([]);
  const refocus = useRef<string | null>(null);
  const lastDecided = useRef<string | null>(null);
  const reviewKey = ["review", ...key];
  const review = useMutation({
    // one at a time, in key order: an answer and its undo reach the server in that order
    mutationKey: reviewKey,
    scope: { id: reviewKey.join(":") },
    mutationFn: async (v: { id: string; body: ShotReviewBody }) => {
      const r = await api.PUT("/v1/orgs/{org_id}/matches/{match_id}/goal-candidates/{candidate_id}/review", {
        params: { path: { ...path, candidate_id: v.id } },
        body: v.body,
      });
      if (r.error) throw r.error;
    },
    onMutate: async ({ id, body }) => {
      setError(null);
      await qc.cancelQueries({ queryKey: key });
      const before = qc.getQueryData<CandidateList | null>(key);
      if (before) qc.setQueryData(key, withShotReview(before, id, body));
      return { before };
    },
    onError: (err, _v, ctx) => {
      if (ctx?.before) qc.setQueryData(key, ctx.before);
      setError(errorKey(err));
    },
    onSettled: () => {
      if (qc.isMutating({ mutationKey: reviewKey }) > 1) return;
      // a confirmed shot is an event (or pins a report entry): everything counted from shots moves
      for (const k of ["shot-candidates", "goal-candidates", "stats", "events", "official-goals"]) void qc.invalidateQueries({ queryKey: [k, matchId] });
    },
  });

  // with a report, the moments it explains come first: roughly one per logged shot
  const shown: ShotFilter = filter ?? ((list?.counts.suggested ?? 0) > 0 ? "report" : "open");
  const current = rate ?? list?.default_rate ?? 4;
  const rows = list ? visibleShots(list, current, shown) : [];
  useEffect(() => {
    if (refocus.current == null) return;
    const i = rows.findIndex((r) => r.id === refocus.current);
    if (i < 0) return;
    refocus.current = null;
    rowRefs.current[i]?.focus();
  });
  const up = rows[Math.min(focus, rows.length - 1)];
  useEffect(() => {
    onActive?.(up?.status === "open" ? up.id : null);
  }, [up?.id, up?.status]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => onActive?.(null), []); // eslint-disable-line react-hooks/exhaustive-deps
  // each moment that comes up is shown in the video, so the coach looks before deciding; in the
  // full-screen review its clip plays by itself
  useEffect(() => {
    if (!up || up.status !== "open") return;
    if (focusMode) onClip(up.start_ms, up.end_ms);
    else onSeek?.(up.start_ms);
  }, [up?.id, focusMode]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (focusMode) rowRefs.current[Math.min(focus, rows.length - 1)]?.focus();
  }, [focusMode]); // eslint-disable-line react-hooks/exhaustive-deps
  const undoRef = useRef<() => void>(() => {});
  useEffect(() => {
    if (!focusMode) return;
    // the last moment decided leaves nothing focused: U still takes it back
    const onKey = (e: globalThis.KeyboardEvent) => {
      if ((e.key === "u" || e.key === "U") && (document.activeElement === document.body || document.activeElement == null)) undoRef.current();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [focusMode]);
  if (!list || list.counts.total === 0) return null;

  const active = Math.min(focus, rows.length - 1);
  const activeRow = rows[active];
  const deciding = activeRow && activeRow.status === "open" && activeRow.known == null ? activeRow : null;
  const team = (s: string | null | undefined) => (s === "own" ? ownName : s === "opponent" ? oppName : null);
  const game = (c: ShotCandidate) =>
    c.clock_s != null ? tr("events.at", { period: c.period ?? 1, clock: formatClock(c.clock_s * 1000) }) : formatClock(c.goal_ms);
  const pickedSide = (c: ShotCandidate) => (side?.id === c.id ? side.side : defaultSide(c));
  const outcomeLabel = (o: string | null | undefined) => (o ? te(o as ShotOutcome) : "");
  // the report's entry as a sentence: "Parade, Wurf von #7 Muster (HC Demo-Meilen)"
  const reportLine = (c: ShotCandidate) => {
    const s = c.suggestion;
    if (!s) return null;
    const who = (s.player_id && names[s.player_id]) || playerLabel(s.number, reportName(s.name));
    // the report's own time only where it differs from the moment's clock (the clock map is an estimate)
    const off = s.clock_s != null && c.clock_s != null && Math.abs(s.clock_s - c.clock_s) >= 3 && s.official_time ? t("reportTime", { time: s.official_time }) : null;
    return [s.penalty ? t("penalty", { what: outcomeLabel(s.outcome) }) : outcomeLabel(s.outcome), who && t("shotBy", { who: `${who} (${team(s.side) ?? ""})` }), off]
      .filter(Boolean)
      .join(", ");
  };

  function decide(c: ShotCandidate, index: number, body: ShotReviewBody) {
    const leaves = shown !== "all" && body.status !== null;
    const next = focusAfter(rows.length, index, leaves);
    setFocus(Math.max(0, next));
    refocus.current = next < 0 ? null : ((leaves ? rows.filter((r) => r.id !== c.id)[next]?.id : rows[next]?.id) ?? null);
    if (body.status !== null) lastDecided.current = c.id;
    setSide(null);
    const what =
      body.status === "rejected"
        ? t("noShot")
        : body.status === "confirmed"
          ? "side" in body
            ? t("shotOf", { what: outcomeLabel(body.outcome), team: team(body.side) ?? "" })
            : t("fromReport", { what: reportLine(c) ?? "" })
          : null;
    setSaid(what ? t("said", { time: game(c), what }) : t("saidUndo", { time: game(c) }));
    review.mutate({ id: c.id, body });
  }
  function answer(c: ShotCandidate, index: number, outcome: ShotOutcome | "accept") {
    const body = shotAnswer(c, side?.id === c.id ? side.side : null, outcome);
    if (!body) return setError(outcome === "accept" ? null : "needSide");
    decide(c, index, body);
  }
  undoRef.current = () => undoLast();
  function undoLast() {
    const id = lastDecided.current;
    if (!id) return;
    lastDecided.current = null;
    refocus.current = id;
    setSaid(null);
    review.mutate({ id, body: { status: null } });
  }
  function onRowKey(e: KeyboardEvent<HTMLLIElement>, c: ShotCandidate, index: number) {
    if (e.target !== e.currentTarget || e.metaKey || e.ctrlKey || e.altKey) return;
    const action = shotKeyAction(e.key);
    if (!action) return;
    e.preventDefault();
    e.stopPropagation(); // the tagger's and the player's keys listen on the window
    const open = c.status === "open" && c.known == null;
    switch (action.kind) {
      case "play":
        return onClip(c.start_ms, c.end_ms);
      case "side":
        if (open) {
          setSide({ id: c.id, side: action.side });
          setError(null);
        }
        return;
      case "outcome":
        if (open) answer(c, index, action.outcome);
        return;
      case "accept":
        return open && c.suggestion ? answer(c, index, "accept") : onClip(c.start_ms, c.end_ms);
      case "reject":
        return open ? decide(c, index, { status: "rejected" }) : undefined;
      case "undo":
        return c.status !== "open" ? decide(c, index, { status: null }) : undoLast();
      default: {
        const to = moveFocus(action.kind, index, rows.length);
        setFocus(to);
        rowRefs.current[to]?.focus();
      }
    }
  }

  const official = list.official;
  const openAt = (r: number) => list.counts.open_by_rate[String(r)] ?? 0;
  const suggested = list.counts.suggested ?? 0;

  return (
    <section className="flex min-h-0 flex-1 flex-col gap-3" data-testid="shot-candidates" aria-labelledby={`sc-title-${matchId}`}>
      <h2 id={`sc-title-${matchId}`} className="sr-only">
        {t("title")}
      </h2>
      <p className="sr-only" id={`sc-keys-${matchId}`}>
        {t.rich("keys", { own: ownName, opp: oppName, k: (chunks) => <kbd>{chunks}</kbd> })}
      </p>

      {/* the report against the video: what is placed, what waits for a click, what is missing */}
      {official && (
        <p className="text-sm" data-testid="shot-candidates-report">
          {t("report", {
            total: official.counts.total,
            confirmed: official.counts.confirmed,
            suggested: official.counts.suggested,
            missing: official.counts.missing,
          })}
          {official.counts.outside > 0 && <span className="text-muted">{` ${t("reportOutside", { n: official.counts.outside })}`}</span>}
        </p>
      )}
      {onSetKickoff && (
        <p className="text-sm text-muted" data-testid="shot-candidates-kickoff">
          {t("noKickoff")}{" "}
          <button type="button" className="font-medium text-foreground underline underline-offset-4" onClick={onSetKickoff}>
            {t("setKickoff")}
          </button>
        </p>
      )}

      {/* the one question first: the moment that is up and its answers */}
      {deciding && (
        <div className="space-y-3 border-y border-foreground/15 py-3" data-testid="shot-candidate-focus">
          <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="font-display text-3xl leading-none">{t("question")}</span>
            <span className="font-score text-lg tabular-nums max-lg:underline max-lg:decoration-resin max-lg:decoration-[5px] max-lg:underline-offset-[5px]">
              {game(deciding)}
            </span>
            {rows.length > 0 && (
              <span className="ml-auto font-score text-sm text-muted tabular-nums">{t("position", { pos: active + 1, n: rows.length })}</span>
            )}
          </p>
          {deciding.suggestion && (
            <Button
              variant="primary"
              className="h-auto w-full justify-start px-3 py-2 text-left whitespace-normal"
              aria-keyshortcuts="Enter"
              onClick={() => answer(deciding, active, "accept")}
              data-testid="shot-accept"
            >
              <kbd aria-hidden className="font-score opacity-70 pointer-coarse:hidden">
                ↵
              </kbd>
              <span>
                <span className="block text-xs font-normal">{t("fromReportLabel")}</span>
                {reportLine(deciding)}
              </span>
            </Button>
          )}
          {/* the coach's own answer: team, then the outcome, which saves */}
          <div className="space-y-2">
            <div role="group" aria-label={t("team")} className="grid grid-cols-2 gap-2">
              {(["own", "opponent"] as const).map((s, k) => (
                <Button
                  key={s}
                  size="sm"
                  variant="secondary"
                  className={cn("min-w-0 justify-start max-sm:min-h-11", pickedSide(deciding) === s && "ring-2 ring-foreground ring-inset")}
                  aria-pressed={pickedSide(deciding) === s}
                  aria-keyshortcuts={String(k + 1)}
                  onClick={() => (setSide({ id: deciding.id, side: s }), setError(null))}
                >
                  <kbd aria-hidden className="font-score opacity-70 pointer-coarse:hidden">
                    {k + 1}
                  </kbd>
                  <span className="truncate">{team(s)}</span>
                </Button>
              ))}
            </div>
            <div role="group" aria-label={t("outcome")} className="flex flex-wrap gap-2">
              {OUTCOMES.map((o) => (
                <Button
                  key={o}
                  size="sm"
                  variant="secondary"
                  className="max-sm:min-h-11"
                  aria-keyshortcuts={OUTCOME_KEY[o]}
                  onClick={() => answer(deciding, active, o)}
                  data-testid={`shot-outcome-${o}`}
                >
                  <kbd aria-hidden className="font-score opacity-70 pointer-coarse:hidden">
                    {OUTCOME_KEY[o]}
                  </kbd>
                  {te(o)}
                </Button>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="quiet" className="max-sm:min-h-11" aria-keyshortcuts="X" onClick={() => decide(deciding, active, { status: "rejected" })}>
                <kbd aria-hidden className="font-score opacity-70 pointer-coarse:hidden">
                  X
                </kbd>
                {t("noShot")}
              </Button>
              <Button size="sm" variant="quiet" className="max-sm:min-h-11" aria-keyshortcuts="R" onClick={() => onClip(deciding.start_ms, deciding.end_ms)}>
                <kbd aria-hidden className="font-score opacity-70 pointer-coarse:hidden">
                  R
                </kbd>
                {t("replay")}
              </Button>
            </div>
          </div>
        </div>
      )}

      <div aria-live="polite" className="space-y-2">
        <p className="flex min-h-8 flex-wrap items-center gap-x-3 text-sm" data-testid="shot-candidates-said">
          {said ?? <span className="text-muted pointer-coarse:hidden">{t("undoIdle")}</span>}
          {said && lastDecided.current && (
            <Button variant="ghost" size="sm" className="-my-1" aria-keyshortcuts="U" onClick={undoLast}>
              <RotateCcw aria-hidden />
              {t("undo")}
              <kbd aria-hidden className="font-score text-muted">
                U
              </kbd>
            </Button>
          )}
        </p>
        {error && <Alert>{error === "needSide" ? t("needSide") : tr(`errors.${error}`)}</Alert>}
      </div>

      <Segmented<ShotFilter>
        label={t("filter")}
        variant="underline"
        size="sm"
        value={shown}
        onChange={(v) => (setFilter(v), setFocus(0))}
        items={[
          ...(suggested > 0 || shown === "report" ? [{ value: "report" as const, label: t("withReport", { n: suggested }) }] : []),
          { value: "open", label: t("open", { n: openAt(current) }) },
          { value: "all", label: t("all") },
        ]}
      />
      {rows.length === 0 ? (
        <p className="text-sm text-muted">{shown === "all" ? t("none") : t("nothingOpen")}</p>
      ) : (
        <ul className="-mx-1.5 max-h-[28rem] min-h-0 flex-1 overflow-auto text-sm lg:max-h-none" aria-label={t("title")} aria-describedby={`sc-keys-${matchId}`}>
          {rows.map((c, i) => {
            const time = game(c);
            const line =
              c.status === "confirmed"
                ? t("shotOf", { what: outcomeLabel(c.outcome), team: team(c.side) ?? "" })
                : c.status === "rejected"
                  ? t("noShot")
                  : c.known
                    ? t("known", { what: outcomeLabel(c.known.outcome) || t("aShot"), team: team(c.known.side) ?? "" })
                    : c.suggestion
                      ? t("reportSays", { what: reportLine(c) ?? "" })
                      : (team(c.suggested_side) ?? t("teamOpen"));
            return (
              <li
                key={c.id}
                ref={(el) => {
                  rowRefs.current[i] = el;
                }}
                tabIndex={i === active ? 0 : -1}
                aria-label={t("row", { label: `${time}, ${line}` })}
                aria-current={i === active || undefined}
                onKeyDown={(e) => onRowKey(e, c, i)}
                onFocus={() => setFocus(i)}
                className={cn(
                  "relative flex flex-wrap items-center gap-x-3 gap-y-1 rounded-sm px-1.5 py-1.5 outline-none after:absolute after:inset-x-1.5 after:bottom-0 after:h-px after:bg-border/70 last:after:hidden focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-inset",
                  i === active && "bg-surface",
                )}
                data-testid="shot-candidate-row"
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
                <span className={cn("min-w-0 flex-1", c.status === "confirmed" ? "font-medium" : "text-muted", c.status === "rejected" && "line-through")}>{line}</span>
                {c.status !== "open" && (
                  <Button
                    variant="quiet"
                    size="icon-sm"
                    tabIndex={i === active ? undefined : -1}
                    aria-label={`${t("undo")}: ${time}`}
                    title={t("undo")}
                    onClick={() => decide(c, i, { status: null })}
                  >
                    <RotateCcw aria-hidden />
                  </Button>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {shown !== "report" && (
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
          </div>
        </details>
      )}
    </section>
  );
}
