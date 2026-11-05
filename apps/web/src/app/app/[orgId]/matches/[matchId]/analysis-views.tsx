"use client";

import type { Schemas } from "@handball/api-client";
import { ZONE_LABELS } from "@handball/court";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useRef, useState } from "react";
import { CourtHalf, ShotDot } from "@/components/analysis/court-half";
import { EventList, type EventFilter } from "@/components/analysis/event-list";
import { GoalGrid } from "@/components/analysis/goal-grid";
import { InsightsCard } from "@/components/analysis/insights";
import { Sheet, EmptyState } from "@/components/ui/card";
import { api } from "@/lib/client";
import { decided } from "@/lib/match-decided";
import { cn } from "@/lib/utils";
import { useOpponentName } from "@/lib/opponent";

type ZoneCount = Record<string, { shots: number; goals: number }>;
interface TeamStats {
  goals: number;
  shots: number;
  shots_blocked: number;
  misses: number;
  posts: number;
  shooting_pct: number | null;
  saves: number;
  save_pct: number | null;
  goals_against: number;
  turnovers: number;
  turnovers_by_type: Record<string, number>;
  seven_m_goals: number;
  seven_m_shots: number;
  fast_break_goals: number;
  suspensions: number;
  attack_efficiency: number | null;
  possessions?: number | null;
  zones: ZoneCount;
  goal_zones: ZoneCount;
  by_situation: Record<string, { shots: number; goals: number; pct: number | null }>;
  xg: number;
}
interface PlayerRow {
  side: "own" | "opponent";
  player_id: string | null;
  number: number | null;
  goals: number;
  shots: number;
  misses: number;
  posts: number;
  saved: number;
  blocked: number;
  turnovers: number;
  suspensions: number;
  assists: number;
  seven_m_goals: number;
  seven_m_shots: number;
  saves: number;
  xg: number;
}
type ZoneSaves = Record<string, { faced: number; saves: number }>;
export interface KeeperRow {
  side: "own" | "opponent";
  player_id: string | null;
  number: number | null;
  faced: number;
  saves: number;
  goals_against: number;
  save_pct: number | null;
  xg_against: number;
  gsax: number;
  seven_m: { faced: number; saves: number };
  goal_zones: ZoneSaves;
  shot_zones: ZoneSaves;
}
export interface Stats {
  own: TeamStats;
  opponent: TeamStats;
  players: Record<string, PlayerRow>;
  goalkeepers?: Record<string, KeeperRow>;
  timeline: {
    score: { clock_s: number; own: number; opp: number }[];
    best_run: Record<string, { goals: number; from_s: number | null }>;
    longest_own_drought_s: { seconds: number };
  };
  quality: { events: number; sources: Record<string, number>; attempts_known?: boolean };
  possessions_source?: string;
}

export function useStats(orgId: string, matchId: string) {
  return useQuery({
    queryKey: ["stats", matchId],
    queryFn: async () =>
      ((await api.GET("/v1/orgs/{org_id}/matches/{match_id}/stats", { params: { path: { org_id: orgId, match_id: matchId } } }))
        .data ?? null) as Stats | null,
  });
}

// a share above 100 % means the sources disagree (goals from a report, attacks from a clip): no figure
const pct = (v: number | null | undefined) => (v == null || v > 1 ? "-" : `${Math.round(v * 100)} %`);

/** A number that opens the events behind it. */
function N({ value, onClick, label }: { value: string | number; onClick?: () => void; label: string }) {
  // zeros stay quiet; figures in ink (red means goal against or error), a dotted line says "opens the scenes"
  if (value === 0 || value === "0") return <span className="tabular-nums text-muted">{value}</span>;
  if (!onClick) return <span className="tabular-nums">{value}</span>;
  return (
    <button type="button" onClick={onClick} aria-label={label} className="tabular-nums font-semibold underline decoration-foreground/35 decoration-dotted underline-offset-4 hover:decoration-accent hover:decoration-solid">
      {value}
    </button>
  );
}

export interface ViewProps {
  orgId: string;
  match: Schemas["MatchOut"];
  teamName: string;
  stats: Stats;
  onPlay?: (t_ms: number) => void;
  names: Record<string, string>;
  staff?: boolean;
}

function useDrill() {
  const [drill, setDrill] = useState<{ title: string; filter: EventFilter } | null>(null);
  return { drill, open: (title: string, filter: EventFilter) => setDrill({ title, filter }), close: () => setDrill(null) };
}

function Drill({ drill, orgId, matchId, onPlay, names, close }: { drill: ReturnType<typeof useDrill>["drill"]; orgId: string; matchId: string; onPlay?: (t: number) => void; names: Record<string, string>; close: () => void }) {
  const t = useTranslations("common");
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (drill) ref.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [drill]);
  if (!drill) return null;
  return (
    <Sheet className="space-y-2" ref={ref}>
      <EventList orgId={orgId} matchId={matchId} filter={drill.filter} title={drill.title} onPlay={onPlay} names={names} />
      <button className="text-sm text-muted underline" onClick={close}>
        {t("close")}
      </button>
    </Sheet>
  );
}

export function OverviewView({ orgId, match, teamName, stats, onPlay, names, staff = false, videoNote = null }: ViewProps & { videoNote?: string | null }) {
  const t = useTranslations("stats");
  const te = useTranslations("events");
  const oppName = useOpponentName();
  const { drill, open, close } = useDrill();
  const attempts = stats.quality.attempts_known !== false;
  const rows: { label: string; own: string | number; opp: string | number; filter?: (s: "own" | "opponent") => EventFilter }[] = [
    { label: t("goals"), own: stats.own.goals, opp: stats.opponent.goals, filter: (s) => ({ side: s, type: "shot", outcome: "goal" }) },
    // goals alone (score overlay): shot counts and xG would only repeat the goals
    ...(attempts ? [{ label: t("shots"), own: stats.own.shots, opp: stats.opponent.shots, filter: (s: "own" | "opponent") => ({ side: s, type: "shot" }) as EventFilter }] : []),
    { label: t("shootingPct"), own: pct(stats.own.shooting_pct), opp: pct(stats.opponent.shooting_pct) },
    ...(attempts ? [{ label: t("saves"), own: stats.own.saves, opp: stats.opponent.saves, filter: (s: "own" | "opponent") => ({ side: s === "own" ? "opponent" : "own", type: "shot", outcome: "save" }) as EventFilter }] : []),
    { label: t("savePct"), own: pct(stats.own.save_pct), opp: pct(stats.opponent.save_pct) },
    { label: t("turnovers"), own: stats.own.turnovers, opp: stats.opponent.turnovers, filter: (s) => ({ side: s, type: "turnover" }) },
    ...(stats.own.seven_m_shots + stats.opponent.seven_m_shots > 0 ? [{ label: t("sevenM"), own: `${stats.own.seven_m_goals}/${stats.own.seven_m_shots}`, opp: `${stats.opponent.seven_m_goals}/${stats.opponent.seven_m_shots}` }] : []),
    { label: t("fastBreakGoals"), own: stats.own.fast_break_goals, opp: stats.opponent.fast_break_goals, filter: (s) => ({ side: s, zone: "fast_break", outcome: "goal" }) },
    ...(stats.own.suspensions + stats.opponent.suspensions > 0
      ? [{ label: t("suspensions"), own: stats.own.suspensions, opp: stats.opponent.suspensions, filter: (s: "own" | "opponent") => ({ side: s, type: "suspension_2min" }) as EventFilter }]
      : []),
    { label: t("efficiency"), own: pct(stats.own.attack_efficiency), opp: pct(stats.opponent.attack_efficiency) },
    { label: t("xg"), own: attempts ? stats.own.xg.toFixed(1) : "-", opp: attempts ? stats.opponent.xg.toFixed(1) : "-" },
  ];
  const run = stats.timeline.best_run.own;
  const result =
    match.score_own == null || match.score_opponent == null ? null : match.score_own > match.score_opponent ? "won" : match.score_own < match.score_opponent ? "lost" : "draw";
  const decision = result ? decided(stats.own, stats.opponent, result) : null;
  const edgeFigures = {
    saves: { a: pct(stats.own.save_pct), b: pct(stats.opponent.save_pct) },
    shooting: { a: pct(stats.own.shooting_pct), b: pct(stats.opponent.shooting_pct) },
    turnovers: { a: stats.own.turnovers, b: stats.opponent.turnovers },
    fastBreaks: { a: stats.own.fast_break_goals, b: stats.opponent.fast_break_goals },
  };
  // where the figures come from, and where they disagree with the result: said, not hidden
  const sources = Object.entries(stats.quality.sources)
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([k, n]) =>
      t.has(`basis_${k}` as "basis_heuristic")
        ? t(`basis_${k}` as "basis_heuristic", { n })
        : `${n} ${te.has(`source_${k}` as "source_model") ? te(`source_${k}` as "source_model") : k}`,
    )
    .join(", ");
  const mismatch =
    match.score_own != null && match.score_opponent != null && (stats.own.goals !== match.score_own || stats.opponent.goals !== match.score_opponent);
  const scorers = Object.values(stats.players)
    .filter((p) => p.side === "own" && p.goals > 0)
    .sort((a, b) => b.goals - a.goals || (a.number ?? 99) - (b.number ?? 99))
    .slice(0, 8);
  const who = (p: (typeof scorers)[number]) => (p.player_id && names[p.player_id]) || `#${p.number ?? "?"}`;
  return (
    <div className="space-y-10">
      <div className="space-y-1 text-sm" data-testid="analysis-basis">
        <p>
          {t("basis", { list: sources })}
          {videoNote && ` ${videoNote}`}
        </p>
        {mismatch && (
          <p className="font-medium">
            {t("scoreMismatch", { events: `${stats.own.goals}:${stats.opponent.goals}`, score: `${match.score_own}:${match.score_opponent}` })}
          </p>
        )}
      </div>
      {decision && (
        // the one statement of the tab: what decided the match, from the head-to-head figures
        <p className="max-w-3xl font-display text-2xl leading-tight sm:text-3xl" data-testid="decided">
          {t(decision.side === "own" ? "decidedOwn" : "decidedOpp", {
            list: decision.edges.map((e) => t(`edge_${e}`, edgeFigures[e])).join(` ${t("and")} `),
          })}
        </p>
      )}
      <InsightsCard
        noSignal={decision != null}
        orgId={orgId}
        matchId={match.id}
        names={names}
        staff={staff}
        onEvidence={open}
        won={match.score_own != null && match.score_opponent != null && match.score_own > match.score_opponent}
      />
      <div className="grid gap-10 lg:grid-cols-2 lg:gap-x-12">
        <Sheet className="space-y-3">
          <h2 className="font-semibold">{t("timeline")}</h2>
          <ScoreChart
            points={stats.timeline.score}
            own={teamName}
            opp={oppName(match)}
            periodS={match.period_s}
            periods={match.periods}
          />
          <ul className="text-sm text-muted">
            {run && run.goals > 1 && <li>{t("bestRun", { goals: run.goals })}</li>}
            {stats.timeline.longest_own_drought_s.seconds > 0 && (
              <li>{t("drought", { minutes: Math.round(stats.timeline.longest_own_drought_s.seconds / 60) })}</li>
            )}
          </ul>
        </Sheet>
        <Sheet className="space-y-3">
          <h2 className="font-semibold">{t("comparison")}</h2>
          <table className="w-full text-sm" data-testid="comparison">
            <thead className="text-muted">
              <tr>
                <th scope="col" className="text-left font-normal" />
                <th scope="col" className="text-right font-medium">{teamName}</th>
                <th scope="col" className="text-right font-medium">{oppName(match)}</th>
              </tr>
            </thead>
            <tbody>
              {rows
                // a row without a figure on either side says nothing
                .filter((r) => !(r.own === "-" && r.opp === "-"))
                .map((r) => (
                <tr key={r.label} className="border-t border-border/70">
                  <th scope="row" className="py-1.5 text-left font-normal">{r.label}</th>
                  <td className="text-right">
                    <N value={r.own} label={`${r.label} ${teamName}`} onClick={r.filter && (() => open(`${r.label}: ${teamName}`, r.filter!("own")))} />
                  </td>
                  <td className="text-right">
                    <N value={r.opp} label={`${r.label} ${oppName(match)}`} onClick={r.filter && (() => open(`${r.label}: ${oppName(match)}`, r.filter!("opponent")))} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-muted">{t(stats.possessions_source === "tracking" ? "possessionsTracked" : "possessionsHint")}</p>
        </Sheet>
      </div>
      {scorers.length > 0 && (
        <Sheet className="space-y-3">
          <h2 className="font-semibold">{t("scorers")}</h2>
          <ul className="grid gap-x-10 sm:grid-cols-2">
            {scorers.map((p) => (
              <li key={`${p.player_id}-${p.number}`} className="flex items-baseline justify-between gap-3 border-b border-border/70 py-1.5 text-sm">
                <span className="min-w-0 truncate">{who(p)}</span>
                <N
                  value={p.shots ? `${p.goals}/${p.shots}` : p.goals}
                  label={`${t("goals")} ${who(p)}`}
                  onClick={() => open(`${t("goals")}: ${who(p)}`, { ...(p.player_id ? { player_id: p.player_id } : { side: "own" as const, number: p.number ?? undefined }), type: "shot", outcome: "goal" })}
                />
              </li>
            ))}
          </ul>
        </Sheet>
      )}
      <Drill drill={drill} orgId={orgId} matchId={match.id} onPlay={onPlay} names={names} close={close} />
    </div>
  );
}

function ScoreChart({
  points,
  own,
  opp,
  periodS,
  periods,
}: {
  points: { clock_s: number; own: number; opp: number }[];
  own: string;
  opp: string;
  periodS: number;
  periods: number;
}) {
  const w = 600;
  const h = 210;
  const right = 34;
  const maxT = Math.max(periodS * periods, ...points.map((p) => p.clock_s));
  const tickStep = maxT > 2400 ? 15 : 5;
  const ticks = Array.from({ length: Math.floor(maxT / 60 / tickStep) + 1 }, (_, i) => i * tickStep);
  const maxG = Math.max(5, ...points.map((p) => Math.max(p.own, p.opp)));
  const gridStep = maxG > 20 ? 10 : 5;
  const grid = Array.from({ length: Math.floor(maxG / gridStep) + 1 }, (_, i) => i * gridStep);
  const X = (s: number) => 28 + (s / maxT) * (w - 28 - right);
  const Y = (g: number) => h - 22 - (g / maxG) * (h - 34);
  const step = (key: "own" | "opp") =>
    points.map((p, i) => `${i ? `H${X(p.clock_s)}` : `M${X(0)} ${Y(0)} H${X(p.clock_s)}`} V${Y(p[key])}`).join(" ") + ` H${X(maxT)}`;
  const timed = points.every((p) => p.clock_s > 0 || (p.own === 0 && p.opp === 0));
  const last = points.at(-1) ?? { own: 0, opp: 0 };
  // end labels: keep them apart when the score is close
  let yo = Y(last.own);
  let yp = Y(last.opp);
  if (Math.abs(yo - yp) < 13) {
    const mid = (yo + yp) / 2;
    const up = last.own >= last.opp;
    yo = mid + (up ? -7 : 7);
    yp = mid + (up ? 7 : -7);
  }
  return (
    <figure className="space-y-3">
      <figcaption className="flex flex-wrap gap-x-5 gap-y-1 text-[0.8125rem]">
        <span className="inline-flex items-center gap-2 font-medium">
          <span aria-hidden className="h-0.5 w-5 rounded-full bg-accent" />
          {own}
        </span>
        <span className="inline-flex items-center gap-2 text-muted">
          <span aria-hidden className="h-0 w-5 border-t-2 border-dashed border-muted" />
          {opp}
        </span>
      </figcaption>
      <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={`${own} ${last.own}, ${opp} ${last.opp}`} className="w-full">
        {grid.map((g) => (
          <g key={g}>
            <line x1={X(0)} x2={X(maxT)} y1={Y(g)} y2={Y(g)} stroke="var(--border)" strokeWidth={g === 0 ? 1.2 : 0.6} />
            <text x={X(0) - 8} y={Y(g) + 3.5} fontSize="10" textAnchor="end" fill="var(--muted)">
              {g}
            </text>
          </g>
        ))}
        {Array.from({ length: periods - 1 }, (_, i) => (
          <line key={i} x1={X((i + 1) * periodS)} x2={X((i + 1) * periodS)} y1={8} y2={h - 22} stroke="var(--muted)" strokeOpacity={0.4} strokeDasharray="3 4" />
        ))}
        {ticks.map((m) => (
          <text key={m} x={X(m * 60)} y={h - 6} fontSize="10" textAnchor="middle" fill="var(--muted)">
            {m}&apos;
          </text>
        ))}
        {timed && <path d={step("opp")} fill="none" stroke="var(--muted)" strokeWidth={1.8} strokeDasharray="5 3" />}
        {timed && <path d={step("own")} fill="none" stroke="var(--accent)" strokeWidth={2.5} strokeLinejoin="round" />}
        {timed && (
          <>
            <text x={X(maxT) + 6} y={yo + 4} fontSize="12" fontWeight="700" fill="var(--accent)">
              {last.own}
            </text>
            <text x={X(maxT) + 6} y={yp + 4} fontSize="12" fontWeight="600" fill="var(--muted)">
              {last.opp}
            </text>
          </>
        )}
      </svg>
    </figure>
  );
}

export function ReportView({ orgId, match, stats, onPlay, names }: ViewProps) {
  const t = useTranslations("stats");
  const te = useTranslations("events");
  const { drill, open, close } = useDrill();
  const own = Object.values(stats.players).filter((p) => p.side === "own" && (p.player_id || p.number != null));
  own.sort((a, b) => b.goals - a.goals || (a.number ?? 99) - (b.number ?? 99));
  const opp = Object.values(stats.players).filter((p) => p.side === "opponent" && p.number != null);
  opp.sort((a, b) => b.goals - a.goals);
  const sheet = ((match.report_extra as { names?: Record<string, string> } | null)?.names ?? {}) as Record<string, string>;
  // the number has its own column: the name goes without it
  const nameOf = (p: PlayerRow) =>
    ((p.player_id && names[p.player_id]) || "").replace(/^#\d+\s+/, "") ||
    (p.side === "own" && p.number != null && sheet[String(p.number)]) ||
    `#${p.number ?? "?"}`;
  const base = (p: PlayerRow): EventFilter => (p.player_id ? { player_id: p.player_id } : { side: p.side, number: p.number ?? undefined });
  const cols: { key: keyof PlayerRow; label: string; filter?: EventFilter }[] = [
    { key: "goals", label: t("goals"), filter: { type: "shot", outcome: "goal" } },
    { key: "shots", label: t("shots"), filter: { type: "shot" } },
    { key: "misses", label: t("misses"), filter: { type: "shot", outcome: "miss" } },
    { key: "posts", label: t("posts"), filter: { type: "shot", outcome: "post" } },
    { key: "blocked", label: t("blocked"), filter: { type: "shot", outcome: "blocked" } },
    { key: "turnovers", label: t("turnovers"), filter: { type: "turnover" } },
    { key: "suspensions", label: t("suspensions"), filter: { type: "suspension_2min" } },
    { key: "assists", label: t("assists") },
    { key: "saves", label: t("saves") },
  ];
  const table = (rows: PlayerRow[], caption: string) => {
    // like a printed match sheet: columns that are zero for everyone are left out
    const used = cols.filter((c) => rows.some((p) => Number(p[c.key] ?? 0) > 0));
    // the one mark of the sheet: who lost the ball most often (own team, at least three)
    const mostTurnovers = rows === own ? [...rows].sort((a, b) => b.turnovers - a.turnovers).find((p) => p.turnovers >= 3) : undefined;
    return (
    <div className="overflow-x-auto border-t-2 border-foreground">
      <table className="w-full text-sm" data-testid="report-table">
        <caption className="sr-only">{caption}</caption>
        <thead className="text-xs text-muted">
          <tr>
            <th scope="col" className="px-3 py-2 text-left font-medium">{t("player")}</th>
            {used.map((c) => (
              <th key={c.key} scope="col" className="px-2 py-2 text-right font-medium">{c.label}</th>
            ))}
            <th scope="col" className="px-2 py-2 text-right font-medium">{t("shootingPct")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={`${p.player_id}-${p.number}`} className="border-t border-border/70">
              <th scope="row" className="px-3 py-1.5 text-left font-medium whitespace-nowrap">
                {p.number != null && <span className="mr-2 inline-block w-5 text-right font-score text-accent tabular-nums">{p.number}</span>}
                {nameOf(p)}
              </th>
              {used.map((c) => (
                <td
                  key={c.key}
                  className={cn(
                    "px-2 py-1.5 text-right font-score text-base tabular-nums",
                    c.key === "turnovers" && p === mostTurnovers && "underline decoration-resin decoration-[5px] underline-offset-[5px]",
                  )}
                >
                  <N
                    value={p[c.key] as number}
                    label={`${c.label} ${nameOf(p)}`}
                    onClick={c.filter && (() => open(`${c.label}: ${nameOf(p)}`, { ...base(p), ...c.filter }))}
                  />
                </td>
              ))}
              <td className="px-2 py-1.5 text-right tabular-nums">{p.shots ? `${Math.round((p.goals / p.shots) * 100)} %` : "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    );
  };
  const tt = stats.own.turnovers_by_type;
  return (
    <div className="space-y-4">
      {table(own, t("player"))}
      {Object.keys(tt).length > 0 && (
        <p className="text-sm">
          <span className="font-medium">{t("turnovers")} {t("byType")}: </span>
          {Object.entries(tt).map(([k, v], i) => (
            <span key={k}>
              {i > 0 && " · "}
              {te(`tt_${k}` as "tt_other")}{" "}
              <N value={v} label={`${te(`tt_${k}` as "tt_other")}`} onClick={() => open(te(`tt_${k}` as "tt_other"), { side: "own", type: "turnover", turnover_type: k })} />
            </span>
          ))}
        </p>
      )}
      {opp.length > 0 && (
        <details>
          <summary className="cursor-pointer text-sm font-medium">{t("opponentPlayers")}</summary>
          <div className="mt-2">{table(opp, t("opponentPlayers"))}</div>
        </details>
      )}
      <Drill drill={drill} orgId={orgId} matchId={match.id} onPlay={onPlay} names={names} close={close} />
    </div>
  );
}

export function ShotsView({ orgId, match, teamName, stats, onPlay, names }: ViewProps) {
  const t = useTranslations("shotsView");
  const oppName = useOpponentName();
  const { drill, open, close } = useDrill();
  const [side, setSide] = useState<"own" | "opponent">("own");
  const [outcome, setOutcome] = useState<string>("");
  const shots = useQuery({
    queryKey: ["events", match.id, { type: "shot", side }],
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/events", {
        params: { path: { org_id: orgId, match_id: match.id }, query: { type: "shot", side } },
      })).data ?? [],
  });
  const list = useMemo(() => (shots.data ?? []).filter((e) => !outcome || e.outcome === outcome), [shots.data, outcome]);
  const placed = list.filter((e) => e.x != null && e.y != null);
  const team = side === "own" ? stats.own : stats.opponent;
  // the one mark of the tab: the zone with the lowest rate from at least five shots
  const weakest = Object.entries(team.zones)
    .filter(([, v]) => v.shots >= 5)
    .sort((a, b) => a[1].goals / a[1].shots - b[1].goals / b[1].shots)[0]?.[0];
  return (
    <div className="space-y-10">
      <div className="flex flex-wrap gap-3">
        <div className="flex gap-4" role="group" aria-label={t("filterTeam")}>
          {(["own", "opponent"] as const).map((s) => (
            <button key={s} aria-pressed={side === s} onClick={() => setSide(s)} className={cn("min-h-9 border-b-2 px-1 text-sm font-semibold", side === s ? "border-foreground text-foreground" : "border-transparent text-muted hover:text-foreground")}>
              {s === "own" ? teamName : oppName(match)}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm">
          {t("filterOutcome")}
          <select value={outcome} onChange={(e) => setOutcome(e.target.value)} className="rounded-lg bg-raised ring-1 ring-inset ring-border px-2 py-1">
            <option value="">{t("all")}</option>
            {["goal", "save", "miss", "post", "blocked"].map((o) => (
              <option key={o} value={o}>
                {t(`outcome_${o as "goal"}`)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="grid gap-10 lg:grid-cols-[3fr_2fr] lg:gap-x-12">
        <Sheet className="space-y-2">
          <h2 className="font-semibold">{t("map")}</h2>
          {/* no shot with a position: a sentence, not an empty court */}
          {placed.length === 0 && !shots.isLoading ? (
            <p className="text-sm text-muted">{t("noPositions")}</p>
          ) : (
          <CourtHalf label={t("map")}>
            {placed.map((e) => (
              <ShotDot key={e.id} x={e.x!} y={e.y!} outcome={e.outcome ?? "miss"} title={`${t(`outcome_${(e.outcome ?? "miss") as "goal"}`)}${e.player_id && names[e.player_id] ? ` · ${names[e.player_id]}` : ""}`} />
            ))}
          </CourtHalf>
          )}
          {list.length - placed.length > 0 && <p className="text-xs text-muted">{t("noPosition", { count: list.length - placed.length })}</p>}
        </Sheet>
        <Sheet className="space-y-2">
          <h2 className="font-semibold">{t("goal")}</h2>
          <GoalGrid data={team.goal_zones} onCell={(z) => open(`${t("goal")} ${z}`, { side, type: "shot", goal_zone: z })} />
        </Sheet>
      </div>
      <Sheet className="space-y-2">
        <h2 className="font-semibold">{t("zones")}</h2>
        {Object.keys(team.zones).length === 0 ? (
          <EmptyState title={t("noPosition", { count: list.length })} />
        ) : (
          <ul className="grid gap-x-10 text-sm sm:grid-cols-2">
            {Object.entries(team.zones).sort((a, b) => b[1].shots - a[1].shots).map(([z, v]) => (
              <li key={z} className="flex items-center gap-3 border-b border-border/70 py-1.5">
                <span className={cn("w-40 truncate", z === weakest && "underline decoration-resin decoration-[5px] underline-offset-[5px]")}>{ZONE_LABELS[z] ?? z}</span>
                <span aria-hidden className="h-1.5 flex-1 bg-foreground/10">
                  <span className="block h-full bg-foreground" style={{ width: `${v.shots ? (v.goals / v.shots) * 100 : 0}%` }} />
                </span>
                <N value={`${v.goals}/${v.shots}`} label={`${ZONE_LABELS[z] ?? z}`} onClick={() => open(ZONE_LABELS[z] ?? z, { side, type: "shot", zone: z })} />
              </li>
            ))}
          </ul>
        )}
      </Sheet>
      <Drill drill={drill} orgId={orgId} matchId={match.id} onPlay={onPlay} names={names} close={close} />
    </div>
  );
}
