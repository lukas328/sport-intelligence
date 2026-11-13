import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/page-header";
import { BackToFixtures } from "./back-to-fixtures";
import Link from "next/link";
import { OpponentPlayers } from "./opponent-players";
import { notFound } from "next/navigation";
import { getFormatter, getTranslations } from "next-intl/server";
import { EmptyState } from "@/components/ui/card";
import { PlanHint } from "@/components/billing/plan-hint";
import { serverApi } from "@/lib/api";

interface Profile {
  opponent: { id: string; name: string };
  record: { won: number; drawn: number; lost: number };
  matches: { match_id: string; kickoff_at: string; is_home: boolean; score_own: number | null; score_opponent: number | null; events: number }[];
  tagged_matches: number;
  totals: { goals: number; shots: number; shooting_pct: number | null; seven_m_goals: number; seven_m_shots: number; fast_break_goals: number; turnovers: number; xg: number; xg_shots: number; xg_coverage: number | null };
  zones: Record<string, { shots: number; goals: number }>;
  goal_zones: Record<string, { shots: number; goals: number }>;
  scorers: { number: number; goals: number; shots: number; matches: number }[];
  formations_ms: Record<string, number>;
}

const pct = (v: number | null) => (v == null ? "-" : `${Math.round(v * 100)} %`);

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("opponent"))("title") };
}

const avg = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1));

export default async function OpponentPage({ params }: { params: Promise<{ orgId: string; opponentId: string }> }) {
  const { orgId, opponentId } = await params;
  const t = await getTranslations("opponent");
  const tz = await getTranslations("zones");
  const tg = await getTranslations("goalZones");
  const tf = await getTranslations("formations");
  const format = await getFormatter();
  const client = await serverApi();
  const [res, players] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/opponents/{opponent_id}/profile", { params: { path: { org_id: orgId, opponent_id: opponentId } } }),
    client.GET("/v1/orgs/{org_id}/opponents/{opponent_id}/players", { params: { path: { org_id: orgId, opponent_id: opponentId } } }),
  ]);
  // shirt numbers read as names where the opponent's squad is known
  const nameOf = (number: number) => (players.data ?? []).find((x) => x.number === number)?.name;
  if (res.response.status === 402) return <PlanHint orgId={orgId} />;
  const p = res.data as unknown as Profile | undefined;
  if (!p) notFound();
  const n = Math.max(1, p.tagged_matches);
  const fTotal = Object.values(p.formations_ms).reduce((a, b) => a + b, 0);
  return (
    <div className="space-y-6">
      <div>
        <BackToFixtures orgId={orgId} />
        <PageHeader eyebrow={`${t("title")} · ${t("record", p.record)}`} title={p.opponent.name} />
      </div>
      {p.tagged_matches === 0 ? (
        <EmptyState title={t("none")} />
      ) : (
        <>
          <p className="text-sm text-muted">{t("tagged", { count: p.tagged_matches })}</p>
          {/* one line of the match sheet, not five tiles; averages say so and drop a ".0" */}
          <dl className={`grid grid-cols-2 gap-x-8 gap-y-4 border-t-2 border-foreground pt-4 sm:grid-cols-5`} data-testid="opponent-tiles">
            {[
              [t("goalsPerMatch"), avg(p.totals.goals / n)],
              [t("shootingPct"), pct(p.totals.shooting_pct)],
              [t("sevenM"), `${p.totals.seven_m_goals}/${p.totals.seven_m_shots}`],
              [t("fastBreakPerMatch"), avg(p.totals.fast_break_goals / n)],
              [t("turnoversPerMatch"), avg(p.totals.turnovers / n)],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-[0.9375rem] text-muted">{label}</dt>
                <dd className="mt-1 font-score text-[1.75rem] leading-none tabular-nums sm:text-3xl">{value}</dd>
              </div>
            ))}
          </dl>
          {/* three open columns on rules, not cards */}
          <div className="grid gap-8 md:grid-cols-3">
            <section className="space-y-2">
              <h2 className="font-semibold">{t("scorers")}</h2>
              {p.scorers.length === 0 && <p className="border-t-2 border-foreground pt-2 text-sm text-muted">{t("noScorers")}</p>}
              <ol className="divide-y divide-foreground/10 border-t-2 border-foreground text-sm empty:hidden">
                {p.scorers.map((s) => (
                  <li key={s.number} className="flex justify-between gap-2 py-1.5">
                    <span>
                      {t("number", { number: s.number })}
                      {nameOf(s.number) && <span className="font-medium"> {nameOf(s.number)}</span>}
                    </span>
                    <span className="tabular-nums">
                      {s.goals}/{s.shots}
                    </span>
                  </li>
                ))}
              </ol>
            </section>
            <section className="space-y-2">
              <h2 className="font-semibold">{t("zones")}</h2>
              <ul className="divide-y divide-foreground/10 border-t-2 border-foreground text-sm">
                {Object.entries(p.zones)
                  .sort((a, b) => b[1].goals - a[1].goals)
                  .map(([z, v]) => (
                    <li key={z} className="flex justify-between gap-2 py-1.5">
                      <span>{tz(z as "wing_left")}</span>
                      <span className="tabular-nums">
                        {v.goals}/{v.shots}
                      </span>
                    </li>
                  ))}
              </ul>
              <h3 className="pt-2 text-sm font-semibold">{t("goalZones")}</h3>
              {/* not every goal has a target point: say how many do */}
              <p className="text-[0.9375rem] text-muted">
                {t("goalZonesBasis", { n: Object.values(p.goal_zones).reduce((a, v) => a + v.goals, 0), total: p.totals.goals })}
              </p>
              <ul className="divide-y divide-foreground/10 border-t-2 border-foreground text-sm">
                {Object.entries(p.goal_zones)
                  .sort((a, b) => b[1].goals - a[1].goals)
                  .slice(0, 4)
                  .map(([z, v]) => (
                    <li key={z} className="flex justify-between gap-2 py-1.5">
                      <span>{tg(z as "TL")}</span>
                      <span className="tabular-nums">{v.goals}</span>
                    </li>
                  ))}
              </ul>
            </section>
            <section className="space-y-2">
              <h2 className="font-semibold">{t("formations")}</h2>
              {fTotal === 0 ? (
                <p className="text-sm text-muted">{tf("none")}</p>
              ) : (
                <ul className="divide-y divide-foreground/10 border-t-2 border-foreground text-sm">
                  {Object.entries(p.formations_ms)
                    .sort((a, b) => b[1] - a[1])
                    .map(([f, ms]) => (
                      <li key={f} className="flex justify-between gap-2 py-1.5">
                        <span>{f === "open" ? tf("open") : f.replaceAll("-", ":")}</span>
                        <span className="tabular-nums">{Math.round((ms / fTotal) * 100)} %</span>
                      </li>
                    ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}
      <section aria-label={t("matches")}>
        <h2 className="mb-2 font-semibold">
          {t("matches")} <span className="text-sm font-normal text-muted">{t("ourScoreFirst")}</span>
        </h2>
        <ul className="divide-y divide-foreground/10 border-t-2 border-foreground">
          {p.matches.map((m) => (
            <li key={m.match_id}>
              <Link href={`/app/${orgId}/matches/${m.match_id}`} className="group flex min-h-11 items-center justify-between gap-3 py-2">
                <span>
                  <span className="group-hover:underline group-hover:underline-offset-4">{format.dateTime(new Date(m.kickoff_at), { dateStyle: "medium" })}</span>
                  <span className="text-sm text-muted"> · {t(m.is_home ? "homeGame" : "awayGame")}</span>
                </span>
                <span className="flex items-baseline gap-3">
                  {m.score_own != null && m.score_opponent != null && (
                    <span className="text-sm text-muted">{t(m.score_own > m.score_opponent ? "won" : m.score_own < m.score_opponent ? "lost" : "drawn")}</span>
                  )}
                  <span className="font-score text-lg tabular-nums">{m.score_own != null && m.score_opponent != null ? `${m.score_own}:${m.score_opponent}` : ""}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
      {/* keeping the squad up to date is upkeep: after the figures, not before */}
      <OpponentPlayers orgId={orgId} opponentId={opponentId} />
    </div>
  );
}
