import Link from "next/link";
import { notFound } from "next/navigation";
import { getFormatter, getTranslations } from "next-intl/server";
import { Card, EmptyState } from "@/components/ui/card";
import { PlanHint } from "@/components/billing/plan-hint";
import { serverApi } from "@/lib/api";

interface Profile {
  opponent: { id: string; name: string };
  record: { won: number; drawn: number; lost: number };
  matches: { match_id: string; kickoff_at: string; score_own: number | null; score_opponent: number | null; events: number }[];
  tagged_matches: number;
  totals: { goals: number; shots: number; shooting_pct: number | null; seven_m_goals: number; seven_m_shots: number; fast_break_goals: number; turnovers: number };
  zones: Record<string, { shots: number; goals: number }>;
  goal_zones: Record<string, { shots: number; goals: number }>;
  scorers: { number: number; goals: number; shots: number; matches: number }[];
  formations_ms: Record<string, number>;
}

const pct = (v: number | null) => (v == null ? "-" : `${Math.round(v * 100)} %`);

export default async function OpponentPage({ params }: { params: Promise<{ orgId: string; opponentId: string }> }) {
  const { orgId, opponentId } = await params;
  const t = await getTranslations("opponent");
  const tz = await getTranslations("zones");
  const tg = await getTranslations("goalZones");
  const tf = await getTranslations("formations");
  const format = await getFormatter();
  const res = await (await serverApi()).GET("/v1/orgs/{org_id}/opponents/{opponent_id}/profile", {
    params: { path: { org_id: orgId, opponent_id: opponentId } },
  });
  if (res.response.status === 402) return <PlanHint orgId={orgId} />;
  const p = res.data as unknown as Profile | undefined;
  if (!p) notFound();
  const n = Math.max(1, p.tagged_matches);
  const fTotal = Object.values(p.formations_ms).reduce((a, b) => a + b, 0);
  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm text-muted">{t("title")}</p>
        <h1 className="text-2xl font-semibold">{p.opponent.name}</h1>
        <p className="text-sm">{t("record", p.record)}</p>
      </header>
      {p.tagged_matches === 0 ? (
        <EmptyState title={t("none")} />
      ) : (
        <>
          <p className="text-sm text-muted">{t("tagged", { count: p.tagged_matches })}</p>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5" data-testid="opponent-tiles">
            {[
              [t("goals"), (p.totals.goals / n).toFixed(1)],
              [t("shootingPct"), pct(p.totals.shooting_pct)],
              [t("sevenM"), `${p.totals.seven_m_goals}/${p.totals.seven_m_shots}`],
              [t("fastBreak"), (p.totals.fast_break_goals / n).toFixed(1)],
              [t("turnovers"), (p.totals.turnovers / n).toFixed(1)],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-border p-3">
                <dt className="text-xs text-muted">{label}</dt>
                <dd className="text-2xl font-semibold tabular-nums">{value}</dd>
              </div>
            ))}
          </dl>
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="space-y-2">
              <h2 className="font-semibold">{t("scorers")}</h2>
              <ol className="space-y-1 text-sm">
                {p.scorers.map((s) => (
                  <li key={s.number} className="flex justify-between gap-2">
                    <span>{t("number", { number: s.number })}</span>
                    <span className="tabular-nums">
                      {s.goals}/{s.shots}
                    </span>
                  </li>
                ))}
              </ol>
            </Card>
            <Card className="space-y-2">
              <h2 className="font-semibold">{t("zones")}</h2>
              <ul className="space-y-1 text-sm">
                {Object.entries(p.zones)
                  .sort((a, b) => b[1].goals - a[1].goals)
                  .map(([z, v]) => (
                    <li key={z} className="flex justify-between gap-2">
                      <span>{tz(z as "wing_left")}</span>
                      <span className="tabular-nums">
                        {v.goals}/{v.shots}
                      </span>
                    </li>
                  ))}
              </ul>
              <h3 className="pt-2 text-sm font-semibold">{t("goalZones")}</h3>
              <ul className="space-y-1 text-sm">
                {Object.entries(p.goal_zones)
                  .sort((a, b) => b[1].goals - a[1].goals)
                  .slice(0, 4)
                  .map(([z, v]) => (
                    <li key={z} className="flex justify-between gap-2">
                      <span>{tg(z as "TL")}</span>
                      <span className="tabular-nums">{v.goals}</span>
                    </li>
                  ))}
              </ul>
            </Card>
            <Card className="space-y-2">
              <h2 className="font-semibold">{t("formations")}</h2>
              {fTotal === 0 ? (
                <p className="text-sm text-muted">{tf("none")}</p>
              ) : (
                <ul className="space-y-1 text-sm">
                  {Object.entries(p.formations_ms)
                    .sort((a, b) => b[1] - a[1])
                    .map(([f, ms]) => (
                      <li key={f} className="flex justify-between gap-2">
                        <span>{f === "open" ? tf("open") : f.replaceAll("-", ":")}</span>
                        <span className="tabular-nums">{Math.round((ms / fTotal) * 100)} %</span>
                      </li>
                    ))}
                </ul>
              )}
            </Card>
          </div>
        </>
      )}
      <section aria-label={t("matches")}>
        <h2 className="mb-2 font-semibold">{t("matches")}</h2>
        <ul className="divide-y divide-border rounded-lg border border-border">
          {p.matches.map((m) => (
            <li key={m.match_id}>
              <Link href={`/app/${orgId}/matches/${m.match_id}`} className="flex justify-between gap-3 px-4 py-2 hover:bg-surface">
                <span>{format.dateTime(new Date(m.kickoff_at), { dateStyle: "medium" })}</span>
                <span className="tabular-nums">{m.score_own != null && m.score_opponent != null ? `${m.score_own}:${m.score_opponent}` : "-"}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
