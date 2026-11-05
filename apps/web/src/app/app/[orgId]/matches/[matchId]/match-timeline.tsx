"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { formatClock } from "@/lib/format";
import type { CandidateList } from "@/lib/goal-candidates";
import { clockAt, inside, type Span } from "@/lib/match-workflow";
import type { GoalComparison } from "@/lib/official-goals";
import { cn } from "@/lib/utils";

/** The whole match on one line: what the video covers, the goals of the official report and the
 * goal candidates, with the playhead. An overview to read at a glance; the lists beside it are the
 * way to act on each goal. */
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
  const pct = (s: number) => `${Math.min(100, Math.max(0, (s / total) * 100))}%`;
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
  const now = clockAt(kickoff, periodS, nowMs);
  const goals = (official?.imported ? official.goals : []).filter((g) => g.clock_s != null);
  const inVideo = goals.filter((g) => inside(g.clock_s!, spans)).length;
  const cands = (candidates?.candidates ?? []).filter((c) => c.clock_s != null && c.rate <= rate);
  const clip = spans.map((s) => `${formatClock(s.from * 1000)} ${t("to")} ${formatClock(s.to * 1000)}`).join(", ");
  const lane = (label: string, children: React.ReactNode) => (
    <>
      <span className="text-[0.8125rem] font-medium text-muted">{label}</span>
      <div className="relative h-5 rounded-xs bg-surface">
        {spans.map((s) => (
          <span key={s.from} className="absolute inset-y-0 bg-accent/12" style={{ left: pct(s.from), width: pct(s.to - s.from) }} />
        ))}
        {children}
        {now != null && <span className="absolute -inset-y-1 w-0.5 bg-foreground" style={{ left: pct(now) }} />}
      </div>
    </>
  );
  return (
    <figure className="space-y-2 border-t border-foreground/15 pt-3" data-testid="match-timeline">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-sm">
        <span className="font-semibold">{t("timeline")}</span>
        <span className="text-muted">
          {t("coverage", { clip })}
          {goals.length > 0 && ` ${t("coverageGoals", { inside: inVideo, total: goals.length })}`}
        </span>
      </figcaption>
      <div aria-hidden className="grid grid-cols-[6.5rem_minmax(0,1fr)] items-center gap-x-3 gap-y-1.5">
        {lane(
          t("laneVideo"),
          spans.map((s) => (
            <span key={s.from} className="absolute inset-y-1 rounded-xs bg-accent" style={{ left: pct(s.from), width: pct(s.to - s.from) }} />
          )),
        )}
        {goals.length > 0 &&
          lane(
            t("laneReport"),
            goals.map((g) => (
              <span
                key={g.event_id}
                className={cn(
                  "absolute inset-y-1 w-[3px] -translate-x-1/2 rounded-[1px]",
                  !inside(g.clock_s!, spans) ? "bg-foreground/20" : g.status === "found" ? "bg-ok" : "bg-warn",
                )}
                style={{ left: pct(g.clock_s!) }}
              />
            )),
          )}
        {cands.length > 0 &&
          lane(
            t("laneCandidates"),
            cands.map((c) => (
              <span
                key={c.id}
                className={cn(
                  "absolute top-1/2 size-2 -translate-1/2 rounded-full",
                  c.status === "confirmed" ? "bg-ok" : c.status === "rejected" ? "bg-foreground/25" : "bg-accent",
                )}
                style={{ left: pct(c.clock_s!) }}
              />
            )),
          )}
        <span />
        <div className="relative h-4 font-score text-xs text-muted">
          {[0, 0.25, 0.5, 0.75, 1].map((f) => (
            <span key={f} className={cn("absolute", f === 0 ? "" : f === 1 ? "-translate-x-full" : "-translate-x-1/2")} style={{ left: `${f * 100}%` }}>
              {f === 0.5 ? `${Math.round((total * f) / 60)}' ${t("halftime")}` : `${Math.round((total * f) / 60)}'`}
            </span>
          ))}
        </div>
      </div>
    </figure>
  );
}
