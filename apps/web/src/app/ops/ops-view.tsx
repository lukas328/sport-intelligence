"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/client";

interface Overview {
  organizations: number;
  users: number;
  teams: number;
  matches: number;
  videos: number;
  storage_bytes: number;
  gpu_minutes_24h: number;
  plans: Record<string, number>;
  jobs_24h: { kind: string; status: string; count: number }[];
  failed_jobs: { id: string; kind: string; organization: string; error: string | null; created_at: string }[];
}
interface Org {
  id: string;
  name: string;
  plan: string;
  status: string | null;
  trial_ends_at: string | null;
  teams: number;
  members: number;
  matches: number;
  storage_bytes: number;
}

const gb = (b: number) => `${(b / 1024 ** 3).toFixed(1)} GB`;

/** Platform operator backoffice (BRIEF M8): health, failed jobs, organisations, support actions. */
export function OpsView() {
  const t = useTranslations("ops");
  const format = useFormatter();
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const ov = useQuery({ queryKey: ["ops"], queryFn: async () => ((await api.GET("/v1/ops/overview")).data ?? null) as Overview | null });
  const orgs = useQuery({
    queryKey: ["ops-orgs", q],
    queryFn: async () => ((await api.GET("/v1/ops/organizations", { params: { query: { q: q || undefined } } })).data ?? []) as unknown as Org[],
  });
  const retry = useMutation({
    mutationFn: async (id: string) => api.POST("/v1/ops/jobs/{job_id}/retry", { params: { path: { job_id: id } } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["ops"] }),
  });
  const trial = useMutation({
    mutationFn: async (id: string) =>
      api.POST("/v1/ops/organizations/{org_id}/trial", { params: { path: { org_id: id } }, body: { plan: "club", days: 14 } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["ops-orgs"] }),
  });
  const o = ov.data;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      {o && (
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7" data-testid="ops-tiles">
          {[
            [t("organizations"), o.organizations],
            [t("users"), o.users],
            [t("teams"), o.teams],
            [t("matches"), o.matches],
            [t("videos"), o.videos],
            [t("storage"), gb(o.storage_bytes)],
            [t("gpu"), o.gpu_minutes_24h],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-lg border border-border p-3">
              <dt className="text-xs text-muted">{label}</dt>
              <dd className="text-xl font-semibold tabular-nums">{value}</dd>
            </div>
          ))}
        </dl>
      )}
      {o && (
        <Card className="space-y-2">
          <h2 className="font-semibold">{t("jobs")}</h2>
          <p className="text-sm text-muted">{o.jobs_24h.map((j) => `${j.kind} ${j.status}: ${j.count}`).join(" · ") || "-"}</p>
          <h3 className="pt-2 text-sm font-semibold">{t("failed")}</h3>
          {o.failed_jobs.length === 0 && <p className="text-sm text-muted">{t("noFailed")}</p>}
          <ul className="divide-y divide-border text-sm" data-testid="ops-failed">
            {o.failed_jobs.map((j) => (
              <li key={j.id} className="flex flex-wrap items-center gap-2 py-2">
                <span className="font-medium">{j.organization}</span>
                <span className="text-muted">
                  {j.kind} · {format.dateTime(new Date(j.created_at), { dateStyle: "short", timeStyle: "short" })}
                </span>
                <span className="min-w-0 flex-1 truncate font-mono text-xs">{j.error}</span>
                <Button variant="secondary" className="min-h-8 px-2 text-xs" onClick={() => retry.mutate(j.id)}>
                  {t("retry")}
                </Button>
              </li>
            ))}
          </ul>
        </Card>
      )}
      <section className="space-y-2" aria-label={t("organizations")}>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">{t("search")}</span>
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} className="min-h-10 w-72 rounded-md border border-border bg-background px-3" />
        </label>
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-sm" data-testid="ops-orgs">
            <caption className="sr-only">{t("organizations")}</caption>
            <thead className="bg-surface text-muted">
              <tr>
                {[t("name"), t("plan"), t("teams"), t("members"), t("matches"), t("storage"), ""].map((h, i) => (
                  <th key={i} scope="col" className="px-3 py-2 text-left font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(orgs.data ?? []).map((org) => (
                <tr key={org.id} className="border-t border-border">
                  <th scope="row" className="px-3 py-1.5 text-left font-medium">{org.name}</th>
                  <td className="px-3 py-1.5">
                    {org.plan}
                    {org.status && ` (${org.status})`}
                    {org.trial_ends_at && ` · ${t("trialUntil", { date: format.dateTime(new Date(org.trial_ends_at), { dateStyle: "short" }) })}`}
                  </td>
                  <td className="px-3 py-1.5 tabular-nums">{org.teams}</td>
                  <td className="px-3 py-1.5 tabular-nums">{org.members}</td>
                  <td className="px-3 py-1.5 tabular-nums">{org.matches}</td>
                  <td className="px-3 py-1.5 tabular-nums">{gb(org.storage_bytes)}</td>
                  <td className="px-3 py-1.5">
                    <Button variant="ghost" className="min-h-8 px-2 text-xs" onClick={() => trial.mutate(org.id)}>
                      {t("trial")}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
