"use client";

import type { Schemas } from "@handball/api-client";
import { ZONE_LABELS } from "@handball/court";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { CourtHalf, ShotDot } from "@/components/analysis/court-half";
import { EventList, type EventFilter } from "@/components/analysis/event-list";
import { GoalGrid } from "@/components/analysis/goal-grid";
import { Card, EmptyState } from "@/components/ui/card";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";

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
  quality: { events: number; sources: Record<string, number> };
}

export function useStats(orgId: string, matchId: string) {
  return useQuery({
    queryKey: ["stats", matchId],
    queryFn: async () =>
      ((await api.GET("/v1/orgs/{org_id}/matches/{match_id}/stats", { params: { path: { org_id: orgId, match_id: matchId } } }))
        .data ?? null) as Stats | null,
  });
}

const pct = (v: number | null | undefined) => (v == null ? "-" : `${Math.round(v * 100)} %`);

/** A number that opens the events behind it. */
function N({ value, onClick, label }: { value: string | number; onClick?: () => void; label: string }) {
  if (!onClick || value === 0 || value === "0") return <span className="tabular-nums">{value}</span>;
  return (
    <button type="button" onClick={onClick} aria-label={label} className="tabular-nums text-accent underline decoration-dotted underline-offset-4 hover:decoration-solid">
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
}

function useDrill() {
  const [drill, setDrill] = useState<{ title: string; filter: EventFilter } | null>(null);
  return { drill, open: (title: string, filter: EventFilter) => setDrill({ title, filter }), close: () => setDrill(null) };
}

function Drill({ drill, orgId, matchId, onPlay, names, close }: { drill: ReturnType<typeof useDrill>["drill"]; orgId: string; matchId: string; onPlay?: (t: number) => void; names: Record<string, string>; close: () => void }) {
  const t = useTranslations("common");
  if (!drill) return null;
  return (
    <Card className="space-y-2">
      <EventList orgId={orgId} matchId={matchId} filter={drill.filter} title={drill.title} onPlay={onPlay} names={names} />
      <button className="text-sm text-muted underline" onClick={close}>
        {t("close")}
      </button>
    </Card>
  );
}

export function OverviewView({ orgId, match, teamName, stats, onPlay, names }: ViewProps) {
  const t = useTranslations("stats");
  const { drill, open, close } = useDrill();
  const rows: { label: string; own: string | number; opp: string | number; filter?: (s: "own" | "opponent") => EventFilter }[] = [
    { label: t("goals"), own: stats.own.goals, opp: stats.opponent.goals, filter: (s) => ({ side: s, type: "shot", outcome: "goal" }) },
    { label: t("shots"), own: stats.own.shots, opp: stats.opponent.shots, filter: (s) => ({ side: s, type: "shot" }) },
    { label: t("shootingPct"), own: pct(stats.own.shooting_pct), opp: pct(stats.opponent.shooting_pct) },
    { label: t("saves"), own: stats.own.saves, opp: stats.opponent.saves, filter: (s) => ({ side: s === "own" ? "opponent" : "own", type: "shot", outcome: "save" }) },
    { label: t("savePct"), own: pct(stats.own.save_pct), opp: pct(stats.opponent.save_pct) },
    { label: t("turnovers"), own: stats.own.turnovers, opp: stats.opponent.turnovers, filter: (s) => ({ side: s, type: "turnover" }) },
    { label: t("sevenM"), own: `${stats.own.seven_m_goals}/${stats.own.seven_m_shots}`, opp: `${stats.opponent.seven_m_goals}/${stats.opponent.seven_m_shots}` },
    { label: t("fastBreakGoals"), own: stats.own.fast_break_goals, opp: stats.opponent.fast_break_goals, filter: (s) => ({ side: s, zone: "fast_break", outcome: "goal" }) },
    { label: t("suspensions"), own: stats.own.suspensions, opp: stats.opponent.suspensions, filter: (s) => ({ side: s, type: "suspension_2min" }) },
    { label: t("efficiency"), own: pct(stats.own.attack_efficiency), opp: pct(stats.opponent.attack_efficiency) },
    { label: t("xg"), own: stats.own.xg.toFixed(1), opp: stats.opponent.xg.toFixed(1) },
  ];
  const run = stats.timeline.best_run.own;
  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="space-y-3">
          <h2 className="font-semibold">{t("timeline")}</h2>
          <ScoreChart points={stats.timeline.score} own={teamName} opp={match.opponent.name} />
          <ul className="text-sm text-muted">
            {run && run.goals > 1 && <li>{t("bestRun", { goals: run.goals })}</li>}
            {stats.timeline.longest_own_drought_s.seconds > 0 && (
              <li>{t("drought", { minutes: Math.round(stats.timeline.longest_own_drought_s.seconds / 60) })}</li>
            )}
          </ul>
        </Card>
        <Card className="space-y-3">
          <h2 className="font-semibold">{t("comparison")}</h2>
          <table className="w-full text-sm" data-testid="comparison">
            <thead className="text-muted">
              <tr>
                <th scope="col" className="text-left font-normal" />
                <th scope="col" className="text-right font-medium">{teamName}</th>
                <th scope="col" className="text-right font-medium">{match.opponent.name}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.label} className="border-t border-border">
                  <th scope="row" className="py-1.5 text-left font-normal">{r.label}</th>
                  <td className="text-right">
                    <N value={r.own} label={`${r.label} ${teamName}`} onClick={r.filter && (() => open(`${r.label}: ${teamName}`, r.filter!("own")))} />
                  </td>
                  <td className="text-right">
                    <N value={r.opp} label={`${r.label} ${match.opponent.name}`} onClick={r.filter && (() => open(`${r.label}: ${match.opponent.name}`, r.filter!("opponent")))} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-muted">{t("possessionsHint")}</p>
        </Card>
      </div>
      <Drill drill={drill} orgId={orgId} matchId={match.id} onPlay={onPlay} names={names} close={close} />
    </div>
  );
}

function ScoreChart({ points, own, opp }: { points: { clock_s: number; own: number; opp: number }[]; own: string; opp: string }) {
  const w = 600;
  const h = 200;
  const maxT = Math.max(3600, ...points.map((p) => p.clock_s));
  const maxG = Math.max(5, ...points.map((p) => Math.max(p.own, p.opp)));
  const X = (s: number) => 30 + (s / maxT) * (w - 40);
  const Y = (g: number) => h - 20 - (g / maxG) * (h - 30);
  const step = (key: "own" | "opp") =>
    points.map((p, i) => `${i ? `H${X(p.clock_s)}` : `M${X(0)} ${Y(0)} H${X(p.clock_s)}`} V${Y(p[key])}`).join(" ") + ` H${X(maxT)}`;
  const timed = points.every((p) => p.clock_s > 0 || (p.own === 0 && p.opp === 0));
  return (
    <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={`${own} ${points.at(-1)?.own ?? 0}, ${opp} ${points.at(-1)?.opp ?? 0}`} className="w-full">
      <line x1={X(1800)} x2={X(1800)} y1={10} y2={h - 20} stroke="var(--border)" strokeDasharray="4 4" />
      {[0, 15, 30, 45, 60].map((m) => (
        <text key={m} x={X(m * 60)} y={h - 4} fontSize="10" textAnchor="middle" fill="var(--muted)">
          {m}&apos;
        </text>
      ))}
      {timed && <path d={step("own")} fill="none" stroke="var(--accent)" strokeWidth={2.5} />}
      {timed && <path d={step("opp")} fill="none" stroke="var(--muted)" strokeWidth={2} strokeDasharray="5 3" />}
      <text x={w - 6} y={14} fontSize="11" textAnchor="end" fill="var(--accent)">{own}</text>
      <text x={w - 6} y={28} fontSize="11" textAnchor="end" fill="var(--muted)">{opp}</text>
    </svg>
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
  const nameOf = (p: PlayerRow) =>
    (p.player_id && names[p.player_id]) || (p.side === "own" && p.number != null && sheet[String(p.number)]) || `#${p.number ?? "?"}`;
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
  const table = (rows: PlayerRow[], caption: string) => (
    <div className="overflow-x-auto rounded-md border border-border">
      <table className="w-full text-sm" data-testid="report-table">
        <caption className="sr-only">{caption}</caption>
        <thead className="bg-surface text-muted">
          <tr>
            <th scope="col" className="px-3 py-2 text-left font-medium">{t("player")}</th>
            {cols.map((c) => (
              <th key={c.key} scope="col" className="px-2 py-2 text-right font-medium">{c.label}</th>
            ))}
            <th scope="col" className="px-2 py-2 text-right font-medium">{t("shootingPct")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={`${p.player_id}-${p.number}`} className="border-t border-border">
              <th scope="row" className="px-3 py-1.5 text-left font-medium">
                {p.number != null && <span className="mr-2 text-muted tabular-nums">{p.number}</span>}
                {nameOf(p)}
              </th>
              {cols.map((c) => (
                <td key={c.key} className="px-2 py-1.5 text-right">
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
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <div className="flex gap-1" role="group" aria-label={t("filterTeam")}>
          {(["own", "opponent"] as const).map((s) => (
            <button key={s} aria-pressed={side === s} onClick={() => setSide(s)} className={cn("rounded px-3 py-1 text-sm", side === s ? "bg-accent text-accent-contrast" : "bg-surface")}>
              {s === "own" ? teamName : match.opponent.name}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm">
          {t("filterOutcome")}
          <select value={outcome} onChange={(e) => setOutcome(e.target.value)} className="rounded border border-border bg-background px-2 py-1">
            <option value="">{t("all")}</option>
            {["goal", "save", "miss", "post", "blocked"].map((o) => (
              <option key={o} value={o}>
                {t(`outcome_${o as "goal"}`)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="grid gap-4 lg:grid-cols-[3fr_2fr]">
        <Card className="space-y-2">
          <h2 className="font-semibold">{t("map")}</h2>
          <CourtHalf label={t("map")}>
            {placed.map((e) => (
              <ShotDot key={e.id} x={e.x!} y={e.y!} outcome={e.outcome ?? "miss"} title={`${t(`outcome_${(e.outcome ?? "miss") as "goal"}`)}${e.player_id && names[e.player_id] ? ` · ${names[e.player_id]}` : ""}`} />
            ))}
          </CourtHalf>
          {list.length - placed.length > 0 && <p className="text-xs text-muted">{t("noPosition", { count: list.length - placed.length })}</p>}
        </Card>
        <Card className="space-y-2">
          <h2 className="font-semibold">{t("goal")}</h2>
          <GoalGrid data={team.goal_zones} onCell={(z) => open(`${t("goal")} ${z}`, { side, type: "shot", goal_zone: z })} />
        </Card>
      </div>
      <Card className="space-y-2">
        <h2 className="font-semibold">{t("zones")}</h2>
        {Object.keys(team.zones).length === 0 ? (
          <EmptyState title={t("noPosition", { count: list.length })} />
        ) : (
          <ul className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(team.zones).sort((a, b) => b[1].shots - a[1].shots).map(([z, v]) => (
              <li key={z} className="flex justify-between rounded bg-surface px-3 py-2">
                <span>{ZONE_LABELS[z] ?? z}</span>
                <N value={`${v.goals}/${v.shots}`} label={`${ZONE_LABELS[z] ?? z}`} onClick={() => open(ZONE_LABELS[z] ?? z, { side, type: "shot", zone: z })} />
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Drill drill={drill} orgId={orgId} matchId={match.id} onPlay={onPlay} names={names} close={close} />
    </div>
  );
}
