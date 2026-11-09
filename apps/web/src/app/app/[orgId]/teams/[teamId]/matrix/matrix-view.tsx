"use client";

import { Play, X } from "lucide-react";
import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card, EmptyState } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

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

export function MatrixView({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("matrix");
  const tr = useTranslations();
  const qc = useQueryClient();
  const team = { org_id: orgId, team_id: teamId };
  const [spec, setSpec] = useState<Spec>({ rows: "number", metrics: ["goals", "shooting_pct"], filter: { side: "own" } });
  const [open, setOpen] = useState<{ label: string; metric: string; cell: Cell } | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<ErrorKey | null>(null);
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
  const select = "min-h-9 rounded-md border border-border bg-background px-2 text-sm";
  const data = result.data;

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold">{t("title")}</h2>
        <p className="text-sm text-muted">{t("hint")}</p>
      </div>
      <Card className="space-y-4">
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
              <option value="own">{t("own")}</option>
              <option value="opponent">{t("opponent")}</option>
            </select>
          </label>
          <label className="text-sm">
            <span className="block font-medium">{t("lastN")}</span>
            <input
              type="number"
              min={1}
              max={100}
              className={`${select} w-24`}
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
                className="rounded-md border border-border px-3 py-1 text-sm aria-pressed:border-accent aria-pressed:bg-accent aria-pressed:text-accent-contrast"
              >
                {t(`m_${m}`)}
              </button>
            ))}
          </div>
        </fieldset>
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" onClick={() => void download("csv")}>{t("csv")}</Button>
          <Button type="button" onClick={() => void download("xlsx")}>{t("xlsx")}</Button>
          <span className="mx-2 h-6 w-px bg-border" aria-hidden />
          <input className={select} placeholder={t("templateName")} aria-label={t("templateName")} value={name} onChange={(e) => setName(e.target.value)} maxLength={120} />
          <Button type="button" disabled={!name.trim() || save.isPending} onClick={() => save.mutate()}>
            {t("save")}
          </Button>
        </div>
        {(templates.data ?? []).length > 0 && (
          <ul className="flex flex-wrap gap-2 text-sm" aria-label={t("templates")}>
            {(templates.data ?? []).map((tp) => (
              <li key={tp.id} className="flex items-center gap-1 rounded-full border border-border pl-3">
                <button type="button" className="hover:underline" onClick={() => setSpec(tp.config)}>
                  {tp.name}
                </button>
                <button type="button" aria-label={t("deleteTemplate", { name: tp.name })} className="px-2 text-muted" onClick={() => remove.mutate(tp.id)}>
                  <X aria-hidden className="size-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
        {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      </Card>

      {!data || data.rows.length === 0 ? (
        <EmptyState title={result.isLoading ? "…" : t("empty")} />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="matrix">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="py-2 pr-4">{t(`dim_${data.by}`)}</th>
                {data.metrics.map((m) => (
                  <th key={m} className="py-2 pr-4" title={data.definitions[m]}>{t(`m_${m}`)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...data.rows, { ...data.totals, label: t("total") }].map((row) => (
                <tr key={row.key} className="border-b border-border">
                  <th scope="row" className="py-2 pr-4 text-left font-normal">{row.label}</th>
                  {data.metrics.map((m) => {
                    const c = row.cells[m];
                    return (
                      <td key={m} className="py-1 pr-4 tabular-nums">
                        {c && c.events > 0 ? (
                          <button type="button" className="hover:underline" onClick={() => setOpen({ label: row.label, metric: m, cell: c })}>
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
      )}

      {open && (
        <Card className="space-y-2" aria-live="polite">
          <h3 className="font-semibold">{t("cellClips", { row: open.label, metric: t(`m_${open.metric}`) })}</h3>
          {open.cell.clips.length === 0 ? (
            <p className="text-sm text-muted">{t("noVideo", { n: open.cell.events })}</p>
          ) : (
            <ul className="flex flex-wrap gap-2">
              {open.cell.clips.map((c, i) => (
                <li key={c.event_id}>
                  <Link className="inline-flex min-h-8 items-center gap-1.5 rounded-md bg-accent/10 px-3 text-sm font-medium text-accent hover:bg-accent/20" href={`/app/${orgId}/matches/${c.match_id}?t=${c.t_ms ?? 0}`}>
                    <Play aria-hidden className="size-3 fill-current" /> {i + 1}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
    </div>
  );
}
