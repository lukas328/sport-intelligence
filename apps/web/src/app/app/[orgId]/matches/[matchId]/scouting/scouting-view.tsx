"use client";

import { BackLink } from "@/components/ui/back-link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useFormatter, useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/card";
import { api } from "@/lib/client";

type Ref = { event_id: string; match_id: string; video_id: string | null; t_ms: number | null };
type Facts = {
  opponent: { name: string };
  glance: { matches: number; tagged_matches: number; record: { won: number; drawn: number; lost: number }; goals_per_match: number | null; shooting_pct: number | null; n: number };
  shooters: { number: number; goals: number; shots: number; shooting_pct: number | null; main_zone: string | null; goal_zones: Record<string, number>; n: number; clips: Ref[] }[];
  defense: { formations_ms: Record<string, number>; weak_zones: { zone: string; goals: number; shots: number; pct: number | null; n: number; clips: Ref[] }[] };
  fast_break: { goals: number; share: number | null; n: number; clips: Ref[] };
  numbers: Record<"they_in_powerplay" | "we_in_powerplay", { periods: number; goals: number; n: number; clips: Ref[] }>;
  observations: { key: string; params: Record<string, string | number | null>; n: number; clips: Ref[] }[];
  missing: string[];
};

const GRID = ["TL", "TC", "TR", "ML", "MC", "MR", "BL", "BC", "BR"];
const pct = (v: number | null | undefined) => (v == null ? "-" : `${Math.round(v * 100)} %`);

/** Automatic preparation report (addendum 01, 4.6): every statement with sample size and clips. */
export function ScoutingView({ orgId, matchId }: { orgId: string; matchId: string }) {
  const t = useTranslations("scouting");
  const tz = useTranslations("zones");
  const locale = useLocale();
  const format = useFormatter();
  const qc = useQueryClient();
  const path = { org_id: orgId, match_id: matchId };
  const q = useQuery({
    queryKey: ["scouting", matchId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/scouting", { params: { path } })).data ?? null,
  });
  const create = useMutation({
    mutationFn: async () => (await api.POST("/v1/orgs/{org_id}/matches/{match_id}/scouting", { params: { path } })).data,
    onSuccess: (d) => qc.setQueryData(["scouting", matchId], d),
  });
  const router = useRouter();
  const asPresentation = useMutation({
    mutationFn: async (id: string) =>
      (await api.POST("/v1/orgs/{org_id}/scouting/{report_id}/presentation", { params: { path: { org_id: orgId, report_id: id } } })).data,
    onSuccess: (p) => p && router.push(`/app/${orgId}/presentations/${p.id}`),
  });
  // the title names the opponent and the date: a report is about one match
  const match = useQuery({
    queryKey: ["match", matchId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}", { params: { path } })).data,
  });
  const rep = q.data;
  const f = rep?.facts as Facts | undefined;
  const zone = (z: string | null) => (z ? (tz.has(z) ? tz(z) : z) : "-");
  const clips = (refs: Ref[]) =>
    refs.filter((r) => r.video_id && r.t_ms != null).length > 0 && (
      <span className="ml-2 inline-flex gap-1">
        {refs
          .filter((r) => r.video_id && r.t_ms != null)
          .map((r, i) => (
            <Link key={r.event_id} href={`/app/${orgId}/matches/${r.match_id}?t=${Math.max(0, (r.t_ms ?? 0) - 6000)}`} className="font-medium underline underline-offset-4">
              {t("clipN", { n: i + 1 })}
            </Link>
          ))}
      </span>
    );
  const sample = (n: number) => <span className="text-xs text-muted"> ({t("sample", { n })})</span>;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <BackLink fallback={`/app/${orgId}/matches/${matchId}`} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-muted">
            {t("title")}
            {match.data && ` · ${format.dateTime(new Date(match.data.kickoff_at), { weekday: "short", day: "numeric", month: "long", year: "numeric" })}`}
          </p>
          <h1 className="text-2xl font-bold sm:text-[1.75rem]">{match.data?.opponent?.name ? t("against", { name: match.data.opponent.name }) : t("title")}</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          {rep && (
            <Button variant="secondary" loading={create.isPending} onClick={() => create.mutate()}>
              {t("refresh")}
            </Button>
          )}
          {rep && (
            <>
              <a className="inline-flex min-h-9 items-center gap-1.5 bg-raised px-4 text-[0.9375rem] font-medium ring-1 ring-inset ring-border hover:bg-surface" href={`/v1/orgs/${orgId}/scouting/${rep.id}/pdf?lang=${locale}`}>
                {t("pdf")}
              </a>
              <a className="inline-flex min-h-9 items-center gap-1.5 bg-raised px-4 text-[0.9375rem] font-medium ring-1 ring-inset ring-border hover:bg-surface" href={`/v1/orgs/${orgId}/scouting/${rep.id}/goalkeeper-card?lang=${locale}`}>
                {t("gkCard")}
              </a>
              <Button variant="secondary" loading={asPresentation.isPending} onClick={() => asPresentation.mutate(rep.id)}>
                {t("asPresentation")}
              </Button>
            </>
          )}
        </div>
      </div>
      {!rep && !q.isLoading && (
        <EmptyState title={t("none")} action={<Button loading={create.isPending} onClick={() => create.mutate()}>{t("create")}</Button>}>
          {t("autoHint")}
        </EmptyState>
      )}
      {rep && f && (
        <>
          <p className="text-sm text-muted" data-testid="scouting-basis">
            {t("basis", { matches: f.glance.matches, tagged: f.glance.tagged_matches, date: format.dateTime(new Date(rep.generated_at), { dateStyle: "medium", timeStyle: "short" }) })}
          </p>
          {f.missing.length > 0 && <p className="text-sm">{t("missing", { items: f.missing.map((m) => t(`missing_${m}` as "missing_video")).join(", ") })}</p>}

          <section className="space-y-2 border-t-2 border-foreground pt-3">
            <h2 className="font-semibold">{t("observations")}</h2>
            <p className="text-xs text-muted">{t("observationsHint")}</p>
            {f.observations.length === 0 ? (
              <p className="text-sm text-muted">{t("noObservations")}</p>
            ) : (
              <ul className="space-y-1 text-sm" data-testid="observations">
                {f.observations.map((o) => (
                  <li key={o.key}>
                    {t(`obs_${o.key}` as "obs_top_shooter", { ...o.params, share: pct(o.params.share as number), pct: pct(o.params.pct as number), zone: zone(o.params.zone as string) })}
                    {sample(o.n)}
                    {clips(o.clips)}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-1 border-t-2 border-foreground pt-3">
            <h2 className="font-semibold">{t("glance")}</h2>
            <p className="text-sm">{t("record", f.glance.record)}</p>
            <p className="text-sm">
              {t("goalsPerMatch", { v: f.glance.goals_per_match ?? "-" })} · {t("shootingPct", { v: pct(f.glance.shooting_pct) })}
              {sample(f.glance.n)}
            </p>
          </section>

          <section className="space-y-2 border-t-2 border-foreground pt-3">
            <h2 className="font-semibold">{t("shooters")}</h2>
            {f.shooters.length === 0 && <p className="text-sm text-muted">{t("noShooters")}</p>}
            <ul className="grid gap-3 sm:grid-cols-2" data-testid="shooters">
              {f.shooters.map((s) => (
                <li key={s.number} className="flex gap-3 ring-1 ring-inset ring-border p-2 text-sm">
                  <div className="grid size-16 shrink-0 grid-cols-3 border border-error" aria-hidden>
                    {GRID.map((z) => (
                      <span key={z} className="flex items-center justify-center text-[14px] tabular-nums" style={{ background: s.goal_zones[z] ? `rgba(220,38,38,${0.15 + 0.6 * (s.goal_zones[z]! / Math.max(...Object.values(s.goal_zones)))})` : undefined }}>
                        {s.goal_zones[z] ?? ""}
                      </span>
                    ))}
                  </div>
                  <div>
                    <p className="font-semibold">#{s.number}</p>
                    <p>
                      {t("goalsShots", { goals: s.goals, shots: s.shots, pct: pct(s.shooting_pct) })}
                      {sample(s.n)}
                    </p>
                    <p className="text-muted">{zone(s.main_zone)}</p>
                    {clips(s.clips)}
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="space-y-1 border-t-2 border-foreground pt-3">
            <h2 className="font-semibold">{t("plays")}</h2>
            <p className="text-sm text-muted">{t("playsMissing")}</p>
          </section>

          <section className="space-y-1 border-t-2 border-foreground pt-3">
            <h2 className="font-semibold">{t("defense")}</h2>
            {Object.keys(f.defense.formations_ms).length === 0 && f.defense.weak_zones.length === 0 && <p className="text-sm text-muted">{t("noDefense")}</p>}
            {Object.entries(f.defense.formations_ms).map(([form, ms]) => (
              <p key={form} className="text-sm">
                {t("formation", { f: form, share: pct(ms / Object.values(f.defense.formations_ms).reduce((a, b) => a + b, 0)) })}
              </p>
            ))}
            {f.defense.weak_zones.map((w) => (
              <p key={w.zone} className="text-sm">
                {t("weakZone", { zone: zone(w.zone), goals: w.goals, shots: w.shots, pct: pct(w.pct) })}
                {sample(w.n)}
                {clips(w.clips)}
              </p>
            ))}
          </section>

          <section className="space-y-1 border-t-2 border-foreground pt-3">
            <h2 className="font-semibold">{t("fastBreak")}</h2>
            <p className="text-sm">
              {t("fastBreakText", { goals: f.fast_break.goals, share: pct(f.fast_break.share) })}
              {sample(f.fast_break.n)}
              {clips(f.fast_break.clips)}
            </p>
          </section>

          <section className="space-y-1 border-t-2 border-foreground pt-3">
            <h2 className="font-semibold">{t("numbers")}</h2>
            <p className="text-sm">
              {t("theyPP", { goals: f.numbers.they_in_powerplay.goals, periods: f.numbers.they_in_powerplay.periods })}
              {clips(f.numbers.they_in_powerplay.clips)}
            </p>
            <p className="text-sm">
              {t("wePP", { goals: f.numbers.we_in_powerplay.goals, periods: f.numbers.we_in_powerplay.periods })}
              {clips(f.numbers.we_in_powerplay.clips)}
            </p>
          </section>
        </>
      )}
    </div>
  );
}
