import type { Metadata } from "next";
import Link from "next/link";
import { getFormatter, getTranslations } from "next-intl/server";
import { PlanHint } from "@/components/billing/plan-hint";
import { serverApi } from "@/lib/api";
import { MatchScore } from "@/components/domain/match-score";
import { Stage, stageButton, stageLink } from "@/components/domain/stage";
import { AreaSubNav } from "@/components/shell/section-nav";
import { IconAsk } from "@/components/shell/icons";
import { focusMetric, matchStatement, seasonStatement } from "@/lib/voice";
import { cn } from "@/lib/utils";

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

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("season"))("title") };
}

export default async function SeasonPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const t = await getTranslations("season");
  const tv = await getTranslations("voice");
  const tm = await getTranslations("matches");
  const tp = await getTranslations("palette");
  const format = await getFormatter();
  const client = await serverApi();
  const [team, org] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: teamId } } }),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
  ]);
  const staff = org.data?.my_role === "org_admin" || ["coach", "analyst", "team_manager", "goalkeeper_coach", "athletic_coach"].includes(team.data?.my_role ?? "");
  const base = `/app/${orgId}/teams/${teamId}`;
  const seasonId = team.data?.current_season?.id;
  const label = team.data?.current_season ? t("title") + " " + team.data.current_season.label : t("title");
  const tools = staff ? (
    <>
      <Link href={`${base}/matrix`} className={stageButton("outline")}>
        {tp("matrix")}
      </Link>
      <Link href={`${base}/assistant`} className={stageLink}>
        <IconAsk />
        {tp("ask")}
      </Link>
    </>
  ) : null;
  const stats = seasonId
    ? await client.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/stats", { params: { path: { org_id: orgId, team_id: teamId, season_id: seasonId } } })
    : null;
  if (stats?.response.status === 402) return <PlanHint orgId={orgId} />;
  const data = stats?.data as unknown as Season | undefined;
  if (!seasonId || !data || data.matches.length === 0) {
    return (
      <div className="space-y-8">
        <AreaSubNav />
        <Stage pullMobile={false}>
          <p className="text-[0.9375rem] font-semibold">{label}</p>
          <h1 className="mt-2 text-[2.75rem] leading-[0.95] sm:text-6xl">{tv("noMatchYet")}</h1>
          <p className="mt-4 max-w-lg text-lg">{t("none")}</p>
          {tools && <div className="mt-7 flex flex-wrap gap-3">{tools}</div>}
        </Stage>
      </div>
    );
  }
  const roster = await client.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster", { params: { path: { org_id: orgId, team_id: teamId, season_id: seasonId } } });
  const names = Object.fromEntries((roster.data ?? []).map((r) => [r.player_id, `${r.jersey_number != null ? `#${r.jersey_number} ` : ""}${r.first_name} ${r.last_name}`]));
  const n = data.totals.matches;
  const statement = seasonStatement(data.matches);
  const last = [...data.matches].sort((x, y) => y.kickoff_at.localeCompare(x.kickoff_at))[0]!;
  const lastResult = matchStatement({ own: last.score_own, opp: last.score_opponent, opponent: last.opponent });
  const focus = focusMetric({ save_pct: data.totals.save_pct, shooting_pct: data.totals.shooting_pct, turnovers_per_match: data.totals.turnovers / n });
  const goalsFor = data.totals.goals / n;
  const goalsAgainst = data.matches.reduce((sum, m) => sum + m.score_opponent, 0) / n;
  const turnovers = data.totals.turnovers / n;
  // one row per figure: value, a bar on a fixed scale and a tick for the reference (or goals against)
  const cells: { key: string; label: string; value: string; href: string; share: number | null; tick: number; refText: string; focus?: boolean }[] = [
    { key: "goals", label: `${t("goals")} ${t("perMatch")}`, value: goalsFor.toFixed(1), href: `${base}/search?type=shot&outcome=goal&side=own`, share: goalsFor / 40, tick: goalsAgainst / 40, refText: tv("againstRef", { value: goalsAgainst.toFixed(1) }) },
    { key: "shooting", label: t("shootingPct"), value: pct(data.totals.shooting_pct), href: `${base}/search?type=shot&side=own`, share: data.totals.shooting_pct, tick: 0.55, refText: tv("reference", { value: "55 %" }), focus: focus === "shooting_pct" },
    { key: "save", label: t("savePct"), value: pct(data.totals.save_pct), href: `${base}/search?type=shot&outcome=save&side=opponent`, share: data.totals.save_pct, tick: 0.3, refText: tv("reference", { value: "30 %" }), focus: focus === "save_pct" },
    { key: "turnovers", label: `${t("turnovers")} ${t("perMatch")}`, value: turnovers.toFixed(1), href: `${base}/search?type=turnover&side=own`, share: turnovers / 24, tick: 0.5, refText: `${tv("reference", { value: "12" })}, ${tv("lowerBetter")}`, focus: focus === "turnovers" },
  ];
  const pick = (score: (r: Row) => number | null) =>
    data.matches.reduce<Row | null>((best, r) => (score(r) != null && (best == null || score(r)! > score(best)!) ? r : best), null);
  const bestGoals = pick((r) => r.score_own);
  const bestShooting = pick((r) => r.shooting_pct);
  const bestSave = pick((r) => r.save_pct);
  const fewestTo = pick((r) => -r.turnovers);
  const bests = [
    { label: t("bestGoals"), row: bestGoals, value: bestGoals?.score_own },
    { label: t("bestShooting"), row: bestShooting, value: pct(bestShooting?.shooting_pct ?? null) },
    { label: t("bestSave"), row: bestSave, value: pct(bestSave?.save_pct ?? null) },
    { label: t("fewestTurnovers"), row: fewestTo, value: fewestTo?.turnovers },
  ];
  const scorers = [...data.players].filter((p) => p.shots > 0).sort((a, b) => b.goals - a.goals || (b.shooting_pct ?? 0) - (a.shooting_pct ?? 0)).slice(0, 8);
  const topGoals = Math.max(1, ...scorers.map((p) => p.goals));
  const lastWon = last.score_own > last.score_opponent ? "won" : last.score_own < last.score_opponent ? "lost" : "draw";
  return (
    <div className="space-y-12">
      <div className="space-y-5 lg:space-y-0">
      <AreaSubNav />
      <Stage
        pullMobile={false}
        eyebrow={tv("afterMatches", { label, n })}
        aside={
          <Link href={`/app/${orgId}/matches/${last.match_id}`} className="group block text-left xl:text-center">
            <span className="block text-[0.9375rem] font-semibold">{tv("lastResult")}: {tm(lastWon)}</span>
            <MatchScore own={last.score_own} opp={last.score_opponent} className="text-[5rem] leading-[0.85] xl:text-[clamp(3.5rem,4.6vw,5.25rem)]" />
            <span className="block text-[0.9375rem] group-hover:underline">{last.opponent}</span>
          </Link>
        }
      >
        <h1 className="mt-2 text-[2.75rem] leading-[0.95] sm:text-6xl lg:text-[4.25rem]">
          {statement ? tv(statement.headline.key.replace("voice.", "") as "overXg", statement.headline.params as never) : lastResult ? tv(lastResult.headline.key.replace("voice.", "") as "won", lastResult.headline.params as never) : tv("neutralSeason")}
        </h1>
        {statement?.evidence && <p className="mt-4 max-w-xl text-lg">{tv(statement.evidence.key.replace("voice.", "") as "record", statement.evidence.params as never)}</p>}
        <div className="mt-7 flex flex-wrap gap-3">
          <Link href={`${base}/search?type=shot&outcome=goal&side=own`} className={stageButton("solid")}>
            {tv("goalsAsClips")}
          </Link>
          {tools}
        </div>
      </Stage>
      </div>

      <div className="grid gap-12 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)] lg:gap-16">
        <section className="space-y-4">
          <h2 className="text-2xl">{tv("inNumbers")}</h2>
          <ul className="border-y border-foreground/15" data-testid="season-tiles">
            {cells.map((c) => (
              <li key={c.key} className="border-t border-foreground/10 first:border-t-0">
                <Link
                  href={c.href}
                  className="group grid grid-cols-[minmax(0,1fr)_auto] items-end gap-x-6 gap-y-3 py-4 sm:grid-cols-[14rem_6.5rem_minmax(0,1fr)] sm:items-center"
                >
                  <span className="min-w-0">
                    <span className="block font-semibold group-hover:text-accent">{c.label}</span>
                    {c.focus && (
                      <span className="mt-0.5 mb-1.5 block w-fit text-sm font-semibold underline decoration-resin decoration-[5px] underline-offset-[5px]">{tv("focus")}</span>
                    )}
                    <span className="block text-sm text-muted">{c.refText}</span>
                  </span>
                  <span className="text-right font-score text-[2.5rem] leading-none sm:text-left">{c.value}</span>
                  <StatBar share={c.share} tick={c.tick} focus={c.focus} />
                </Link>
              </li>
            ))}
          </ul>
          <p className="text-sm text-muted">{tv("focusNote")}</p>
        </section>

        <div className="space-y-12">
          <section className="space-y-4">
            <h2 className="text-2xl">{t("form")}</h2>
            <ol className="flex flex-wrap gap-x-2 gap-y-4">
              {[...data.matches]
                .sort((x, y) => x.kickoff_at.localeCompare(y.kickoff_at))
                .map((m) => {
                  const r = m.score_own > m.score_opponent ? "won" : m.score_own < m.score_opponent ? "lost" : "draw";
                  return (
                    <li key={m.match_id}>
                      <Link
                        href={`/app/${orgId}/matches/${m.match_id}`}
                        title={`${format.dateTime(new Date(m.kickoff_at), { dateStyle: "medium" })} ${m.opponent} ${m.score_own}:${m.score_opponent}`}
                        className="group flex w-16 flex-col items-center gap-1.5 text-center"
                      >
                        <span
                          aria-hidden
                          className={cn(
                            "grid size-10 place-items-center rounded-[5px] font-score text-xl text-background transition-transform group-hover:-translate-y-0.5",
                            r === "won" ? "bg-ok" : r === "lost" ? "bg-error" : "bg-muted",
                          )}
                        >
                          {tm(r).charAt(0)}
                        </span>
                        <span className="sr-only">{tm(r)}</span>
                        <span className="font-score text-lg leading-none group-hover:underline">
                          {m.score_own}:{m.score_opponent}
                        </span>
                        <span className="w-full truncate text-xs text-muted">{m.opponent}</span>
                      </Link>
                    </li>
                  );
                })}
            </ol>
          </section>

          {n > 1 && (
            <section className="space-y-4">
              <h2 className="text-2xl">{t("best")}</h2>
              <ul className="border-y border-foreground/15">
                {bests.map((b) =>
                  b.row ? (
                    <li key={b.label} className="border-t border-foreground/10 first:border-t-0">
                      <Link href={`/app/${orgId}/matches/${b.row.match_id}`} className="group flex items-baseline gap-4 py-3">
                        <span className="min-w-0 flex-1">
                          <span className="block text-sm font-semibold">{b.label}</span>
                          <span className="block truncate text-sm text-muted group-hover:underline">{t("against", { opponent: b.row.opponent })}</span>
                        </span>
                        <span className="font-score text-3xl leading-none">{b.value}</span>
                      </Link>
                    </li>
                  ) : null,
                )}
              </ul>
            </section>
          )}
        </div>
      </div>

      {n >= 3 ? (
        <div className={cn("grid gap-8", scorers.length > 0 && "lg:grid-cols-2")}>
          <section className="space-y-3">
            <h2 className="text-2xl">{t("trend")}</h2>
            <TrendChart rows={data.matches} label={t("chartLabel")} goals={t("goals")} xg={t("xg")} />
          </section>
          {scorers.length > 0 && <Scorers scorers={scorers} names={names} topGoals={topGoals} t={t} />}
        </div>
      ) : (
        <>
          <p className="text-[0.9375rem] text-muted" data-testid="season-trend">
            {tv("chartLater")}
          </p>
          {scorers.length > 0 && <Scorers scorers={scorers} names={names} topGoals={topGoals} t={t} />}
        </>
      )}

      <section className="space-y-3">
        <h2 className="text-2xl">{t("allMatches")}</h2>
        <div className="sheet overflow-x-auto">
          <table className="w-full text-[0.9375rem]" data-testid="season-matches">
            <caption className="sr-only">{t("matches")}</caption>
            <thead>
              <tr>
                <th scope="col" className="text-left">{t("match")}</th>
                <th scope="col">{t("result")}</th>
                <th scope="col">{t("shootingPct")}</th>
                <th scope="col">{t("savePct")}</th>
                <th scope="col">{t("turnovers")}</th>
                <th scope="col">{t("xg")}</th>
                <th scope="col">{t("xgAgainst")}</th>
                <th scope="col">{t("sevenM")}</th>
              </tr>
            </thead>
            <tbody>
              {data.matches.map((m) => (
                <tr key={m.match_id}>
                  <th scope="row" className="text-left font-medium">
                    <Link href={`/app/${orgId}/matches/${m.match_id}`} className="hover:text-accent hover:underline">
                      <span className="text-muted tabular-nums">{format.dateTime(new Date(m.kickoff_at), { dateStyle: "short" })}</span> {m.is_home ? "" : "@ "}
                      {m.opponent}
                    </Link>
                  </th>
                  <td className="font-semibold">
                    {m.score_own}:{m.score_opponent}
                  </td>
                  <td>{pct(m.shooting_pct)}</td>
                  <td>{pct(m.save_pct)}</td>
                  <td>{m.turnovers}</td>
                  <td>{m.xg.toFixed(1)}</td>
                  <td>{m.xg_against.toFixed(1)}</td>
                  <td>
                    {m.seven_m[0]}/{m.seven_m[1]}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-muted">{t("xgNote")}</p>
      </section>
    </div>
  );
}

function Scorers({ scorers, names, topGoals, t }: { scorers: Season["players"]; names: Record<string, string>; topGoals: number; t: (k: string, p?: Record<string, string | number>) => string }) {
  return (
    <section className="space-y-3">
      <h2 className="text-2xl">{t("scorers")}</h2>
      <ol className="divide-y divide-foreground/10 border-y border-foreground/15" data-testid="season-players">
        {scorers.map((p, i) => (
          <li key={p.player_id} className="grid grid-cols-[1.5rem_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1.5 py-3">
            <span className="font-score text-lg text-muted">{i + 1}</span>
            <span className="min-w-0">
              <span className="block truncate font-semibold">{names[p.player_id] ?? t("unknownPlayer")}</span>
              <span className="block text-sm text-muted">
                {t("goalsOfShots", { goals: p.goals, shots: p.shots })} · {t("inMatches", { n: p.matches })}
              </span>
            </span>
            <span className="text-right">
              <span className="block font-score text-2xl leading-none">{p.goals}</span>
              <span className="block text-sm text-muted tabular-nums">{pct(p.shooting_pct)}</span>
            </span>
            <span aria-hidden className="col-start-2 col-end-4 h-1.5 overflow-hidden rounded-[2px] bg-foreground/10">
              <span className="block h-full bg-accent" style={{ width: `${(p.goals / topGoals) * 100}%` }} />
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

/** A figure on a fixed scale with a tick for its reference; yellow when it needs work. */
function StatBar({ share, tick, focus }: { share: number | null; tick: number; focus?: boolean }) {
  const clamp = (v: number) => `${Math.max(0, Math.min(1, v)) * 100}%`;
  return (
    <span aria-hidden className="relative col-span-2 block h-2.5 rounded-[2px] bg-foreground/10 sm:col-span-1">
      {share != null && <span className={cn("absolute inset-y-0 left-0 rounded-[2px]", focus ? "bg-resin ring-1 ring-inset ring-foreground/25" : "bg-accent")} style={{ width: clamp(share) }} />}
      <span className="absolute -top-1.5 -bottom-1.5 w-0.5 -translate-x-1/2 bg-foreground" style={{ left: clamp(tick) }} />
    </span>
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
      <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={label} className="max-h-64 w-full" data-testid="season-trend">
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
