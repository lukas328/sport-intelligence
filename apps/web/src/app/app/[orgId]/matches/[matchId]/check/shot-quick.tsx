"use client";

import type { Schemas } from "@handball/api-client";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { type CSSProperties, useCallback, useEffect, useRef, useState } from "react";
import { useShell } from "@/components/shell/context";
import { VideoPlayer, type PlayerHandle } from "@/components/video/player";
import { matchStyle } from "@/lib/color";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { formatClock } from "@/lib/format";
import type { CandidateSide } from "@/lib/goal-candidates";
import { matchSides, pairing } from "@/lib/match-sides";
import { useOpponentName } from "@/lib/opponent";
import { ownName } from "@/lib/own-name";
import { QUICK_ANSWERS, quickBody, quickQueue, quickWindow, startSide, type QuickAnswer, type ShotCandidate } from "@/lib/shot-candidates";
import { cn } from "@/lib/utils";
import { useShotCandidates, useShotReview } from "../shot-candidates";

type Match = Schemas["MatchOut"];

/**
 * «Würfe schnell prüfen»: the shots the analysis found, one after the other, each as a short clip
 * from shortly before the shot, looped; four big answers under it (Tor, Gehalten, Daneben, Kein
 * Wurf; keys 1 to 4), in reach of the thumb on a phone; on to the next by itself, «7 von 23»,
 * «Rückgängig». The least sure first. Saved through the same review as the shot list of the
 * workbench (useShotReview): one truth.
 */
export function ShotQuick({ orgId, match }: { orgId: string; match: Match }) {
  const t = useTranslations("shotQuick");
  const tc = useTranslations("check");
  const ta = useTranslations("anlauf");
  const tAll = useTranslations();
  const { org, teams } = useShell();
  const oppName = useOpponentName()(match);
  const sides = matchSides(match, { team: ownName(teams.find((x) => x.id === match.team_id)?.name, org.name), opponent: oppName, otherFallback: tAll("progress.otherTeam") });
  const q = useShotCandidates(orgId, match.id);
  const [error, setError] = useState<ErrorKey | "needSide" | null>(null);
  const review = useShotReview(orgId, match.id, { start: () => setError(null), error: (e) => setError(errorKey(e)) });
  // the questions taken once when the screen opens: answering does not shuffle them, undo goes back
  const [queue, setQueue] = useState<ShotCandidate[] | null>(() => (q.data ? quickQueue(q.data) : null));
  useEffect(() => {
    if (!queue && q.data) setQueue(quickQueue(q.data));
  }, [queue, q.data]);
  const [at, setAt] = useState(0);
  // the team of the shot that is up: the analysis' (or the report's) guess, changeable
  const [side, setSide] = useState<CandidateSide | null>(null);
  // without a guess from the analysis, the team chosen last is offered, marked as a suggestion
  const [lastSide, setLastSide] = useState<CandidateSide | null>(null);
  const [suggested, setSuggested] = useState(false);
  const player = useRef<PlayerHandle>(null);
  const back = `/app/${orgId}/matches/${match.id}/check`;
  const shot = queue?.[at] ?? null;
  const total = queue?.length ?? 0;
  // the team of a new shot starts at its guess (kept per shot id, so undo shows it again)
  const [sideFor, setSideFor] = useState<string | null>(null);
  if (shot && sideFor !== shot.id) {
    setSideFor(shot.id);
    const start = startSide(shot, lastSide);
    setSide(start.side);
    setSuggested(start.suggested);
    setError(null);
  }
  const team = (s: CandidateSide | null) => (s === "own" ? sides.own : s === "opponent" ? oppName : null);
  const when = (c: ShotCandidate) => (c.clock_s != null ? tAll("events.at", { period: c.period ?? 1, clock: formatClock(c.clock_s * 1000) }) : formatClock(c.goal_ms));

  const answer = useCallback(
    (a: QuickAnswer) => {
      if (!shot || review.isPending) return;
      const body = quickBody(shot, side, a);
      if (!body) return setError("needSide");
      if (side) setLastSide(side);
      review.mutate({ id: shot.id, body });
      setAt((n) => n + 1);
    },
    [shot, side, review],
  );
  const undo = useCallback(() => {
    if (at === 0 || !queue) return;
    const prev = queue[at - 1]!;
    review.mutate({ id: prev.id, body: { status: null } });
    setAt((n) => n - 1);
  }, [at, queue, review]);
  // keys: 1 to 4 answer, U or Backspace undo, Space plays the clip again
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || (e.target as HTMLElement)?.closest("input, textarea, select")) return;
      const i = Number(e.key) - 1;
      if (i >= 0 && i < QUICK_ANSWERS.length) return (e.preventDefault(), answer(QUICK_ANSWERS[i]!));
      if (e.key === "u" || e.key === "U" || e.key === "Backspace") return (e.preventDefault(), undo());
      // Space presses a focused button, link or slider as everywhere; elsewhere it plays the clip again
      if (e.key === " " && !(e.target as HTMLElement)?.closest("button, a, summary, [role=button], [role=slider], [role=tab]")) return (e.preventDefault(), player.current?.restart?.());
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [answer, undo]);
  // after an answer (or undo) the next question takes the focus, so a screen reader reads it and
  // Tab goes on from there; not when the focus is elsewhere (the player, the link at the top)
  const heading = useRef<HTMLHeadingElement>(null);
  const answers = useRef<HTMLElement>(null);
  const shownAt = useRef(at);
  useEffect(() => {
    if (shownAt.current === at) return;
    shownAt.current = at;
    const active = document.activeElement;
    if (!active || active === document.body || answers.current?.contains(active)) heading.current?.focus({ preventScroll: true });
  }, [at, shot]);

  const media = shot ? `/v1/orgs/${orgId}/videos/${shot.video_asset_id}/media/hls/master.m3u8` : null;
  return (
    <div style={matchStyle([org.primary_color, org.secondary_color ?? null], match.opponent_colors ? [match.opponent_colors.color, match.opponent_colors.second ?? null] : null) as CSSProperties} data-testid="shot-quick">
      <div className="bleed-x -mt-px flex h-[60px] items-center justify-between gap-3 border-b-2 border-ink px-4 md:px-8">
        <span className="min-w-0 truncate text-[15px] font-bold">{t("top", { pairing: pairing(sides, ta("vsShort")) })}</span>
        <Link href={back} className="inline-flex min-h-11 shrink-0 items-center border-2 border-ink px-3.5 text-[15px] font-bold whitespace-nowrap text-ink no-underline">
          {tc("later")}
        </Link>
      </div>
      {!queue ? (
        <p className="py-10 text-ink-2">{tc("loading")}</p>
      ) : !shot ? (
        <div className="max-w-[60ch] space-y-4 py-10" data-testid="shot-quick-done">
          <h1 ref={heading} tabIndex={-1} className="text-[40px] outline-none md:text-[58px]">
            {total === 0 ? t("none") : t("done")}
          </h1>
          {total > 0 && <p className="text-[17px] text-ink-2">{t("doneText", { n: total })}</p>}
          <div className="flex flex-wrap gap-3">
            {total > 0 && (
              <button type="button" onClick={undo} className="min-h-12 cursor-pointer border-2 border-ink bg-transparent px-5 font-bold text-ink" data-testid="shot-quick-undo">
                {t("undo")}
              </button>
            )}
            <Link href={back} className="inline-flex min-h-12 items-center border-2 border-ink bg-ink px-5 font-bold text-ground no-underline" data-testid="shot-quick-back">
              {t("back")}
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid gap-2 py-2 md:grid-cols-[minmax(0,1fr)_420px] md:gap-14 md:py-10">
          <figure className="relative m-0 self-start bg-court-bar">
            {media && <VideoPlayer ref={player} key={shot.id} src={media} window={quickWindow(shot)} autoPlay bare loop />}
            <figcaption className="flex items-center justify-between gap-x-3 bg-court-bar px-3 py-1.5 text-court-text">
              <span className="font-mono text-[13px] font-semibold">{when(shot)}</span>
              <button type="button" onClick={() => player.current?.restart?.()} className="min-h-11 cursor-pointer border-[1.5px] border-court-text bg-transparent px-3 text-[15px] font-bold text-white" data-testid="shot-quick-replay">
                {t("replay")}
              </button>
            </figcaption>
          </figure>
          <section ref={answers} aria-labelledby="shot-quick-question" className="flex flex-col" data-testid="shot-quick-step">
            <div className="flex items-center justify-between gap-3">
              {/* «2 von 23» is said when it changes */}
              <p className="m-0 text-[15px] font-semibold md:text-[17px]" aria-live="polite" aria-atomic="true" data-testid="shot-quick-count">
                {t("count", { n: at + 1, total })}
              </p>
              {at > 0 && (
                <button type="button" onClick={undo} className="min-h-11 cursor-pointer border-0 bg-transparent p-0 text-[15px] font-bold text-ink underline decoration-[1.5px] underline-offset-4" data-testid="shot-quick-undo">
                  {t("undo")}
                </button>
              )}
            </div>
            <h1 ref={heading} id="shot-quick-question" tabIndex={-1} className="mt-1 mb-0 text-[32px] leading-[.95] outline-none md:mt-2 md:text-[52px]">
              {t("question")}
            </h1>
            {/* whose shot: the analysis' guess, one tap changes it */}
            <div className="mt-3 flex flex-wrap items-center gap-2" role="group" aria-label={t("whose")}>
              <span className="text-[15px] text-ink-2">{t("whose")}</span>
              {(["own", "opponent"] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  aria-pressed={side === s}
                  onClick={() => (setSide(s), setSuggested(false), setError(null))}
                  className={cn("min-h-11 cursor-pointer border-2 border-ink px-3 text-[15px] font-bold", side === s ? "bg-ink text-ground" : "bg-transparent text-ink", error === "needSide" && "border-attn")}
                  data-testid={`shot-quick-side-${s}`}
                >
                  {team(s)}
                </button>
              ))}
            </div>
            {suggested && side && (
              <p className="m-0 mt-1 text-[15px] text-ink-2" data-testid="shot-quick-suggested">
                {t("suggestedSide", { team: team(side) ?? "" })}
              </p>
            )}
            {error && (
              <p role="alert" className="mt-3 max-w-[54ch] border-l-4 border-loss pl-3 text-[15px] font-semibold" data-testid="shot-quick-error">
                {error === "needSide" ? t("needSide") : tc("saveFailed")}
              </p>
            )}
            {/* the answers at the bottom on a phone, in reach of the thumb (Prüfen is a full-screen tool:
                no tab bar under them), clear of the iPhone's home bar */}
            <div className="mt-4 grid grid-cols-2 gap-2 max-md:sticky max-md:bottom-0 max-md:bg-ground max-md:pt-2 max-md:pb-[calc(env(safe-area-inset-bottom)+0.5rem)]" data-testid="shot-quick-answers">
              {QUICK_ANSWERS.map((a, i) => (
                <button
                  key={a}
                  type="button"
                  onClick={() => answer(a)}
                  // not disabled while saving: a disabled button drops the focus (answer() waits itself)
                  aria-disabled={review.isPending || undefined}
                  aria-keyshortcuts={String(i + 1)}
                  className={cn(
                    "flex min-h-16 cursor-pointer items-center justify-between gap-2 border-2 border-ink px-4 text-left text-[19px] font-bold aria-disabled:opacity-60",
                    a === "none" ? "bg-transparent text-ink" : "bg-ink text-ground",
                  )}
                  data-testid={`shot-quick-${a}`}
                >
                  <span>{t(`answer_${a}`)}</span>
                  {/* the key is in aria-keyshortcuts; in the name it read «Tor1» */}
                  <kbd aria-hidden className="font-mono text-[13px] font-normal opacity-70 max-md:hidden">
                    {i + 1}
                  </kbd>
                </button>
              ))}
            </div>
            <div className="mt-6 flex gap-[3px]" role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={at} aria-label={t("count", { n: at, total })}>
              {queue.map((c, i) => (
                <i key={c.id} className={cn("block h-1.5 flex-1", i < at ? "bg-ink" : "bg-rule")} />
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
