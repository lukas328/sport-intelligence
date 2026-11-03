"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
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
      <h1 className="text-2xl font-bold sm:text-[1.75rem]">{t("title")}</h1>
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
            <div key={String(label)} className="rounded-2xl bg-raised px-4 py-4 ring-1 ring-border/70 sm:px-5">
              <dt className="text-[0.8125rem] text-muted">{label}</dt>
              <dd className="mt-1 font-score text-[1.75rem] leading-none sm:text-3xl">{value}</dd>
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
          <ul className="divide-y divide-border/70 text-sm" data-testid="ops-failed">
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
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} className="min-h-10 w-72 rounded-xl bg-raised ring-1 ring-inset ring-border px-3" />
        </label>
        <div className="overflow-x-auto rounded-2xl bg-raised ring-1 ring-border/70">
          <table className="w-full text-sm" data-testid="ops-orgs">
            <caption className="sr-only">{t("organizations")}</caption>
            <thead className="text-xs text-muted">
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
                <tr key={org.id} className="border-t border-border/70">
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
      <OpsBilling />
    </div>
  );
}


/** Invoices (mark paid, camt.054 matching) and vouchers (addendum 01, 4.10). */
function OpsBilling() {
  const t = useTranslations("ops");
  const qc = useQueryClient();
  const [camt, setCamt] = useState<string | null>(null);
  const invoices = useQuery({
    queryKey: ["ops-invoices"],
    queryFn: async () => (await api.GET("/v1/ops/invoices")).data ?? [],
  });
  const vouchers = useQuery({
    queryKey: ["ops-vouchers"],
    queryFn: async () => (await api.GET("/v1/ops/vouchers")).data ?? [],
  });
  const paid = useMutation({
    mutationFn: async (id: string) => api.POST("/v1/ops/invoices/{invoice_id}/paid", { params: { path: { invoice_id: id } }, body: { note: "manuell" } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["ops-invoices"] }),
  });
  const voucher = useMutation({
    mutationFn: async (body: { code: string; percent_off: number; note: string | null }) => api.POST("/v1/ops/vouchers", { body }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["ops-vouchers"] }),
  });
  async function upload(file: File) {
    const body = new FormData();
    body.append("file", file);
    const res = await fetch("/v1/ops/invoices/camt054", {
      method: "POST",
      body,
      credentials: "same-origin",
      headers: { "x-csrf-token": document.cookie.match(/hb_csrf=([^;]+)/)?.[1] ?? "" },
    });
    const data = (await res.json()) as { matched?: unknown[]; unmatched?: unknown[] };
    setCamt(t("camtResult", { matched: data.matched?.length ?? 0, unmatched: data.unmatched?.length ?? 0 }));
    void qc.invalidateQueries({ queryKey: ["ops-invoices"] });
  }
  return (
    <section className="space-y-3" aria-labelledby="ops-billing">
      <h2 id="ops-billing" className="text-lg font-semibold">
        {t("invoices")}
      </h2>
      <label className="block text-sm">
        {t("camt")}
        <input type="file" accept=".xml" className="ml-2" onChange={(e) => e.target.files?.[0] && void upload(e.target.files[0])} />
      </label>
      {camt && <p role="status" className="text-sm">{camt}</p>}
      <table className="w-full text-sm" data-testid="ops-invoices">
        <thead>
          <tr className="text-left text-muted">
            <th scope="col">{t("invoiceNo")}</th>
            <th scope="col">{t("club")}</th>
            <th scope="col" className="text-right">{t("amount")}</th>
            <th scope="col">{t("due")}</th>
            <th scope="col">{t("state")}</th>
          </tr>
        </thead>
        <tbody>
          {(invoices.data ?? []).map((i) => (
            <tr key={String(i.id)} className="border-t border-border/70">
              <td>{String(i.number)}</td>
              <td>{String(i.organization)}</td>
              <td className="text-right tabular-nums">{(Number(i.amount_cents) / 100).toFixed(2)}</td>
              <td>{String(i.due_date)}</td>
              <td>
                {i.paid_at ? (
                  t("paid")
                ) : (
                  <Button variant="ghost" className="min-h-8 px-2 text-xs" onClick={() => paid.mutate(String(i.id))}>
                    {t("markPaid")}
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <form
        className="flex flex-wrap items-end gap-2"
        aria-label={t("newVoucher")}
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          voucher.mutate({ code: String(f.get("code")), percent_off: Number(f.get("percent")), note: String(f.get("note") ?? "") || null });
          e.currentTarget.reset();
        }}
      >
        <Input label={t("voucherCode")} name="code" required pattern="[A-Za-z0-9-]+" />
        <Input label={t("percentOff")} name="percent" type="number" min={1} max={100} required />
        <Input label={t("note")} name="note" />
        <Button type="submit" variant="secondary">
          {t("newVoucher")}
        </Button>
      </form>
      <ul className="text-sm">
        {(vouchers.data ?? []).map((v) => (
          <li key={String(v.code)}>
            {String(v.code)} · {String(v.percent_off)} % · {t("uses", { n: Number(v.uses) })}
            {v.note ? ` · ${String(v.note)}` : ""}
          </li>
        ))}
      </ul>
    </section>
  );
}
