"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { CourtHeatmap } from "@/components/analysis/court-full";
import { GoalGrid } from "@/components/analysis/goal-grid";
import { Card, EmptyState } from "@/components/ui/card";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";
import type { KeeperRow, ViewProps } from "./analysis-views";
import { useOpponentName } from "@/lib/opponent";

const pct = (v: number | null | undefined) => (v == null ? "-" : `${Math.round(v * 100)} %`);

/** Goalkeeper module (M5): save rate overall, per goal zone and shot zone, 7 m, GSAx. */
export function KeepersView({ match, teamName, stats, names }: ViewProps) {
  const t = useTranslations("keepers");
  const oppName = useOpponentName();
  const sheet = ((match.report_extra as { names?: Record<string, string> } | null)?.names ?? {}) as Record<string, string>;
  const rows = Object.values(stats.goalkeepers ?? {}).sort((a, b) => (a.side === b.side ? b.faced - a.faced : a.side === "own" ? -1 : 1));
  if (rows.length === 0) return <EmptyState title={t("none")}>{t("assignHint")}</EmptyState>;
  const nameOf = (k: KeeperRow) =>
    (k.player_id && names[k.player_id]) ||
    (k.number != null && k.side === "own" && sheet[String(k.number)]) ||
    (k.number != null ? t("number", { number: k.number }) : t("unknown"));
  return (
    <div className="space-y-4">
      {(["own", "opponent"] as const).map((side) => {
        const list = rows.filter((k) => k.side === side);
        if (list.length === 0) return null;
        return (
          <section key={side} className="space-y-3" aria-label={side === "own" ? t("own") : t("opponent")}>
            <h2 className="font-semibold">
              {side === "own" ? t("own") : t("opponent")} <span className="text-sm font-normal text-muted">({side === "own" ? teamName : oppName(match)})</span>
            </h2>
            <div className="grid gap-4 lg:grid-cols-2">
              {list.map((k) => (
                <Card key={`${k.side}-${k.player_id ?? k.number ?? "u"}`} className="space-y-3" data-testid="keeper-card">
                  <h3 className="font-semibold">{nameOf(k)}</h3>
                  <dl className="grid grid-cols-3 gap-2 text-sm sm:grid-cols-6">
                    <Stat label={t("faced")} value={k.faced} />
                    <Stat label={t("saves")} value={k.saves} />
                    <Stat label={t("savePct")} value={pct(k.save_pct)} />
                    <Stat label={t("sevenM")} value={`${k.seven_m.saves}/${k.seven_m.faced}`} />
                    <Stat label={t("xgAgainst")} value={k.xg_against.toFixed(1)} />
                    <Stat
                      label={t("gsax")}
                      value={`${k.gsax > 0 ? "+" : ""}${k.gsax.toFixed(1)}`}
                      title={t("gsaxHint")}
                      tone={k.gsax > 0.5 ? "ok" : k.gsax < -0.5 ? "error" : undefined}
                    />
                  </dl>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-muted">{t("byGoalZone")}</p>
                      <GoalGrid saves data={Object.fromEntries(Object.entries(k.goal_zones).map(([z, v]) => [z, { shots: v.faced, goals: v.saves }]))} />
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-muted">{t("byShotZone")}</p>
                      <ul className="space-y-1 text-sm">
                        {Object.entries(k.shot_zones)
                          .sort((a, b) => b[1].faced - a[1].faced)
                          .map(([z, v]) => (
                            <li key={z} className="flex items-center gap-2">
                              <span className="w-28 truncate">{z}</span>
                              <span className="h-2 flex-1 overflow-hidden rounded bg-surface">
                                <span className="block h-full bg-ok" style={{ width: `${v.faced ? (v.saves / v.faced) * 100 : 0}%` }} />
                              </span>
                              <span className="w-14 text-right tabular-nums">
                                {v.saves}/{v.faced}
                              </span>
                            </li>
                          ))}
                      </ul>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </section>
        );
      })}
      <p className="text-xs text-muted">{t("gsaxHint")}</p>
    </div>
  );
}

function Stat({ label, value, title, tone }: { label: string; value: string | number; title?: string; tone?: "ok" | "error" }) {
  return (
    <div title={title} className="rounded bg-surface px-2 py-1.5">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className={cn("text-lg font-semibold tabular-nums", tone === "ok" && "text-ok", tone === "error" && "text-error")}>{value}</dd>
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
  const data = q.data;
  if (!data || (data.players.length === 0 && data.tracks.length === 0)) return <EmptyState title={q.isLoading ? "…" : t("none")}>{t("hint")}</EmptyState>;
  const rows = [
    ...data.players.map((p) => ({ key: `p:${p.player_id}`, label: names[p.player_id] ?? (p.number != null ? `#${p.number}` : "?"), ...p })),
    ...data.tracks
      .filter((tr) => tr.team === "home" || tr.team === "home_gk")
      .map((tr) => ({ key: `t:${tr.track_no}`, label: t("track", { n: tr.track_no }), ...tr })),
  ];
  const selected = rows.find((r) => r.key === sel) ?? rows[0];
  const km = (m: number) => (m / 1000).toFixed(2);
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        <span className="mr-2 rounded-full bg-surface px-2 py-0.5 text-xs">{ta("heuristic")}</span>
        {t("hint")}
      </p>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-sm" data-testid="physical-table">
            <caption className="sr-only">{t("title")}</caption>
            <thead className="bg-surface text-muted">
              <tr>
                <th scope="col" className="px-3 py-2 text-left font-medium" />
                <th scope="col" className="px-2 py-2 text-right font-medium">{t("distance")}</th>
                <th scope="col" className="px-2 py-2 text-right font-medium">{t("highIntensity")}</th>
                <th scope="col" className="px-2 py-2 text-right font-medium">{t("sprints")}</th>
                <th scope="col" className="px-2 py-2 text-right font-medium">{t("topSpeed")}</th>
                <th scope="col" className="px-2 py-2 text-right font-medium">{t("time")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key} className={cn("border-t border-border", selected?.key === r.key && "bg-accent/10")}>
                  <th scope="row" className="px-3 py-1.5 text-left font-medium">
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
              ))}
            </tbody>
          </table>
        </div>
        {selected && (
          <Card className="space-y-2">
            <h3 className="font-semibold">
              {t("heatmap")}: {selected.label}
            </h3>
            <CourtHeatmap grid={selected.heatmap} label={`${t("heatmap")} ${selected.label}`} />
          </Card>
        )}
      </div>
    </div>
  );
}
