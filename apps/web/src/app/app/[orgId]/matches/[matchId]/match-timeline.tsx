"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { formatClock } from "@/lib/format";
import type { CandidateList } from "@/lib/goal-candidates";
import { clockAt, covered, inside, type Span } from "@/lib/match-workflow";
import type { GoalComparison } from "@/lib/official-goals";
import { cn } from "@/lib/utils";

type Zoom = "game" | "moment";

/** The match on one axis under the video, drawn like a scoresheet: hairline lanes, the own team
 * above the centre line and the opponent below, proposals as rings and confirmed goals filled.
 * "Spiel" shows the whole match, "Moment" what the video covers (the default when that is a
 * short part of the match). An overview to read at a glance; the lists beside it act on goals. */
export function MatchTimeline({
  spans,
  periodS,
  kickoff,
  nowMs,
  official,
  candidates,
  rate,
  onSetKickoff,
}: {
  spans: Span[] | null;
  periodS: number;
  kickoff: Record<string, number> | null | undefined;
  nowMs: number;
  official: GoalComparison | null | undefined;
  candidates: CandidateList | null | undefined;
  rate: number;
  onSetKickoff?: () => void;
}) {
  const t = useTranslations("workflow");
  const total = periodS * 2;
  const short = spans != null && covered(spans) < total * 0.25;
  const [picked, setZoom] = useState<Zoom | null>(null);
  const zoom: Zoom = picked ?? (short ? "moment" : "game");
  if (!spans) {
    return (
      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-foreground/15 pt-3 text-sm text-muted" data-testid="match-timeline">
        {t("coverageUnknown")}
        {onSetKickoff && (
          <Button variant="ghost" size="sm" className="-my-1" onClick={onSetKickoff}>
            {t("setKickoff")}
          </Button>
        )}
      </p>
    );
  }
  // the visible stretch of match time
  const lo = zoom === "game" || !spans.length ? 0 : Math.max(0, Math.min(...spans.map((s) => s.from)) - pad(spans));
  const hi = zoom === "game" || !spans.length ? total : Math.min(total, Math.max(...spans.map((s) => s.to)) + pad(spans));
  const x = (s: number) => `${Math.min(100, Math.max(0, ((s - lo) / (hi - lo)) * 100))}%`;
  const seen = (s: number) => s >= lo && s <= hi;
  const now = clockAt(kickoff, periodS, nowMs);
  const goals = (official?.imported ? official.goals : []).filter((g) => g.clock_s != null);
  const inVideo = goals.filter((g) => inside(g.clock_s!, spans)).length;
  const cands = (candidates?.candidates ?? []).filter((c) => c.clock_s != null && c.rate <= rate);
  const clip = spans.map((s) => `${formatClock(s.from * 1000)} ${t("to")} ${formatClock(s.to * 1000)}`).join(", ");
  const ticks = zoom === "game" ? [0, 0.25, 0.5, 0.75, 1].map((f) => total * f) : [0, 0.25, 0.5, 0.75, 1].map((f) => lo + (hi - lo) * f);
  const lane = (label: string, children: React.ReactNode, sided = false) => (
    <>
      <span className="font-score text-[0.8125rem] uppercase tracking-wide text-muted">{label}</span>
      <div className="relative h-6 border-b border-foreground/15">
        {spans.map((s) => (
          <span key={s.from} className="absolute inset-y-0 bg-accent/8" style={{ left: x(s.from), width: `calc(${x(s.to)} - ${x(s.from)})` }} />
        ))}
        {sided && <span className="absolute inset-x-0 top-1/2 h-px bg-foreground/10" />}
        {children}
        {now != null && seen(now) && <span className="absolute -inset-y-1 w-0.5 bg-foreground" style={{ left: x(now) }} />}
      </div>
    </>
  );
  return (
    <figure className="space-y-2 border-t border-foreground/15 pt-3" data-testid="match-timeline">
      <figcaption className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm">
        <span className="font-semibold">{t("timeline")}</span>
        <span className="text-muted">
          {t("coverage", { clip })}
          {goals.length > 0 && ` ${t("coverageGoals", { inside: inVideo, total: goals.length })}`}
        </span>
        <span role="group" aria-label={t("zoom")} className="ml-auto flex gap-3">
          {(["moment", "game"] as const).map((z) => (
            <button
              key={z}
              type="button"
              aria-pressed={zoom === z}
              onClick={() => setZoom(z)}
              className={cn(
                "min-h-6 border-b-2 text-[0.8125rem] font-semibold outline-none focus-visible:ring-2 focus-visible:ring-accent",
                zoom === z ? "border-foreground text-foreground" : "border-transparent text-muted hover:text-foreground",
              )}
            >
              {t(`zoom_${z}`)}
            </button>
          ))}
        </span>
      </figcaption>
      <div aria-hidden className="grid grid-cols-[6.5rem_minmax(0,1fr)] items-center gap-x-3">
        {lane(
          t("laneVideo"),
          spans.map((s) => (
            <span key={s.from} className="absolute inset-y-2 bg-accent" style={{ left: x(s.from), width: `calc(${x(s.to)} - ${x(s.from)})` }} />
          )),
        )}
        {goals.length > 0 &&
          lane(
            t("laneReport"),
            goals
              .filter((g) => seen(g.clock_s!))
              .map((g) => (
                <span
                  key={g.event_id}
                  className={cn(
                    "absolute h-[calc(50%-3px)] w-[3px] -translate-x-1/2",
                    g.side === "own" ? "top-0.5" : "bottom-0.5",
                    !inside(g.clock_s!, spans) ? "bg-foreground/20" : g.status === "found" ? "bg-foreground" : "bg-background ring-1 ring-inset ring-foreground",
                  )}
                  style={{ left: x(g.clock_s!) }}
                />
              )),
            true,
          )}
        {cands.length > 0 &&
          lane(
            t("laneCandidates"),
            cands
              .filter((c) => seen(c.clock_s!))
              .map((c) => {
                const side = c.side ?? c.suggested_side;
                return (
                  <span
                    key={c.id}
                    className={cn(
                      "absolute size-2.5 -translate-x-1/2 rounded-full",
                      side === "opponent" ? "bottom-[1px]" : side === "own" ? "top-[1px]" : "top-1/2 -translate-y-1/2",
                      c.status === "confirmed" ? "bg-foreground" : c.status === "rejected" ? "size-1.5 bg-foreground/25" : "border-2 border-foreground bg-background",
                    )}
                    style={{ left: x(c.clock_s!) }}
                  />
                );
              }),
            true,
          )}
        <span className="pt-1 text-[0.75rem] text-muted">{t("legendSides")}</span>
        <div className="relative h-5 pt-1 font-score text-xs text-muted tabular-nums">
          {ticks.map((s, i) => (
            <span key={i} className={cn("absolute", i === 0 ? "" : i === ticks.length - 1 ? "-translate-x-full" : "-translate-x-1/2")} style={{ left: `${(i / (ticks.length - 1)) * 100}%` }}>
              {zoom === "game" ? (s === total / 2 ? `${Math.round(s / 60)}' ${t("halftime")}` : `${Math.round(s / 60)}'`) : formatClock(s * 1000)}
            </span>
          ))}
        </div>
      </div>
    </figure>
  );
}

/** Room around the covered stretch in "Moment": a tenth of it, at least half a minute. */
function pad(spans: Span[]) {
  return Math.max(30, covered(spans) * 0.1);
}
