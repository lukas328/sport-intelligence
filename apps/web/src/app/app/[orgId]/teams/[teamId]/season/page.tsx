import Link from "next/link";
import { getFormatter, getTranslations } from "next-intl/server";
import { Card, EmptyState } from "@/components/ui/card";
import { PlanHint } from "@/components/billing/plan-hint";
import { serverApi } from "@/lib/api";

interface Row {
  match_id: string;
  kickoff_at: string;
  opponent: string;
  is_home: boolean;
  score_own: number;
  score_opponent: number;
  goals: number;
  shots: number;
  shooting_pct: number | null;
  save_pct: number | null;
  turnovers: number;
  xg: number;
  xg_against: number;
  seven_m: [number, number];
}
interface Season {
  matches: Row[];
  totals: { matches: number; goals: number; shots: number; turnovers: number; xg: number; shooting_pct: number | null; save_pct: number | null };
  players: { player_id: string; matches: number; goals: number; shots: number; turnovers: number; suspensions: number; saves: number; xg: number; shooting_pct: number | null }[];
}

const pct = (v: number | null) => (v == null ? "-" : `${Math.round(v * 100)} %`);

export default async function SeasonPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const t = await getTranslations("season");
  const format = await getFormatter();
  const client = await serverApi();
  const team = await client.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: teamId } } });
  const seasonId = team.data?.current_season?.id;
  if (!seasonId) return <EmptyState title={t("none")} />;
  const path = { params: { path: { org_id: orgId, team_id: teamId, season_id: seasonId } } };
  const [stats, roster] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/stats", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster", path),
  ]);
  if (stats.response.status === 402) return <PlanHint orgId={orgId} />;
  const data = stats.data as unknown as Season | undefined;
  if (!data || data.matches.length === 0) return <EmptyState title={t("none")} />;
  const names = Object.fromEntries((roster.data ?? []).map((r) => [r.player_id, `${r.jersey_number != null ? `#${r.jersey_number} ` : ""}${r.first_name} ${r.last_name}`]));
  const n = data.totals.matches;
  const tiles = [
    { label: t("matches"), value: n },
    { label: `${t("goals")} ${t("perMatch")}`, value: (data.totals.goals / n).toFixed(1) },
    { label: t("shootingPct"), value: pct(data.totals.shooting_pct) },
    { label: t("savePct"), value: pct(data.totals.save_pct) },
    { label: `${t("turnovers")} ${t("perMatch")}`, value: (data.totals.turnovers / n).toFixed(1) },
  ];
  return (
    <div className="space-y-6">
      <h2 className="sr-only">{t("title")}</h2>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5" data-testid="season-tiles">
        {tiles.map((x) => (
          <div key={x.label} className="rounded-lg border border-border p-3">
            <dt className="text-xs text-muted">{x.label}</dt>
            <dd className="text-2xl font-semibold tabular-nums">{x.value}</dd>
          </div>
        ))}
      </dl>
      <Card className="space-y-2">
        <h3 className="font-semibold">{t("trend")}</h3>
        <TrendChart rows={data.matches} label={t("chartLabel")} goals={t("goals")} xg={t("xg")} />
      </Card>
      <div className="overflow-x-auto rounded-md border border-border">
        <table className="w-full text-sm" data-testid="season-matches">
          <caption className="sr-only">{t("matches")}</caption>
          <thead className="bg-surface text-muted">
            <tr>
              <th scope="col" className="px-3 py-2 text-left font-medium">{t("match")}</th>
              <th scope="col" className="px-2 py-2 text-right font-medium">{t("result")}</th>
              <th scope="col" className="px-2 py-2 text-right font-medium">{t("shootingPct")}</th>
              <th scope="col" className="px-2 py-2 text-right font-medium">{t("savePct")}</th>
              <th scope="col" className="px-2 py-2 text-right font-medium">{t("turnovers")}</th>
              <th scope="col" className="px-2 py-2 text-right font-medium">{t("xg")}</th>
              <th scope="col" className="px-2 py-2 text-right font-medium">{t("xgAgainst")}</th>
              <th scope="col" className="px-2 py-2 text-right font-medium">{t("sevenM")}</th>
            </tr>
          </thead>
          <tbody>
            {data.matches.map((m) => (
              <tr key={m.match_id} className="border-t border-border">
                <th scope="row" className="px-3 py-1.5 text-left font-medium">
                  <Link href={`/app/${orgId}/matches/${m.match_id}`} className="underline decoration-dotted underline-offset-4">
                    {format.dateTime(new Date(m.kickoff_at), { dateStyle: "short" })} {m.is_home ? "" : "@ "}
                    {m.opponent}
                  </Link>
                </th>
                <td className="px-2 py-1.5 text-right tabular-nums">
                  {m.score_own}:{m.score_opponent}
                </td>
                <td className="px-2 py-1.5 text-right tabular-nums">{pct(m.shooting_pct)}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{pct(m.save_pct)}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{m.turnovers}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{m.xg.toFixed(1)}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{m.xg_against.toFixed(1)}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">
                  {m.seven_m[0]}/{m.seven_m[1]}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.players.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-sm" data-testid="season-players">
            <caption className="px-3 py-2 text-left font-semibold">{t("players")}</caption>
            <thead className="bg-surface text-muted">
              <tr>
                <th scope="col" className="px-3 py-2 text-left font-medium">{t("player")}</th>
                <th scope="col" className="px-2 py-2 text-right font-medium">{t("matches")}</th>
                <th scope="col" className="px-2 py-2 text-right font-medium">{t("goals")}</th>
                <th scope="col" className="px-2 py-2 text-right font-medium">{t("shootingPct")}</th>
                <th scope="col" className="px-2 py-2 text-right font-medium">{t("xg")}</th>
                <th scope="col" className="px-2 py-2 text-right font-medium">{t("turnovers")}</th>
              </tr>
            </thead>
            <tbody>
              {data.players.map((p) => (
                <tr key={p.player_id} className="border-t border-border">
                  <th scope="row" className="px-3 py-1.5 text-left font-medium">{names[p.player_id] ?? "?"}</th>
                  <td className="px-2 py-1.5 text-right tabular-nums">{p.matches}</td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{p.goals}</td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{pct(p.shooting_pct)}</td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{p.xg.toFixed(1)}</td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{p.turnovers}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/** Goals and xG per match on one axis; identity by colour, dash and legend; values on hover. */
function TrendChart({ rows, label, goals, xg }: { rows: Row[]; label: string; goals: string; xg: string }) {
  const w = 640;
  const h = 200;
  const pad = { l: 32, r: 16, t: 12, b: 24 };
  const max = Math.max(5, ...rows.flatMap((r) => [r.goals, r.xg]));
  const X = (i: number) => pad.l + (rows.length === 1 ? (w - pad.l - pad.r) / 2 : (i / (rows.length - 1)) * (w - pad.l - pad.r));
  const Y = (v: number) => h - pad.b - (v / max) * (h - pad.t - pad.b);
  const line = (k: "goals" | "xg") => rows.map((r, i) => `${i ? "L" : "M"}${X(i)} ${Y(r[k])}`).join(" ");
  const ticks = [0, Math.round(max / 2), Math.round(max)];
  return (
    <div className="space-y-2">
      <ul className="flex gap-4 text-xs text-muted" aria-hidden>
        <li className="flex items-center gap-1.5">
          <svg width="18" height="6"><line x1="0" x2="18" y1="3" y2="3" stroke="var(--accent)" strokeWidth={2} /></svg>
          {goals}
        </li>
        <li className="flex items-center gap-1.5">
          <svg width="18" height="6"><line x1="0" x2="18" y1="3" y2="3" stroke="var(--muted)" strokeWidth={2} strokeDasharray="4 3" /></svg>
          {xg}
        </li>
      </ul>
      <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={label} className="w-full" data-testid="season-trend">
        {ticks.map((v) => (
          <g key={v}>
            <line x1={pad.l} x2={w - pad.r} y1={Y(v)} y2={Y(v)} stroke="var(--border)" strokeWidth={1} />
            <text x={pad.l - 6} y={Y(v) + 3} fontSize="10" textAnchor="end" fill="var(--muted)">
              {v}
            </text>
          </g>
        ))}
        <path d={line("xg")} fill="none" stroke="var(--muted)" strokeWidth={2} strokeDasharray="5 4" />
        <path d={line("goals")} fill="none" stroke="var(--accent)" strokeWidth={2} />
        {rows.map((r, i) => (
          <g key={r.match_id}>
            <circle cx={X(i)} cy={Y(r.goals)} r={4} fill="var(--accent)" stroke="var(--background)" strokeWidth={2} />
            <circle cx={X(i)} cy={Y(r.goals)} r={12} fill="transparent">
              <title>{`${r.opponent}: ${goals} ${r.goals}, ${xg} ${r.xg.toFixed(1)}`}</title>
            </circle>
            <text x={X(i)} y={h - 6} fontSize="10" textAnchor="middle" fill="var(--muted)">
              {i + 1}
            </text>
          </g>
        ))}
        {rows.length > 0 && (
          <text x={X(rows.length - 1)} y={Y(rows[rows.length - 1]!.goals) - 8} fontSize="11" textAnchor="end" fill="var(--foreground)">
            {rows[rows.length - 1]!.goals}
          </text>
        )}
      </svg>
    </div>
  );
}
