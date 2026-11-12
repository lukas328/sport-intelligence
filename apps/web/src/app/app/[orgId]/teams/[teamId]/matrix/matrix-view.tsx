"use client";

import { ChevronDown, Play, X } from "lucide-react";
import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert, EmptyState } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { cn } from "@/lib/utils";

type Spec = Schemas["MatrixIn"];
type Cell = Schemas["MatrixCell"];

export const DIMENSIONS = ["number", "position", "play", "match", "opponent", "period", "minute_10", "zone", "shot_type"] as const;
export const METRICS = [
  "goals",
  "shots",
  "shooting_pct",
  "on_target_pct",
  "saves",
  "save_pct",
  "xg",
  "turnovers",
  "steals",
  "suspensions",
  "seven_m_goals",
  "seven_m_pct",
  "fast_break_goals",
] as const;
const RATIOS = new Set(["shooting_pct", "on_target_pct", "save_pct", "seven_m_pct"]);

export function formatCell(metric: string, c: Cell | undefined): string {
  if (!c || c.value == null) return "-";
  if (RATIOS.has(metric)) return `${Math.round(c.value * 100)} % (${c.numerator}/${c.denominator})`;
  return String(c.value);
}

export function MatrixView({ orgId, teamId, teamName, seasonId }: { orgId: string; teamId: string; teamName: string; seasonId: string | null }) {
  const t = useTranslations("matrix");
  const tr = useTranslations();
  const qc = useQueryClient();
  const team = { org_id: orgId, team_id: teamId };
  const [spec, setSpec] = useState<Spec>({ rows: "number", metrics: ["goals", "shooting_pct"], filter: { side: "own" } });
  const [open, setOpen] = useState<{ label: string; metric: string; cell: Cell } | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<ErrorKey | null>(null);
  // on phones the settings fold away behind one line, so the table is on the first screen
  const [settings, setSettings] = useState(false);
  // shirt numbers of the own team read as names
  const roster = useQuery({
    queryKey: ["roster", seasonId],
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster", { params: { path: { ...team, season_id: seasonId! } } })).data ?? [],
    enabled: !!seasonId,
  });
  // which seasons the matrix reads: by default the current and the previous one (the API's default)
  const seasons = useQuery({
    queryKey: ["seasons", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons", { params: { path: team } })).data ?? [],
  });
  const seasonChoice = spec.season_ids == null ? "" : spec.season_ids.length === 1 ? spec.season_ids[0]! : "all";
  const setSeasons = (v: string) =>
    setSpec((s) => ({ ...s, season_ids: v === "" ? null : v === "all" ? (seasons.data ?? []).map((x) => x.id).slice(0, 20) : [v] }));
  const filter = (spec.filter ?? {}) as Record<string, string | number | undefined>;
  const setFilter = (k: string, v: string | number | undefined) =>
    setSpec((s) => {
      const f = { ...(s.filter ?? {}) } as Record<string, unknown>;
      if (v === undefined || v === "") delete f[k];
      else f[k] = v;
      return { ...s, filter: f };
    });

  const result = useQuery({
    queryKey: ["matrix", teamId, spec],
    queryFn: async () => {
      const r = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/matrix", { params: { path: team }, body: spec });
      if (r.error) throw r.error;
      return r.data;
    },
    enabled: spec.metrics.length > 0,
  });
  const templates = useQuery({
    queryKey: ["matrix-templates", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/matrix/templates", { params: { path: team } })).data ?? [],
  });
  const save = useMutation({
    mutationFn: async () => {
      const r = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/matrix/templates", { params: { path: team }, body: { name, config: spec } });
      if (r.error) throw r.error;
    },
    onSuccess: () => {
      setName("");
      void qc.invalidateQueries({ queryKey: ["matrix-templates", teamId] });
    },
    onError: (e) => setError(errorKey(e)),
  });
  const remove = useMutation({
    mutationFn: async (id: string) => api.DELETE("/v1/orgs/{org_id}/matrix/templates/{template_id}", { params: { path: { org_id: orgId, template_id: id } } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["matrix-templates", teamId] }),
  });
  const download = async (format: "csv" | "xlsx") => {
    const r = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/matrix/export", {
      params: { path: team, query: { format } },
      body: spec,
      parseAs: "blob",
    });
    if (!r.data) return;
    const url = URL.createObjectURL(r.data as unknown as Blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `matrix-${spec.rows}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };
  const toggleMetric = (m: string) =>
    setSpec((s) => ({
      ...s,
      metrics: s.metrics.includes(m) ? s.metrics.filter((x) => x !== m) : s.metrics.length < 8 ? [...s.metrics, m] : s.metrics,
    }));
  const data = result.data;
  const rowLabel = (label: string) => {
    if (!data || data.by !== "number" || filter.side !== "own") return label;
    const n = Number(label.replace("#", ""));
    const p = (roster.data ?? []).find((r) => r.jersey_number === n);
    return p ? `${n} ${p.first_name} ${p.last_name}` : label.replace("#", t("shirtPrefix"));
  };
  const select = "min-h-9 border border-border bg-background px-2 text-sm";

  const seasonLabel = seasonChoice === "" ? null : seasonChoice === "all" ? t("seasonsAll") : seasons.data?.find((x) => x.id === seasonChoice)?.label;
  const summary = [
    t(`dim_${spec.rows}`),
    filter.side === "own" ? teamName || t("own") : filter.side === "opponent" ? t("opponent") : t("both"),
    seasonLabel,
    t("metricsN", { n: spec.metrics.length }),
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <div className="space-y-5">
      <p className="text-sm text-muted">{t("hint")}</p>
      <button
        type="button"
        aria-expanded={settings}
        onClick={() => setSettings((v) => !v)}
        className="flex min-h-11 w-full items-center justify-between gap-3 border-y border-foreground/15 text-left text-sm sm:hidden"
      >
        <span>
          <span className="font-semibold">{t("settings")}</span> <span className="text-muted">{summary}</span>
        </span>
        <ChevronDown aria-hidden className={cn("size-4 shrink-0 transition-transform", settings && "rotate-180")} />
      </button>
      <section className={cn("space-y-4 border-b border-foreground/15 pb-5", !settings && "hidden sm:block")} aria-label={t("settings")}>
        <div className="flex flex-wrap items-end gap-4">
          <label className="text-sm">
            <span className="block font-medium">{t("rows")}</span>
            <select className={select} value={spec.rows} onChange={(e) => setSpec((s) => ({ ...s, rows: e.target.value }))}>
              {DIMENSIONS.map((d) => (
                <option key={d} value={d}>{t(`dim_${d}`)}</option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="block font-medium">{t("side")}</span>
            <select className={select} value={String(filter.side ?? "")} onChange={(e) => setFilter("side", e.target.value)}>
              <option value="">{t("both")}</option>
              <option value="own">{teamName || t("own")}</option>
              <option value="opponent">{t("opponent")}</option>
            </select>
          </label>
          {(seasons.data?.length ?? 0) > 1 && (
            <label className="text-sm">
              <span className="block font-medium">{t("seasons")}</span>
              <select className={select} value={seasonChoice} onChange={(e) => setSeasons(e.target.value)} data-testid="matrix-seasons">
                <option value="">{t("seasonsRecent")}</option>
                {(seasons.data ?? []).map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.label}
                  </option>
                ))}
                <option value="all">{t("seasonsAll")}</option>
              </select>
            </label>
          )}
          <label className="text-sm">
            <span className="block font-medium">{t("lastN")}</span>
            <input
              type="number"
              min={1}
              max={100}
              className={`${select} w-24`}
              placeholder={t("allMatches")}
              value={filter.last_n_matches ?? ""}
              onChange={(e) => setFilter("last_n_matches", e.target.value ? Number(e.target.value) : undefined)}
            />
          </label>
          <label className="text-sm">
            <span className="block font-medium">{t("period")}</span>
            <select className={select} value={String(filter.period ?? "")} onChange={(e) => setFilter("period", e.target.value ? Number(e.target.value) : undefined)}>
              <option value="">{t("both")}</option>
              <option value="1">1</option>
              <option value="2">2</option>
            </select>
          </label>
        </div>
        <fieldset>
          <legend className="text-sm font-medium">{t("columns")}</legend>
          <div className="mt-1 flex flex-wrap gap-2">
            {METRICS.map((m) => (
              <button
                key={m}
                type="button"
                aria-pressed={spec.metrics.includes(m)}
                onClick={() => toggleMetric(m)}
                className="min-h-8 border border-border px-3 py-1 text-sm aria-pressed:border-foreground aria-pressed:bg-foreground aria-pressed:text-background"
              >
                {t(`m_${m}`)}
              </button>
            ))}
          </div>
        </fieldset>
        <div className="flex flex-wrap items-center gap-2">
          <input className={select} placeholder={t("templateName")} aria-label={t("templateName")} value={name} onChange={(e) => setName(e.target.value)} maxLength={120} />
          <Button type="button" variant="secondary" disabled={!name.trim() || save.isPending} onClick={() => save.mutate()}>
            {t("save")}
          </Button>
        </div>
        {(templates.data ?? []).length > 0 && (
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm" aria-label={t("templates")}>
            {(templates.data ?? []).map((tp) => (
              <li key={tp.id} className="flex items-center gap-1">
                <button type="button" className="min-h-8 font-medium underline underline-offset-4" onClick={() => setSpec(tp.config)}>
                  {tp.name}
                </button>
                <button type="button" aria-label={t("deleteTemplate", { name: tp.name })} className="grid size-8 place-items-center text-muted hover:text-foreground" onClick={() => remove.mutate(tp.id)}>
                  <X aria-hidden className="size-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
        {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      </section>

      {!data || data.rows.length === 0 ? (
        <EmptyState title={result.isLoading ? "…" : t("empty")} />
      ) : (
        <div className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted">{t("export")}</span>
          <Button type="button" variant="ghost" size="sm" onClick={() => void download("csv")}>{t("csv")}</Button>
          <Button type="button" variant="ghost" size="sm" onClick={() => void download("xlsx")}>{t("xlsx")}</Button>
        </div>
        <div className="overflow-x-auto">
          <table className="sheet w-full text-sm" data-testid="matrix">
            <thead>
              <tr className="border-b border-foreground/15 text-left">
                <th className="py-2 pr-4">{t(`dim_${data.by}`)}</th>
                {data.metrics.map((m) => (
                  <th key={m} className="py-2 pr-4" title={data.definitions[m]}>{t(`m_${m}`)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...data.rows, { ...data.totals, label: t("total") }].map((row) => (
                <tr key={row.key} className={cn("border-b border-foreground/10", row.key === "total" && "border-t-2 border-t-foreground/40 font-semibold")}>
                  <th scope="row" className={cn("py-2 pr-4 text-left", row.key === "total" ? "font-semibold" : "font-normal")}>{row.key === "total" ? row.label : rowLabel(row.label)}</th>
                  {data.metrics.map((m) => {
                    const c = row.cells[m];
                    return (
                      <td key={m} className="py-1 pr-4 tabular-nums">
                        {c && c.events > 0 ? (
                          <button
                            type="button"
                            aria-pressed={open?.label === row.label && open.metric === m}
                            className="min-h-8 underline decoration-dotted decoration-foreground/50 underline-offset-4 hover:decoration-solid aria-pressed:font-semibold aria-pressed:decoration-solid"
                            onClick={() => setOpen({ label: row.key === "total" ? row.label : rowLabel(row.label), metric: m, cell: c })}
                          >
                            {formatCell(m, c)}
                          </button>
                        ) : (
                          formatCell(m, c)
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </div>
      )}

      {open && (
        <section className="space-y-2 border-t-2 border-foreground pt-3" aria-live="polite">
          <h3 className="font-semibold">{t("cellClips", { row: open.label, metric: t(`m_${open.metric}`) })}</h3>
          {open.cell.clips.length === 0 ? (
            <p className="text-sm text-muted">{t("noVideo", { n: open.cell.events })}</p>
          ) : (
            <ul className="flex flex-wrap gap-2">
              {open.cell.clips.map((c, i) => (
                <li key={c.event_id}>
                  <Link className="inline-flex min-h-9 items-center gap-1.5 px-3 text-sm font-semibold ring-1 ring-inset ring-foreground/20 hover:bg-surface" href={`/app/${orgId}/matches/${c.match_id}?t=${c.t_ms ?? 0}`}>
                    <Play aria-hidden className="size-3 fill-current" /> {i + 1}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
