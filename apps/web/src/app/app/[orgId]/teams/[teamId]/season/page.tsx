import type { Metadata } from "next";
import Link from "next/link";
import { getFormatter, getTranslations } from "next-intl/server";
import { PlanHint } from "@/components/billing/plan-hint";
import { serverApi } from "@/lib/api";
import { linkClass, OwnRowMark, SectionHead } from "@/components/anlauf/blocks";
import { Bundle, type GoalRun } from "@/components/anlauf/bundle";
import { DiffBars, Series } from "@/components/anlauf/charts";
import { goalRuns } from "@/lib/graphics";
import { uploadHref } from "@/lib/nav-model";
import { seasonRepeats, shortName, type SeasonMatch } from "@/lib/season-repeats";
import { buttonClass } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { AreaSubNav } from "@/components/shell/section-nav";
import { SeasonThemes } from "@/components/season/season-themes";
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
  xg_coverage: number | null;
  xg_against: number;
  /** share of the opponent's shots on target with a position; xG against only with enough of them */
  xg_against_coverage?: number | null;
  seven_m: [number, number];
}
interface Season {
  matches: Row[];
  totals: { matches: number; goals: number; shots: number; turnovers: number; xg: number; xg_shots: number; xg_coverage: number | null; shooting_pct: number | null; save_pct: number | null };
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
  const ts = await getTranslations("seasonPage");
  const ta = await getTranslations("anlauf");
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
      <Link href={`${base}/matrix`} className={buttonClass("secondary")}>
        {tp("matrix")}
      </Link>
      <Link href={`${base}/assistant`} className={linkClass}>
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
        <PageHeader eyebrow={label} title={tv("noMatchYet")} actions={tools} />
        <p className="max-w-lg text-[17px] text-ink-2">{t("none")}</p>
      </div>
    );
  }
  const [roster, official, matches] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster", { params: { path: { org_id: orgId, team_id: teamId, season_id: seasonId } } }),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/official", { params: { path: { org_id: orgId, team_id: teamId } } }),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", { params: { path: { org_id: orgId, team_id: teamId } } }),
  ]);
  const names = Object.fromEntries((roster.data ?? []).map((r) => [r.player_id, `${r.first_name} ${r.last_name}`]));
  const shirts = Object.fromEntries((roster.data ?? []).map((r) => [r.player_id, r.jersey_number]));
  const n = data.totals.matches;
  const statement = seasonStatement(data.matches, data.totals.xg_coverage, false) // no xG statements (UX test B07);
  const last = [...data.matches].sort((x, y) => y.kickoff_at.localeCompare(x.kickoff_at))[0]!;
  const lastResult = matchStatement({ own: last.score_own, opp: last.score_opponent, opponent: last.opponent });
  const focus = focusMetric({ save_pct: data.totals.save_pct, shooting_pct: data.totals.shooting_pct, turnovers_per_match: data.totals.turnovers / n });
  // columns that are zero in every match are left out (no 7 m recorded yet)
  const sevenM = data.matches.some((m) => m.seven_m[1] > 0);
  const goalsFor = data.totals.goals / n;
  const goalsAgainst = data.matches.reduce((sum, m) => sum + m.score_opponent, 0) / n;
  const turnovers = data.totals.turnovers / n;
  // one row per figure: value, a bar on a fixed scale and a tick for the reference (or goals against)
  const cells: { key: string; label: string; value: string; href: string; share: number | null; tick: number; refText: string; focus?: boolean }[] = [
    { key: "goals", label: `${t("goals")} ${t("perMatch")}`, value: goalsFor.toFixed(1), href: `${base}/scenes?type=shot&outcome=goal&side=own`, share: goalsFor / 40, tick: goalsAgainst / 40, refText: tv("againstRef", { value: goalsAgainst.toFixed(1) }) },
    { key: "shooting", label: t("shootingPct"), value: pct(data.totals.shooting_pct), href: `${base}/scenes?type=shot&side=own`, share: data.totals.shooting_pct, tick: 0.55, refText: tv("reference", { value: "55 %" }), focus: focus === "shooting_pct" },
    { key: "save", label: t("savePct"), value: pct(data.totals.save_pct), href: `${base}/scenes?type=shot&outcome=save&side=opponent`, share: data.totals.save_pct, tick: 0.3, refText: tv("reference", { value: "30 %" }), focus: focus === "save_pct" },
    { key: "turnovers", label: `${t("turnovers")} ${t("perMatch")}`, value: turnovers.toFixed(1), href: `${base}/scenes?type=turnover&side=own`, share: turnovers / 24, tick: 0.5, refText: `${tv("reference", { value: "12" })}, ${tv("lowerBetter")}`, focus: focus === "turnovers" },
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
  const wins = data.matches.filter((m) => m.score_own > m.score_opponent).length;
  const draws = data.matches.filter((m) => m.score_own === m.score_opponent).length;
  const losses = n - wins - draws;
  // what repeats over the matches with video (SPEC 7.9): from the measured goals of each match
  const chrono = [...data.matches].sort((x, y) => x.kickoff_at.localeCompare(y.kickoff_at));
  const graphics = await Promise.all(
    chrono.map(async (m) => ({ m, g: (await client.GET("/v1/orgs/{org_id}/matches/{match_id}/graphics", { params: { path: { org_id: orgId, match_id: m.match_id } } })).data ?? null })),
  );
  const withVideo: SeasonMatch<GoalRun & { eventId: string }>[] = graphics
    .filter(({ g }) => g && g.goals.some((x) => x.has_video || x.source === "demo"))
    .map(({ m, g }) => ({ id: m.match_id, label: shortName(m.opponent), goals: goalRuns(g!), turnovers: m.turnovers }));
  const rep = seasonRepeats(withVideo);
  const main = rep.conceded;
  // the table from the official data (handball.ch) when the team is linked; without it no rank
  const standing = (official.data?.linked ? (official.data.standing ?? []) : []) as { teamId?: number; name?: string; rank?: number; games?: number; goalDifference?: number; points?: number }[];
  const ours = standing.find((r) => r.teamId != null && r.teamId === (official.data?.official_team_id ?? team.data?.official_team_id));
  const zoneNoun = main ? ts(`zoneNoun.${main.zone}` as "zoneNoun.ra") : null;
  const title = zoneNoun
    ? ours?.rank
      ? ts("titleRank", { rank: ours.rank, zone: zoneNoun })
      : ts("titleCount", { n, zone: zoneNoun })
    : statement
      ? tv(statement.headline.key.replace("voice.", "") as "overXg", statement.headline.params as never)
      : lastResult
        ? tv(lastResult.headline.key.replace("voice.", "") as "won", lastResult.headline.params as never)
        : tv("neutralSeason");
  const league = official.data?.linked ? official.data.league || official.data.group_name || "" : (team.data?.league ?? "");
  const season = `${t("title")} ${team.data?.current_season?.label ?? ""}`.trim();
  const kickBase = league ? ts("kick", { season, league, n }) : ts("kickNoLeague", { season, n });
  // the rank always stands in the head when the table is known (UX test B41), in the title or here
  const kick = ours?.rank && !(zoneNoun && ours.rank) ? `${kickBase} · ${ts("rankKick", { rank: ours.rank, points: ours.points ?? 0 })}` : kickBase;
  const goalsAgainstTotal = data.matches.reduce((sum, m) => sum + m.score_opponent, 0);
  const goalsForTotal = data.matches.reduce((sum, m) => sum + m.score_own, 0);
  const noVideo = data.matches.length - withVideo.length;
  const upload = uploadHref(orgId, teamId);
  const fixtures = ((matches.data ?? []) as { id: string; kickoff_at: string; opponent_name: string | null; status: string; score_own: number | null; score_opponent: number | null }[])
    .filter((m) => m.opponent_name && new Date(m.kickoff_at) > new Date())
    .sort((x, y) => x.kickoff_at.localeCompare(y.kickoff_at))
    .slice(0, 3);
  const top = [...data.players].filter((p) => p.goals > 0).sort((a, b) => b.goals - a.goals).slice(0, 5);
  const scenesHref = (chips: string[]) => `${base}/scenes?chips=${chips.join(",")}`;
  const ZONE_CHIP: Record<string, string> = { ra: "wing_right", la: "wing_left", rl: "back_left", rm: "back_centre", rr: "back_right", kr: "circle" };
  const rows: { key: string; title: string; text: string; series: number[]; team: "own" | "opp"; count: number; href: string | null }[] = [];
  if (rep.conceded) {
    const c = rep.conceded;
    rows.push({ key: "conceded", title: ta("thing_conceded_zone", { zone: ta(`zoneFrom.${c.zone}` as "zoneFrom.ra") }), text: c.everyMatch ? ts("everyMatch", { n: c.value, of: c.of }) : ts("ofAll", { n: c.value, of: c.of }), series: c.series, team: "opp", count: c.value, href: scenesHref(["conceded", ...(ZONE_CHIP[c.zone] ? [ZONE_CHIP[c.zone]!] : [])]) });
  }
  if (rep.turnovers) {
    const tt = rep.turnovers;
    rows.push({ key: "turnovers", title: ts("turnovers"), text: tt.outlier != null ? ts("turnoverOutlier", { opp: withVideo[tt.outlier]!.label, median: tt.median }) : ts("turnoverAround", { median: tt.median }), series: tt.series, team: "own", count: tt.total, href: null }); // from the report: no scenes behind them (ANLAUF 10, UX test B41)
  }
  if (rep.scored) {
    const c = rep.scored;
    rows.push({ key: "scored", title: ta("thing_scored_zone", { zone: ta(`zoneFrom.${c.zone}` as "zoneFrom.ra") }), text: c.rising ? ts("rising", { first: c.series[0]!, last: c.series[c.series.length - 1]!, k: c.series.length, n: c.value, of: c.of }) : ts("ofAll", { n: c.value, of: c.of }), series: c.series, team: "own", count: c.value, href: scenesHref(["scored", ...(ZONE_CHIP[c.zone] ? [ZONE_CHIP[c.zone]!] : [])]) });
  }

  return (
    <div>
      <AreaSubNav />
      <PageHeader eyebrow={kick} title={title} />
      {/* the record in words for screen readers and the flows; the figure above is its short form */}
      <dl className="sr-only" data-testid="season-record">
        {([["won", wins], ["draw", draws], ["lost", losses]] as const).map(([k, v]) => (
          <div key={k}>
            <dt>{tm(k)}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>

      <div className="grid gap-x-12 gap-y-14 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-14">
          <section data-testid="season-repeats">
            <SectionHead title={ts("repeats")} note={ts("repeatsBase", { n: withVideo.length })} />
            {rows.length === 0 ? (
              <p className="text-[17px] text-ink-2">{ts("repeatsNone")}</p>
            ) : (
              <ul className="m-0 list-none p-0">
                {rows.map((r) => (
                  <li key={r.key} className="flex flex-wrap items-end justify-between gap-x-8 gap-y-3 border-t border-rule py-5 first:border-t-0">
                    <div className="min-w-0 flex-1">
                      <h3 className="font-slant text-[22px] leading-tight md:text-2xl">{r.title}</h3>
                      <p className="mt-1 text-[17px] text-ink-2">{r.text}</p>
                      {r.href ? (
                        <Link href={r.href} className={cn(linkClass, "mt-2 inline-flex min-h-11 items-center text-[15px]")}>
                          {ta("scenes", { count: r.count })}
                        </Link>
                      ) : (
                        <p className="mt-2 text-[15px] text-ink-2">{ta("fromReport")}</p>
                      )}
                    </div>
                    <figure className="m-0">
                      <Series values={r.series} team={r.team} label={ts("seriesLabel", { what: r.title, values: withVideo.map((m, i) => `${m.label} ${r.series[i]}`).join(", ") })} />
                      <figcaption aria-hidden className="flex w-[132px] justify-between text-[14px] text-ink-2">
                        {withVideo.map((m) => (
                          <span key={m.id} className="truncate">
                            {m.label}
                          </span>
                        ))}
                      </figcaption>
                    </figure>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <SectionHead title={ts("trend")} note={ts("trendNote")} />
            {/* phones: the last six matches at a readable size */}
            <div className="sm:hidden">
              <DiffBars matches={chrono.slice(-6).map((m) => ({ label: shortName(m.opponent), diff: m.score_own - m.score_opponent }))} width={400} label={t("chartLabel")} />
            </div>
            <div className="max-sm:hidden">
              <DiffBars matches={chrono.slice(-10).map((m) => ({ label: shortName(m.opponent), diff: m.score_own - m.score_opponent }))} label={t("chartLabel")} />
            </div>
            <p className="mt-3 text-[15px] text-ink-2" data-testid="season-summary">
              {draws > 0 ? ts("recordDraws", { w: wins, d: draws, l: losses }) : ts("record", { w: wins, l: losses })} · {ts("goalsFor", { gf: goalsForTotal, ga: goalsAgainstTotal })}
              {noVideo > 0 && staff && upload && (
                <>
                  {" "}
                  {ts("noVideo", { n: noVideo })}{" "}
                  <Link href={upload} className={linkClass}>
                    {ts("upload")}
                  </Link>
                </>
              )}
            </p>
          </section>

          {top.length > 0 && (
            <section>
              <SectionHead title={ts("scorers")} note={ts("scorersNote", { n })} />
              <table className="w-full border-collapse text-[17px]" data-testid="season-players">
                <thead>
                  <tr className="border-b-2 border-ink text-left text-[15px] text-ink-2">
                    <th scope="col" className="py-2 font-semibold">{ts("colNumberName")}</th>
                    <th scope="col" className="py-2 text-right font-semibold max-sm:hidden">{ts("colMatches")}</th>
                    <th scope="col" className="py-2 text-right font-semibold">{ts("colGoals")}</th>
                    <th scope="col" className="py-2 text-right font-semibold">{ts("colPerMatch")}</th>
                  </tr>
                </thead>
                <tbody>
                  {top.map((p) => (
                    <tr key={p.player_id} className="border-b border-rule">
                      <th scope="row" className="py-3 text-left font-normal">
                        <b className="font-num mr-3 inline-block w-8 text-xl text-club-text">{shirts[p.player_id] ?? ""}</b>
                        {staff ? (
                          <Link href={`${base}/players/${p.player_id}`} className="hover:underline hover:underline-offset-4">
                            {names[p.player_id] ?? t("unknownPlayer")}
                          </Link>
                        ) : (
                          (names[p.player_id] ?? t("unknownPlayer"))
                        )}
                      </th>
                      <td className="py-3 text-right tabular-nums max-sm:hidden">{p.matches}</td>
                      <td className="py-3 text-right tabular-nums">
                        <Link href={`${base}/scenes?chips=scored`} className="underline decoration-[1.5px] underline-offset-4">
                          {p.goals}
                        </Link>
                      </td>
                      <td className="py-3 text-right tabular-nums">{format.number(p.goals / Math.max(1, p.matches), { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-3">
                <Link href={base} className={cn(linkClass, "text-[15px]")}>
                  {ts("wholeSquad")}
                </Link>
              </p>
            </section>
          )}
        </div>

        <aside className="min-w-0 space-y-14">
          {main && (
            <section>
              <SectionHead title={ts(`zoneTitle.${main.zone}` as "zoneTitle.ra")} note={ts("runs", { n: main.value, k: withVideo.length })} />
              <Bundle goals={main.goals} rest={[]} width={340} label={ts("bundleLabel", { n: main.value, what: ta(`zoneFrom.${main.zone}` as "zoneFrom.ra") })} />
            </section>
          )}
          {standing.length > 0 && (
            <section>
              <SectionHead title={ts("table")} note={official.data?.synced_at ? ts("tableNote", { when: format.relativeTime(new Date(official.data.synced_at), new Date()) }) : undefined} />
              <table className="w-full border-collapse text-[15px]" data-testid="season-standing">
                <thead>
                  <tr className="text-left text-[15px] text-ink-2">
                    <th scope="col" className="py-2 font-semibold">{ts("colRank")}</th>
                    <th scope="col" className="py-2 text-right font-semibold">{ts("colGames")}</th>
                    <th scope="col" className="py-2 text-right font-semibold">{ts("colDiff")}</th>
                    <th scope="col" className="py-2 text-right font-semibold">{ts("colPoints")}</th>
                  </tr>
                </thead>
                <tbody>
                  {standing.map((r) => {
                    const me = r === ours;
                    return (
                      <tr key={`${r.rank}-${r.name}`} className={cn(me ? "border-y-2 border-ink font-bold" : "border-t border-rule")}>
                        <th scope="row" className="py-2.5 text-left font-[inherit]">
                          {me && <OwnRowMark />}
                          {r.rank} {r.name}
                        </th>
                        <td className="py-2.5 text-right tabular-nums">{r.games}</td>
                        <td className="py-2.5 text-right tabular-nums">{r.goalDifference != null && r.goalDifference > 0 ? `+${r.goalDifference}` : r.goalDifference}</td>
                        <td className="py-2.5 text-right tabular-nums">{r.points}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </section>
          )}
          <section>
            <SectionHead title={ts("opponents")} />
            {fixtures.length === 0 ? (
              <p className="text-[15px] text-ink-2">{ts("noFixtures")}</p>
            ) : (
              <ul className="m-0 list-none p-0" data-testid="season-opponents">
                {fixtures.map((f) => {
                  const before = [...data.matches].filter((m) => m.opponent === f.opponent_name).sort((x, y) => y.kickoff_at.localeCompare(x.kickoff_at))[0];
                  return (
                    <li key={f.id} className="flex min-h-11 items-center justify-between gap-3 border-t border-rule py-2.5 text-[15px] first:border-t-0">
                      <Link href={`/app/${orgId}/matches/${f.id}`} className="hover:underline hover:underline-offset-4">
                        {f.opponent_name}, {format.dateTime(new Date(f.kickoff_at), { weekday: "long" })}
                      </Link>
                      {before ? (
                        <Link href={`/app/${orgId}/matches/${before.match_id}`} className={cn(linkClass, "text-[15px]")}>
                          {ts("lastAgainst", { own: before.score_own, opp: before.score_opponent })}
                        </Link>
                      ) : (
                        <span className="text-[15px] text-ink-2">{ts("noMatchYet")}</span>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </aside>
      </div>

      {/* everything the season page showed before, one click away (nothing is lost) */}
      <details className="mt-16 border-t-2 border-ink pt-4" data-testid="season-more">
        <summary className="min-h-11 cursor-pointer content-center">
          <span className="font-slant text-[22px]">{ts("more")}</span> <span className="text-[15px] text-ink-2">{ts("moreNote")}</span>
        </summary>
        <div className="mt-8 space-y-12">
          {statement?.evidence && <p className="max-w-xl text-[17px] text-ink-2">{tv(statement.evidence.key.replace("voice.", "") as "record", statement.evidence.params as never)}</p>}
          <p className="flex flex-wrap items-center gap-3 text-[15px]">
            <Link href={`/app/${orgId}/matches/${last.match_id}`} className={linkClass}>
              {tv("lastResult")}: {last.score_own}:{last.score_opponent} {last.opponent}
            </Link>
            <Link href={`${base}/scenes?type=shot&outcome=goal&side=own`} className={buttonClass("secondary")}>
              {tv("goalsAsClips")}
            </Link>
            {tools}
          </p>
          <SeasonThemes orgId={orgId} teamId={teamId} seasonId={seasonId} names={names} />
      <div className="grid gap-12 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)] lg:gap-16">
            <section className="space-y-4">
              <SectionHead title={tv("inNumbers")} />
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
                          <span className="mt-0.5 mb-1.5 block w-fit bg-attn px-2 py-[3px] text-[15px] font-extrabold text-attn-ink">{tv("focus")}</span>
                        )}
                        <span className="block text-sm text-muted">{c.refText}</span>
                      </span>
                      <span className="text-right font-score text-[2.5rem] leading-none sm:text-left">{c.value}</span>
                      <StatBar share={c.share} tick={c.tick} focus={c.focus} />
                    </Link>
                  </li>
                ))}
              </ul>
              <p className="text-sm text-muted">{tv("focusNote")}{focus && ` ${tv("focusNoteMarked")}`}</p>
            </section>
    
            <div className="space-y-12">
              <section className="space-y-4">
                <SectionHead title={t("form")} note={t("formLast", { n: Math.min(10, n) })} />
                <DiffBars
                  matches={[...data.matches]
                    .sort((x, y) => x.kickoff_at.localeCompare(y.kickoff_at))
                    .slice(-10)
                    .map((m) => ({ label: m.opponent.split(/[\s-]/).filter((w) => w.length > 3)[0] ?? m.opponent, diff: m.score_own - m.score_opponent }))}
                  label={t("chartLabel")}
                />
              </section>
    
              {n > 1 && (
                <section className="space-y-4">
                  <SectionHead title={t("best")} />
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
            <section className="space-y-3">
              <h2 className="text-2xl">
                {t("trend")} <span className="font-sans text-base font-medium text-muted">{t("chartLabel")}</span>
              </h2>
              {(() => {
                const rows = [...data.matches].sort((x, y) => x.kickoff_at.localeCompare(y.kickoff_at));
                const day = (iso: string) => format.dateTime(new Date(iso), { day: "numeric", month: "numeric" });
                return (
                  <>
                    {/* phones: the last six matches at a readable size */}
                    <div className="sm:hidden">
                      <TrendChart rows={rows.slice(-6)} label={t("chartLabel")} day={day} width={420} />
                    </div>
                    <div className="hidden sm:block">
                      <TrendChart rows={rows} label={t("chartLabel")} day={day} />
                    </div>
                  </>
                );
              })()}
            </section>
          ) : (
            <p className="text-[0.9375rem] text-muted" data-testid="season-trend">
              {tv("chartLater")}
            </p>
          )}
          {scorers.length > 0 && <Scorers scorers={scorers} names={names} shirts={shirts} topGoals={topGoals} t={t} />}
      <section className="space-y-3">
            <SectionHead title={t("allMatches")} />
            <div className="sheet overflow-x-auto">
              <table className="w-full text-[0.9375rem]" data-testid="season-matches">
                <caption className="sr-only">{t("matches")}</caption>
                <thead>
                  <tr>
                    <th scope="col" className="sticky left-0 bg-background shadow-[inset_-1px_0_0_var(--border)] text-left">{t("match")}</th>
                    <th scope="col">{t("result")}</th>
                    <th scope="col">{t("shootingPct")}</th>
                    <th scope="col">{t("savePct")}</th>
                    <th scope="col">{t("turnovers")}</th>
                    {sevenM && <th scope="col">{t("sevenM")}</th>}
                  </tr>
                </thead>
                <tbody>
                  {data.matches.map((m) => (
                    <tr key={m.match_id}>
                      <th scope="row" className="sticky left-0 bg-background shadow-[inset_-1px_0_0_var(--border)] text-left font-medium">
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
                      {sevenM && (
                        <td>
                          {m.seven_m[0]}/{m.seven_m[1]}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
    
        </div>
      </details>
    </div>
  );
}

function Scorers({ scorers, names, shirts, topGoals, t }: { scorers: Season["players"]; names: Record<string, string>; shirts: Record<string, number | null | undefined>; topGoals: number; t: (k: string, p?: Record<string, string | number>) => string }) {
  return (
    <section className="space-y-3">
      <h2 className="text-2xl">{t("scorers")}</h2>
      <ol className="gap-x-12 border-y border-foreground/15 lg:columns-2 [&>li]:break-inside-avoid [&>li+li]:border-t [&>li+li]:border-foreground/10" data-testid="season-players">
        {scorers.map((p, i) => (
          <li key={p.player_id} className="grid grid-cols-[2.75rem_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1.5 py-3">
            <span className="text-center font-score text-[2rem] leading-none text-accent">
              <span className="sr-only">{shirts[p.player_id] != null ? "#" : `${i + 1}.`}</span>
              {shirts[p.player_id] ?? <span aria-hidden>{i + 1}</span>}
            </span>
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
            <span aria-hidden className="col-start-2 col-end-4 h-1.5 overflow-hidden bg-foreground/10">
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
    <span aria-hidden className="relative col-span-2 block h-2.5 bg-foreground/10 sm:col-span-1">
      {share != null && <span className={cn("absolute inset-y-0 left-0", focus ? "bg-ink" : "bg-ink/45")} style={{ width: clamp(share) }} />}
      <span className="absolute -top-1.5 -bottom-1.5 w-0.5 -translate-x-1/2 bg-foreground" style={{ left: clamp(tick) }} />
    </span>
  );
}

/** Goal difference per match as bars above (won) and below (lost) the line; values on hover. */
function TrendChart({ rows, label, day, width = 1100 }: { rows: Row[]; label: string; day: (iso: string) => string; width?: number }) {
  const w = width;
  const h = 240;
  const pad = { l: 8, r: 8, t: 22, b: 40 };
  const max = Math.max(5, ...rows.map((r) => Math.abs(r.score_own - r.score_opponent)));
  const mid = pad.t + (h - pad.t - pad.b) / 2;
  const half = (h - pad.t - pad.b) / 2;
  const slot = (w - pad.l - pad.r) / rows.length;
  const bw = Math.min(44, slot * 0.6);
  return (
    <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={label} className="h-auto w-full" data-testid="season-trend">
      {rows.map((r, i) => {
        const d = r.score_own - r.score_opponent;
        const bh = Math.max(3, (Math.abs(d) / max) * half);
        const x = pad.l + slot * i + (slot - bw) / 2;
        const y = d >= 0 ? mid - bh : mid;
        const fill = d > 0 ? "var(--ok)" : d < 0 ? "var(--error)" : "var(--muted)";
        return (
          <g key={r.match_id}>
            <title>{`${r.opponent} ${r.score_own}:${r.score_opponent}`}</title>
            <rect x={x} y={y} width={bw} height={bh} rx={2} fill={fill} />
            <text x={x + bw / 2} y={d >= 0 ? y - 6 : y + bh + 14} fontSize="14" fontWeight={700} textAnchor="middle" fill="var(--foreground)">
              {d > 0 ? `+${d}` : d}
            </text>
            <text x={x + bw / 2} y={h - 8} fontSize="14" textAnchor="middle" fill="var(--muted)">
              {day(r.kickoff_at)}
            </text>
          </g>
        );
      })}
      <line x1={pad.l} x2={w - pad.r} y1={mid} y2={mid} stroke="var(--foreground)" strokeWidth={1.5} />
    </svg>
  );
}
