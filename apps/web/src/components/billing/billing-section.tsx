"use client";

import { problemCode } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";
import { InvoiceOrder } from "./invoice-order";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";

interface PlanRow {
  plan: "free" | "team" | "club";
  price_chf_month: number;
  teams: number;
  matches_per_season: number | null;
  storage_gb: number;
  gpu_minutes_month: number;
  features: string[];
  trial_days: number;
}
interface Billing {
  plan: string;
  effective_plan: string;
  status: string | null;
  trial_ends_at: string | null;
  current_period_end: string | null;
  goalkeeper_seats: number;
  enforced: boolean;
  checkout_available: boolean;
  limits: { teams: number; matches_per_season: number | null; storage_gb: number; gpu_minutes_month: number };
  usage: { teams: number; storage_bytes: number; gpu_minutes: number; max_matches_per_season: number };
  plans: PlanRow[];
  goalkeeper_addon_chf: number;
}

function Meter({ label, used, limit, unit = "" }: { label: string; used: number; limit: number | null; unit?: string }) {
  const share = limit ? Math.min(1, used / limit) : 0;
  return (
    <div className="space-y-1 text-sm">
      <div className="flex justify-between gap-2">
        <span>{label}</span>
        <span className="tabular-nums">
          {used}
          {unit} / {limit == null ? "∞" : `${limit}${unit}`}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded bg-surface" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={limit ?? 0} aria-valuenow={used}>
        <div className={cn("h-full", share >= 0.9 ? "bg-error" : "bg-accent")} style={{ width: `${share * 100}%` }} />
      </div>
    </div>
  );
}

/** Plan, usage and Stripe checkout/portal for org admins (BRIEF 13). */
export function BillingSection({ orgId }: { orgId: string }) {
  const t = useTranslations("billing");
  const format = useFormatter();
  const [problem, setProblem] = useState<string | null>(null);
  const [goalkeepers, setGoalkeepers] = useState(0);
  const q = useQuery({
    queryKey: ["billing", orgId],
    queryFn: async () => ((await api.GET("/v1/orgs/{org_id}/billing", { params: { path: { org_id: orgId } } })).data ?? null) as Billing | null,
  });
  const b = q.data;
  if (!b) return null;
  async function go(path: "/v1/orgs/{org_id}/billing/checkout" | "/v1/orgs/{org_id}/billing/portal", plan?: string) {
    const res =
      path === "/v1/orgs/{org_id}/billing/checkout"
        ? await api.POST(path, { params: { path: { org_id: orgId } }, body: { plan: plan as "team", goalkeeper_seats: goalkeepers } })
        : await api.POST(path, { params: { path: { org_id: orgId } } });
    if (res.error || !res.data) return setProblem(problemCode(res.error) ?? "generic");
    window.location.assign(res.data.url);
  }
  const gb = (bytes: number) => Math.round((bytes / 1024 ** 3) * 10) / 10;
  return (
    <section id="billing" aria-labelledby="billing-title" className="space-y-3">
      <h2 id="billing-title" className="text-lg font-semibold">
        {t("title")}
      </h2>
      <Card className="space-y-4" data-testid="billing">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p>
            <span className="font-semibold">{t(`plan_${b.plan as "free"}`)}</span>
            {b.status && <span className="ml-2 text-sm text-muted">{t(`status_${b.status as "active"}`)}</span>}
            {b.trial_ends_at && b.status === "trialing" && (
              <span className="ml-2 text-sm">{t("trialUntil", { date: format.dateTime(new Date(b.trial_ends_at), { dateStyle: "medium" }) })}</span>
            )}
          </p>
          {b.plan !== "free" && b.checkout_available && (
            <Button variant="secondary" onClick={() => void go("/v1/orgs/{org_id}/billing/portal")}>
              {t("portal")}
            </Button>
          )}
        </div>
        {!b.enforced && <p className="text-sm text-muted">{t("notEnforced")}</p>}
        <div className="grid gap-3 sm:grid-cols-2">
          <Meter label={t("teams")} used={b.usage.teams} limit={b.limits.teams} />
          <Meter label={t("matches")} used={b.usage.max_matches_per_season} limit={b.limits.matches_per_season} />
          <Meter label={t("storage")} used={gb(b.usage.storage_bytes)} limit={b.limits.storage_gb} unit=" GB" />
          <Meter label={t("gpu")} used={b.usage.gpu_minutes} limit={b.limits.gpu_minutes_month} unit=" min" />
        </div>
        <ul className="grid gap-3 md:grid-cols-3" data-testid="plans">
          {b.plans.map((p) => (
            <li key={p.plan} className={cn("space-y-2 rounded-lg border p-3", p.plan === b.plan ? "border-accent" : "border-border")}>
              <p className="font-semibold">{t(`plan_${p.plan}`)}</p>
              <p className="text-2xl font-bold tabular-nums">
                {p.price_chf_month ? t("price", { price: p.price_chf_month }) : t("free")}
              </p>
              <ul className="space-y-0.5 text-sm text-muted">
                <li>{t("teamsN", { count: p.teams })}</li>
                <li>{p.matches_per_season == null ? t("matchesUnlimited") : t("matchesN", { count: p.matches_per_season })}</li>
                <li>{t("storageN", { gb: p.storage_gb })}</li>
                <li>{p.features.includes("tracking") ? t("withAnalysis") : t("withoutAnalysis")}</li>
                {p.trial_days > 0 && <li>{t("trial", { days: p.trial_days })}</li>}
              </ul>
              {p.plan !== "free" && p.plan !== b.plan && (
                <Button className="w-full" disabled={!b.checkout_available} onClick={() => void go("/v1/orgs/{org_id}/billing/checkout", p.plan)}>
                  {t("choose", { plan: t(`plan_${p.plan}`) })}
                </Button>
              )}
            </li>
          ))}
        </ul>
        <label className="flex flex-wrap items-center gap-2 text-sm">
          {t("goalkeepers", { price: b.goalkeeper_addon_chf })}
          <input
            type="number"
            min={0}
            max={20}
            value={goalkeepers}
            onChange={(e) => setGoalkeepers(Math.max(0, Math.min(20, Number(e.target.value) || 0)))}
            className="min-h-9 w-20 rounded-md border border-border bg-background px-2"
          />
        </label>
        {!b.checkout_available && <p className="text-xs text-muted">{t("unavailable")}</p>}
        {problem && <Alert>{problem === "two-factor-required" ? t("needs2fa") : t("failed")}</Alert>}
      </Card>
      <InvoiceOrder orgId={orgId} goalkeepers={goalkeepers} />
    </section>
  );
}
