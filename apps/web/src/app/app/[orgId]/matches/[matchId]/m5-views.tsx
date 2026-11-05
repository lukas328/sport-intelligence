"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { CourtHeatmap } from "@/components/analysis/court-full";
import { GoalGrid } from "@/components/analysis/goal-grid";
import { EmptyState, Sheet } from "@/components/ui/card";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";
import type { KeeperRow, ViewProps } from "./analysis-views";
import { useOpponentName } from "@/lib/opponent";

const pct = (v: number | null | undefined) => (v == null ? "-" : `${Math.round(v * 100)} %`);

/** Goalkeeper module (M5): save rate overall, per goal zone and shot zone, 7 m, GSAx. */
export function KeepersView({ match, teamName, stats, names }: ViewProps) {
  const t = useTranslations("keepers");
  const tz = useTranslations("zones");
  const oppName = useOpponentName();
  const sheet = ((match.report_extra as { names?: Record<string, string> } | null)?.names ?? {}) as Record<string, string>;
  const rows = Object.values(stats.goalkeepers ?? {}).sort((a, b) => (a.side === b.side ? b.faced - a.faced : a.side === "own" ? -1 : 1));
  if (rows.length === 0) return <EmptyState title={t("none")}>{t("assignHint")}</EmptyState>;
  const nameOf = (k: KeeperRow) =>
    (k.player_id && names[k.player_id]) ||
    (k.number != null && k.side === "own" && sheet[String(k.number)]) ||
    (k.number != null ? t("number", { number: k.number }) : t("unknown"));
  // one match sheet: a row per goalkeeper, then where they were beaten, side by side
  const teamOf = (k: KeeperRow) => (k.side === "own" ? teamName : oppName(match));
  return (
    <div className="space-y-10">
      <Sheet className="space-y-3">
        <h2 className="font-semibold">{t("title")}</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="keeper-table">
            <thead className="text-xs text-muted">
              <tr>
                <th scope="col" className="py-2 pr-3 text-left font-medium">{t("keeper")}</th>
                <th scope="col" className="px-2 py-2 text-right font-medium">{t("faced")}</th>
                <th scope="col" className="px-2 py-2 text-right font-medium">{t("saves")}</th>
                <th scope="col" className="px-2 py-2 text-right font-medium">{t("savePct")}</th>
                <th scope="col" className="py-2 pl-2 text-right font-medium">{t("sevenM")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((k) => (
                <tr key={`${k.side}-${k.player_id ?? k.number ?? "u"}`} className="border-t border-border/70">
                  <th scope="row" className="py-2 pr-3 text-left font-medium">
                    {nameOf(k)} <span className="font-normal text-muted">{teamOf(k)}</span>
                  </th>
                  <td className="px-2 py-2 text-right font-score text-base tabular-nums">{k.faced}</td>
                  <td className="px-2 py-2 text-right font-score text-base tabular-nums">{k.saves}</td>
                  <td className="px-2 py-2 text-right font-score text-lg tabular-nums">{pct(k.save_pct)}</td>
                  <td className="py-2 pl-2 text-right font-score text-base tabular-nums">
                    {k.seven_m.faced ? `${k.seven_m.saves}/${k.seven_m.faced}` : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Sheet>
      <div className="grid gap-10 lg:grid-cols-2 lg:gap-x-12">
        {rows.map((k) => (
          <Sheet key={`z-${k.side}-${k.player_id ?? k.number ?? "u"}`} className="space-y-4">
            <h3 className="font-semibold">
              {nameOf(k)} <span className="font-normal text-muted">{teamOf(k)}</span>
            </h3>
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted">{t("byGoalZone")}</p>
              <GoalGrid saves data={Object.fromEntries(Object.entries(k.goal_zones).map(([z, v]) => [z, { shots: v.faced, goals: v.saves }]))} />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted">{t("byShotZone")}</p>
              <ul className="text-sm">
                {Object.entries(k.shot_zones)
                  .sort((a, b) => b[1].faced - a[1].faced)
                  .map(([z, v]) => (
                    <li key={z} className="flex items-center gap-3 border-b border-border/70 py-1.5">
                      <span className="w-40 truncate">{tz.has(z as "penalty") ? tz(z as "penalty") : z}</span>
                      <span aria-hidden className="h-1.5 flex-1 bg-foreground/10">
                        <span className="block h-full bg-foreground" style={{ width: `${v.faced ? (v.saves / v.faced) * 100 : 0}%` }} />
                      </span>
                      <span className="w-12 text-right font-score tabular-nums">
                        {v.saves}/{v.faced}
                      </span>
                    </li>
                  ))}
              </ul>
            </div>
          </Sheet>
        ))}
      </div>
    </div>
  );
}

interface PhysRow {
  distance_m: number;
  duration_s: number;
  max_speed_ms: number;
  sprints: number;
  band_distance_m: Record<string, number>;
  heatmap: number[][];
}
interface Physical {
  video_id: string | null;
  players: (PhysRow & { player_id: string; number: number | null; team: string | null; tracks: number[] })[];
  tracks: (PhysRow & { track_no: number; team: string | null; number: number | null; first_ms: number; last_ms: number })[];
}

export function usePhysical(orgId: string, matchId: string) {
  return useQuery({
    queryKey: ["physical", matchId],
    queryFn: async () =>
      ((await api.GET("/v1/orgs/{org_id}/matches/{match_id}/physical", { params: { path: { org_id: orgId, match_id: matchId } } })).data ??
        null) as Physical | null,
  });
}

/** Running load per player from tracking (estimates, M5). */
export function PhysicalView({ orgId, matchId, names }: { orgId: string; matchId: string; names: Record<string, string> }) {
  const t = useTranslations("physical");
  const ta = useTranslations("analysis");
  const q = usePhysical(orgId, matchId);
  const [sel, setSel] = useState<string | null>(null);
  const [showShort, setShowShort] = useState(false);
  const data = q.data;
  if (!data || (data.players.length === 0 && data.tracks.length === 0)) return <EmptyState title={q.isLoading ? "…" : t("none")}>{t("hint")}</EmptyState>;
  const km = (m: number) => (m / 1000).toFixed(2);
  type Row = { key: string; label: string; distance_m: number; band_distance_m: Record<string, number>; sprints: number; max_speed_ms: number; duration_s: number; heatmap: number[][] };
  const own = (team: string | null | undefined) => team === "home" || team === "home_gk";
  const opp = (team: string | null | undefined) => team === "away" || team === "away_gk";
  // team totals over every track of the side: what a single camera saw of the team
  const team = (pick: (team: string | null | undefined) => boolean): Row | null => {
    const ts = [...data.players.filter((p) => pick(p.team)), ...data.tracks.filter((tr) => pick(tr.team))] as unknown as Row[];
    if (ts.length === 0) return null;
    const grid = ts[0]!.heatmap.map((r) => r.map(() => 0));
    for (const tr of ts) tr.heatmap.forEach((r, i) => r.forEach((v, j) => (grid[i]![j]! += v)));
    return {
      key: "team",
      label: "",
      distance_m: ts.reduce((s, x) => s + x.distance_m, 0),
      band_distance_m: { run: ts.reduce((s, x) => s + (x.band_distance_m.run ?? 0) + (x.band_distance_m.sprint ?? 0), 0) },
      sprints: ts.reduce((s, x) => s + x.sprints, 0),
      max_speed_ms: Math.max(...ts.map((x) => x.max_speed_ms)),
      duration_s: Math.max(...ts.map((x) => x.duration_s)),
      heatmap: grid,
    };
  };
  const ownTeam = team(own);
  const oppTeam = team(opp);
  const players: Row[] = data.players.filter((p) => own(p.team)).map((p) => ({ ...(p as unknown as Row), key: `p:${p.player_id}`, label: names[p.player_id] ?? (p.number != null ? `#${p.number}` : "?") }));
  const loose = data.tracks
    .filter((tr) => own(tr.team))
    .map((tr) => ({ ...(tr as unknown as Row), key: `t:${tr.track_no}`, label: t("track", { n: tr.track_no }) }))
    .sort((x, y) => y.distance_m - x.distance_m);
  const long = loose.filter((r) => r.duration_s >= 60);
  const short = loose.length - long.length;
  const rows = [...players, ...(showShort ? loose : long)];
  const teamRows = [
    ownTeam && { ...ownTeam, key: "team:own", label: t("teamOwn") },
    oppTeam && { ...oppTeam, key: "team:opp", label: t("teamOpp") },
  ].filter(Boolean) as Row[];
  const all = [...teamRows, ...rows];
  const selected = all.find((r) => r.key === sel) ?? teamRows[0] ?? rows[0];
  const line = (r: Row, strong = false) => (
    <tr key={r.key} className={cn("border-t border-foreground/10", selected?.key === r.key && "bg-accent/10")}>
      <th scope="row" className={cn("px-3 py-1.5 text-left", strong ? "font-semibold" : "font-medium")}>
        <button className="underline decoration-dotted underline-offset-4" onClick={() => setSel(r.key)} aria-label={`${t("showHeatmap")}: ${r.label}`}>
          {r.label}
        </button>
      </th>
      <td className="px-2 py-1.5 text-right tabular-nums">{t("km", { value: km(r.distance_m) })}</td>
      <td className="px-2 py-1.5 text-right tabular-nums">{t("m", { value: Math.round((r.band_distance_m.run ?? 0) + (r.band_distance_m.sprint ?? 0)) })}</td>
      <td className="px-2 py-1.5 text-right tabular-nums">{r.sprints}</td>
      <td className="px-2 py-1.5 text-right tabular-nums">{t("kmh", { value: (r.max_speed_ms * 3.6).toFixed(1) })}</td>
      <td className="px-2 py-1.5 text-right tabular-nums">{t("min", { value: Math.round(r.duration_s / 60) })}</td>
    </tr>
  );
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        <span className="mr-2 rounded-md bg-surface px-2 py-0.5 text-xs">{ta("heuristic")}</span>
        {t("hint")}
      </p>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] lg:gap-x-10">
        <div className="space-y-2">
          <div className="sheet overflow-x-auto">
            <table className="w-full text-sm" data-testid="physical-table">
              <caption className="sr-only">{t("title")}</caption>
              <thead>
                <tr>
                  <th scope="col" className="text-left" />
                  <th scope="col">{t("distance")}</th>
                  <th scope="col">{t("highIntensity")}</th>
                  <th scope="col">{t("sprints")}</th>
                  <th scope="col">{t("topSpeed")}</th>
                  <th scope="col">{t("time")}</th>
                </tr>
              </thead>
              <tbody>
                {teamRows.map((r) => line(r, true))}
                {rows.length > 0 && (
                  <tr>
                    <th scope="colgroup" colSpan={6} className="pt-4 text-left text-xs font-semibold text-muted">
                      {players.length > 0 ? t("playersAndTracks") : t("tracksOwn")}
                    </th>
                  </tr>
                )}
                {rows.map((r) => line(r))}
              </tbody>
            </table>
          </div>
          {short > 0 && (
            <button type="button" className="text-sm font-medium text-accent hover:underline" onClick={() => setShowShort((v) => !v)}>
              {showShort ? t("hideShort") : t("showShort", { n: short })}
            </button>
          )}
        </div>
        {selected && (
          <section className="space-y-2 border-t-2 border-foreground pt-4">
            <h3 className="text-lg">
              {t("heatmap")}: {selected.label}
            </h3>
            <CourtHeatmap grid={selected.heatmap} label={`${t("heatmap")} ${selected.label}`} />
          </section>
        )}
      </div>
    </div>
  );
}
