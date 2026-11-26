"use client";

import { problemCode } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { InvoiceOrder } from "./invoice-order";
import { Button } from "@/components/ui/button";
import { Alert, Skeleton } from "@/components/ui/card";
import { Term } from "@/components/ui/term";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";

interface PlanRow {
  plan: "free" | "team" | "club";
  /** the same number in CHF and EUR; the club pays in `Billing.currency` */
  price_month: number;
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
  enforced: boolean;
  checkout_available: boolean;
  /** why not: no Stripe at all, or no price in the club's currency (EUR open, Q-BILL-EU5) */
  checkout_unavailable?: "not_configured" | "currency" | null;
  currency?: "CHF" | "EUR";
  limits: { teams: number; matches_per_season: number | null; storage_gb: number; gpu_minutes_month: number };
  usage: { teams: number; storage_bytes: number; gpu_minutes: number; max_matches_per_season: number };
  plans: PlanRow[];
}

/** Usage against the plan; red only when a limit is enforced and reached (limits off: ink). */
function Meter({ label, shown, used, limit, unit = "", enforced }: { label: string; /** the label as shown, e.g. with an explained word (A17) */ shown?: ReactNode; used: number; limit: number | null; unit?: string; enforced: boolean }) {
  const share = limit ? Math.min(1, used / limit) : 0;
  // limits off: the usage as text, no bar that reads full or over
  if (!enforced)
    return (
      <div className="flex justify-between gap-2 border-b border-foreground/10 py-1.5 text-sm">
        <span>{shown ?? label}</span>
        <span className="tabular-nums">
          {used}
          {unit}
        </span>
      </div>
    );
  return (
    <div className="space-y-1 text-sm">
      <div className="flex justify-between gap-2">
        <span>{shown ?? label}</span>
        <span className="tabular-nums">
          {used}
          {unit} / {limit == null ? "∞" : `${limit}${unit}`}
        </span>
      </div>
      <div className="h-2 overflow-hidden bg-surface" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={limit ?? 0} aria-valuenow={used}>
        <div className={cn("h-full", share >= 1 ? "bg-error" : "bg-foreground/70")} style={{ width: `${share * 100}%` }} />
      </div>
    </div>
  );
}

/** Plan, usage and Stripe checkout/portal for org admins (BRIEF 13). */
export function BillingSection({ orgId }: { orgId: string }) {
  const t = useTranslations("billing");
  const tc = useTranslations("common");
  const te = useTranslations("errors");
  const tg = useTranslations("glossary");
  const format = useFormatter();
  const [problem, setProblem] = useState<string | null>(null);
  const q = useQuery({
    queryKey: ["billing", orgId],
    queryFn: async () => ((await api.GET("/v1/orgs/{org_id}/billing", { params: { path: { org_id: orgId } } })).data ?? null) as Billing | null,
  });
  const b = q.data;
  // while the plan loads: the shape of the section, not a blank second (finding A15)
  if (!b)
    return (
      <section id="billing" aria-labelledby="billing-title" aria-busy={q.isPending || undefined} className="space-y-3" data-testid="billing-loading">
        <h2 id="billing-title" className="text-lg font-semibold">
          {t("title")}
        </h2>
        {q.isPending ? (
          <div className="space-y-4 border-t border-foreground/15 pt-5">
            <p role="status" className="sr-only">
              {tc("loading")}
            </p>
            <Skeleton className="h-6 w-56 max-w-full" />
            <div className="grid gap-3 sm:grid-cols-2">
              <Skeleton className="h-8" />
              <Skeleton className="h-8" />
              <Skeleton className="h-8" />
              <Skeleton className="h-8" />
            </div>
            <Skeleton className="h-36" />
          </div>
        ) : (
          <Alert kind="error">
            {te("generic")}{" "}
            <button type="button" onClick={() => void q.refetch()} className="cursor-pointer font-bold underline underline-offset-4">
              {tc("retry")}
            </button>
          </Alert>
        )}
      </section>
    );
  async function go(path: "/v1/orgs/{org_id}/billing/checkout" | "/v1/orgs/{org_id}/billing/portal", plan?: string) {
    const res =
      path === "/v1/orgs/{org_id}/billing/checkout"
        ? await api.POST(path, { params: { path: { org_id: orgId } }, body: { plan: plan as "team" } })
        : await api.POST(path, { params: { path: { org_id: orgId } } });
    if (res.error || !res.data) return setProblem(problemCode(res.error) ?? "generic");
    window.location.assign(res.data.url);
  }
  const trialOn = Boolean(b.trial_ends_at && new Date(b.trial_ends_at).getTime() > Date.now());
  const gb = (bytes: number) => Math.round((bytes / 1024 ** 3) * 10) / 10;
  return (
    <section id="billing" aria-labelledby="billing-title" className="space-y-3">
      <h2 id="billing-title" className="text-lg font-semibold">
        {t("title")}
      </h2>
      <div className="border-t border-foreground/15 pt-5 space-y-4" data-testid="billing">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p>
            <span className="font-semibold">{t(`plan_${b.plan as "free"}`)}</span>
            {/* «Team · Testphase»: the parts as text with their separator, not glued by margins (A12) */}
            {b.status && !(b.status === "trialing" && trialOn) && <span className="text-sm text-muted">{` · ${t(`status_${b.status as "active"}`)}`}</span>}
            {/* the trial at sign-up has no Stripe status: shown by its end (UX test Z8) */}
            {trialOn && (
              <span className="text-sm">{` · ${t("trialUntil", { date: format.dateTime(new Date(b.trial_ends_at!), { dateStyle: "medium" }) })}`}</span>
            )}
          </p>
          {b.trial_ends_at && new Date(b.trial_ends_at).getTime() > Date.now() && !b.status && (
            <p className="m-0 w-full text-[15px] text-ink-2" data-testid="trial-after">
              {t("trialAfter")}
            </p>
          )}
          {b.plan !== "free" && b.checkout_available && (
            <Button variant="secondary" onClick={() => void go("/v1/orgs/{org_id}/billing/portal")}>
              {t("portal")}
            </Button>
          )}
        </div>
        {!b.enforced && <p className="text-sm text-muted">{t("notEnforced")}</p>}
        <div className="grid gap-3 sm:grid-cols-2">
          <Meter enforced={b.enforced} label={t("teams")} used={b.usage.teams} limit={b.limits.teams} />
          <Meter enforced={b.enforced} label={t("matches")} used={b.usage.max_matches_per_season} limit={b.limits.matches_per_season} />
          <Meter enforced={b.enforced} label={t("storage")} used={gb(b.usage.storage_bytes)} limit={b.limits.storage_gb} unit=" GB" />
          <Meter enforced={b.enforced} label={t("gpu")} shown={t.rich("gpuTerm", { term: (w) => <Term explain={tg("analysisMinutes")}>{w}</Term> })} used={b.usage.gpu_minutes} limit={b.limits.gpu_minutes_month} unit=" min" />
        </div>
        {/* the plans as rows of one sheet, not cards inside the card */}
        <ul className="divide-y divide-foreground/10 border-t-2 border-foreground" data-testid="plans">
          {b.plans.map((p) => (
            <li key={p.plan} className="flex flex-wrap items-center gap-x-4 gap-y-2 py-3">
              <span className="w-28 shrink-0">
                <span className="block font-semibold">{t(`plan_${p.plan}`)}</span>
                {p.plan === b.plan && <span className="block text-[0.9375rem] font-semibold text-muted">{t("current")}</span>}
              </span>
              <span className="w-40 shrink-0 font-semibold tabular-nums">{t("price", { price: p.price_month ?? 0, currency: b.currency ?? "CHF" })}</span>
              <span className="min-w-48 flex-1 text-sm text-muted">
                {[
                  t("teamsN", { count: p.teams }),
                  p.matches_per_season == null ? t("matchesUnlimited") : t("matchesN", { count: p.matches_per_season }),
                  t("storageN", { gb: p.storage_gb }),
                  p.features.includes("tracking") ? t("withAnalysis") : t("withoutAnalysis"),
                  // the goalkeeper module: Team and Verein, no add-on (A9), not Gratis (18.11.2026)
                  p.features.includes("goalkeepers") ? t("withKeepers") : null,
                  p.trial_days > 0 ? t("trial", { days: p.trial_days }) : null,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
              {p.plan !== "free" && p.plan !== b.plan && (
                <Button variant="secondary" size="sm" disabled={!b.checkout_available} onClick={() => void go("/v1/orgs/{org_id}/billing/checkout", p.plan)}>
                  {t("choose", { plan: t(`plan_${p.plan}`) })}
                </Button>
              )}
            </li>
          ))}
        </ul>
        {!b.checkout_available &&
          (b.checkout_unavailable === "currency" ? (
            // honest: no checkout in another currency, and the way that works meanwhile
            <p className="text-sm" data-testid="billing-unavailable-currency">
              {t("unavailableCurrency", { currency: b.currency ?? "EUR" })}
            </p>
          ) : (
            <p className="text-xs text-muted">{t("unavailable")}</p>
          ))}
        {problem && <Alert>{problem === "two-factor-required" ? t("needs2fa") : t("failed")}</Alert>}
      </div>
      <InvoiceOrder orgId={orgId} />
    </section>
  );
}
