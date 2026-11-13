"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useFormatter, useTranslations } from "next-intl";
import type { ComponentProps, CSSProperties, ReactNode } from "react";
import { AttnTag, linkClass, SectionHead } from "@/components/anlauf/blocks";
import { Bundle, EmptyField } from "@/components/anlauf/bundle";
import { WurfHead } from "@/components/anlauf/heads";
import { ThreeThingsView, useThingText } from "@/components/anlauf/three-things-view";
import { FromMatchButton } from "@/components/collections/from-match";
import { useShell } from "@/components/shell/context";
import { buttonClass } from "@/components/ui/button";
import { api } from "@/lib/client";
import { ownName } from "@/lib/own-name";
import { TeamFacts, useStanding } from "@/app/(einstieg)/einstieg/entry-view";
import { matchStyle } from "@/lib/color";
import { goalRuns, reportGoals, useMatchGraphics, type MatchGraphics } from "@/lib/graphics";
import { matchState } from "@/lib/match-state";
import { threeThings } from "@/lib/three-things";
import { cn } from "@/lib/utils";

type Match = Schemas["MatchSummary"];

const resultOf = (m: Match) => (m.score_own == null || m.score_opponent == null ? null : m.score_own > m.score_opponent ? "win" : m.score_own < m.score_opponent ? "loss" : "draw");

/** Spiele, the start (SPEC 7.1): the last match in the Wurf head, its three things, all matches. */
export function StartView({
  orgId,
  played,
  upcoming,
  canWrite,
  actions,
}: {
  orgId: string;
  played: Match[];
  upcoming: Match[];
  canWrite: boolean;
  actions?: ReactNode;
}) {
  const t = useTranslations("anlauf");
  // the team's name in the head, the same as in the top bar (UX test H11: one club, one name)
  const { org, team } = useShell();
  const last = played.find((m) => m.kind !== "training" && m.score_own != null) ?? played[0] ?? null;
  const next = upcoming.find((m) => m.kind !== "training") ?? null;
  const withoutVideo = played.filter((m) => !m.has_video).length;
  return (
    <div className="space-y-8">
      <LastMatch orgId={orgId} m={last} next={next} teamName={ownName(team?.name, org.name)} canWrite={canWrite} club={[org.primary_color, org.secondary_color ?? null]} />
      <div className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_340px]">
        <section aria-labelledby="all-matches">
          <SectionHead
            title={<span id="all-matches">{t("allMatches")}</span>}
            note={withoutVideo > 0 ? t("withoutVideo", { count: withoutVideo, total: played.length }) : undefined}
          />
          {/* a new match and a report are not actions on the last match: they belong to the list */}
          {actions && <div className="-mt-1 mb-2 flex flex-wrap items-center gap-3">{actions}</div>}
          <ul className="m-0 list-none p-0" data-testid="match-list">
            {played.map((m) => (
              <li key={m.id}>
                <GameRow orgId={orgId} m={m} canWrite={canWrite} />
              </li>
            ))}
          </ul>
        </section>
        <aside className="flex min-w-0 flex-col gap-8">{next && <NextOpponent orgId={orgId} teamId={team?.id} next={next} played={played} />}</aside>
      </div>
    </div>
  );
}

function LastMatch({ orgId, m, next, teamName, canWrite, club }: { orgId: string; m: Match | null; next: Match | null; teamName: string; canWrite: boolean; club: [string, string | null] }) {
  const t = useTranslations("anlauf");
  const g = useMatchGraphics(orgId, m?.id ?? "");
  const head = useHeadProps(m, next, g.data ?? null, teamName);
  const checks = g.data?.checks.length ?? 0;
  const base = m ? `/app/${orgId}/matches/${m.id}` : null;
  const running = m ? ["matches.status_processing", "matches.status_uploading"].includes(matchState(m).label) : false;
  // the analysis is done without three things: one sentence and one next step, nothing else that
  // says the same (UX test A02)
  const quiet = Boolean(m?.has_video && g.data && !running && threeThings(goalRuns(g.data)).length === 0);
  const scenes = g.data ? g.data.goals.filter((x) => x.has_video || x.source === "demo").length : 0;
  return (
    <div style={matchStyle(club, m?.opponent_color ? [m.opponent_color] : null) as CSSProperties} className="space-y-6">
      {/* no match played yet: the head waits (ink outline, no club area) and says what comes */}
      <div className="bleed-x -mt-6 lg:-mt-8">
        <WurfHead {...head} />
      </div>
      <div className="flex flex-wrap items-center gap-3">
        {/* the last match without video: the task is the video, the demo shows what comes (UX test B26) */}
        {m && base && canWrite && !m.has_video ? (
          <>
            <Link href={`${base}?tab=video#upload`} className={buttonClass("primary")} data-testid="start-upload">
              {t("uploadVideo")}
            </Link>
            <DemoButton orgId={orgId} teamId={m.team_id} />
            <Link href={base} className={linkClass} data-testid="open-match">
              {t("openMatch")}
            </Link>
          </>
        ) : (
          m &&
          base &&
          !quiet && (
            <Link href={base} className={buttonClass("primary")} data-testid="open-match">
              {t("openMatch")}
            </Link>
          )
        )}
        {/* a collection needs scenes: none, no button (UX test A02) */}
        {m && canWrite && m.has_video && !quiet && scenes > 0 && <FromMatchButton orgId={orgId} teamId={m.team_id} matchId={m.id} opponent={m.opponent_name} />}
        {canWrite && checks > 0 && base && !quiet && (
          <span className="flex items-center gap-2.5">
            <AttnTag>{t("check")}</AttnTag>
            <Link href={`${base}/check`} className={linkClass}>
              {/* after the court come the people in the picture: say so instead of «1 Minute» (UX test N13) */}
              {g.data?.checks.some((c) => c.kind === "field") ? t("checksThenPeople", { count: checks }) : t("checksOpen", { count: checks, minutes: Math.max(1, Math.round(checks / 3)) })}
            </Link>
          </span>
        )}
      </div>
      {/* before the first video: what the federation's data already says (UX test H02) */}
      {!m?.has_video && m && <FromReport orgId={orgId} teamId={m.team_id} hideNext={next != null} />}
      {/* the analysis is done without three things: say so and name the next step (UX test N05) */}
      {quiet && m && g.data && base && (
        <section className="max-w-[60ch] space-y-3 border-l-4 border-attn pl-4" data-testid="start-next-step">
          <p className="m-0 text-[19px] font-bold">{checks > 0 ? t("nextStepChecks", { n: checks }) : g.data.report_goals.length === 0 ? t("nextStepReport") : t("nextStepNoGoals")}</p>
          <div className="flex flex-wrap items-center gap-4">
            {canWrite && checks > 0 ? (
              <Link href={`${base}/check`} className={buttonClass("primary")} data-testid="start-step">
                {t("plainToCheck")}
              </Link>
            ) : canWrite && g.data.report_goals.length === 0 ? (
              <Link href={`/app/${orgId}/teams/${m.team_id}/matches?report=1`} className={buttonClass("primary")} data-testid="start-step">
                {t("nextStepAddReport")}
              </Link>
            ) : (
              <Link href={base} className={buttonClass("primary")} data-testid="start-step">
                {t("openMatch")}
              </Link>
            )}
            {/* the match stays one tap away, as a plain link beside the step */}
            {(checks > 0 || g.data.report_goals.length === 0) && canWrite && (
              <Link href={base} className={linkClass} data-testid="open-match">
                {t("openMatch")}
              </Link>
            )}
          </div>
        </section>
      )}
      {m?.has_video && g.data && base && !quiet && <ThreeThingsView orgId={orgId} matchId={m.id} graphics={g.data} oppName={m.opponent_name} hrefScenes={(_, n) => `${base}?tab=video&thing=${n}`} />}
    </div>
  );
}

/** Rank, form, table excerpt, scorers and next game from handball.ch for a linked team. */
function FromReport({ orgId, teamId, hideNext }: { orgId: string; teamId: string; hideNext: boolean }) {
  const t = useTranslations("entry");
  const link = useQuery({
    queryKey: ["official", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/official", { params: { path: { org_id: orgId, team_id: teamId } } })).data ?? null,
  });
  const club = link.data?.official_club_id;
  const team = link.data?.official_team_id;
  const preview = useQuery({
    queryKey: ["public-team", club, team],
    enabled: Boolean(club && team),
    retry: false,
    staleTime: 3_600_000,
    queryFn: async () => (await api.GET("/v1/public/clubs/{club_id}/teams/{official_id}", { params: { path: { club_id: club!, official_id: team! } } })).data ?? null,
  });
  const standing = useStanding(preview.data);
  if (!preview.data) return null;
  return (
    <section className="space-y-6" data-testid="start-from-report">
      {standing && <p className="font-slant m-0 text-[28px] leading-tight md:text-[34px]">{standing}</p>}
      {/* the next opponent stands once, at the side (UX test B40) */}
      <TeamFacts p={preview.data} hideNext={hideNext} />
      <p className="m-0 text-[15px] text-ink-2">{t("source")}</p>
    </section>
  );
}

/** «Demo-Spiel ansehen»: a seeded match of this team, opened at once. */
function DemoButton({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("anlauf");
  const router = useRouter();
  const demo = useMutation({
    mutationFn: async () => (await api.POST("/v1/orgs/{org_id}/teams/{team_id}/demo-match", { params: { path: { org_id: orgId, team_id: teamId } } })).data,
    onSuccess: (d) => d && router.push(`/app/${orgId}/matches/${d.id}`),
  });
  return (
    <button type="button" className={buttonClass("secondary")} onClick={() => demo.mutate()} disabled={demo.isPending} data-testid="start-demo">
      {t("demoMatch")}
    </button>
  );
}

/** What the Wurf head of the start says: the last match by its state, or what comes. */
function useHeadProps(m: Match | null, next: Match | null, g: MatchGraphics | null, teamName: string): ComponentProps<typeof WurfHead> {
  const t = useTranslations("anlauf");
  const format = useFormatter();
  if (!m) {
    return { title: next ? t("titleNext", { opponent: next.opponent_name }) : t("titleWelcome"), own: null, opp: null, ownName: teamName, oppName: next?.opponent_name ?? "", waiting: true };
  }
  const state = matchState(m);
  const running = ["matches.status_processing", "matches.status_uploading"].includes(state.label);
  const things = g ? threeThings(goalRuns(g)) : [];
  const result = resultOf(m);
  const title = running
    ? t("titleRunning")
    : !m.has_video
      ? t("titleNoVideo")
      : `${t(result === "win" ? "titleWon" : result === "loss" ? "titleLost" : "titleDraw")}${things.length ? ` ${t("titleThings", { count: things.length })}` : ""}`;
  return {
    kick: t("kickVs", { when: format.dateTime(new Date(m.kickoff_at), { weekday: "long" }), opponent: m.opponent_name }),
    title,
    own: m.score_own,
    opp: m.score_opponent,
    ownName: teamName,
    oppName: m.opponent_name,
    goals: g ? reportGoals(g) : null,
    flightLabels: { half: t("halftime", { v: "{v}" }), end: t("end", { v: "{v}" }), halfLevel: t("halftimeLevel"), endLevel: t("endLevel") },
  };
}

/** The Minifeld of a row: the bundle of the match's first thing, or the empty field with its word. */
function MiniField({ orgId, m, width = 128 }: { orgId: string; m: Match; width?: number }) {
  const t = useTranslations("anlauf");
  const text = useThingText();
  const state = matchState(m);
  const running = ["matches.status_processing", "matches.status_uploading"].includes(state.label);
  const g = useMatchGraphics(orgId, m.has_video && !running ? m.id : "");
  const first = g.data ? threeThings(goalRuns(g.data))[0] : undefined;
  if (first) {
    return (
      <span className="block w-full" style={{ maxWidth: width }}>
        <Bundle goals={first.goals} rest={first.rest} width={width} label={text(first)} />
      </span>
    );
  }
  const word = running ? t("miniRunning") : !m.has_video ? t("miniNoVideo") : null;
  return (
    <span className="relative block w-full" style={{ maxWidth: width }}>
      <EmptyField />
      {word && <em className="absolute top-[52%] left-1/2 -translate-x-1/2 -translate-y-1/2 bg-ground px-1.5 py-0.5 text-center text-xs leading-tight font-semibold whitespace-nowrap text-ink not-italic">{word}</em>}
    </span>
  );
}

/** The second line of a match with video: its things, its scenes and Punkt 1. */
function RowSummary({ orgId, m }: { orgId: string; m: Match }) {
  const t = useTranslations("anlauf");
  const text = useThingText();
  const g = useMatchGraphics(orgId, m.id);
  if (!g.data) return <>{m.competition}</>;
  const things = threeThings(goalRuns(g.data));
  const scenes = g.data.goals.filter((x) => x.has_video || x.source === "demo").length;
  // no things yet: the state in words, not «Kein Ding · 0 Szenen» (UX test A02)
  if (things.length === 0) return <>{g.data.checks.length > 0 ? t("rowChecks", { n: g.data.checks.length }) : t("rowNoGoals")}</>;
  return <>{t("rowSummary", { things: things.length, scenes, first: things[0] ? text(things[0]) : "none" })}</>;
}

function GameRow({ orgId, m, canWrite }: { orgId: string; m: Match; canWrite: boolean }) {
  const t = useTranslations("anlauf");
  const tm = useTranslations("matches");
  const format = useFormatter();
  const date = new Date(m.kickoff_at);
  const result = resultOf(m);
  const state = matchState(m);
  const base = `/app/${orgId}/matches/${m.id}`;
  return (
    <div className="grid grid-cols-[84px_minmax(0,1fr)_auto] items-center gap-3 border-b border-rule py-3 md:grid-cols-[64px_128px_minmax(0,1fr)_auto] md:gap-5">
      <p className="m-0 text-[15px] leading-tight text-ink-2 max-md:hidden">
        {format.dateTime(date, { weekday: "short" })}
        <b className="font-num block text-xl text-ink">{format.dateTime(date, { day: "2-digit", month: "2-digit" })}</b>
        {m.is_home ? t("home") : t("away")}
      </p>
      <Link href={base} aria-hidden tabIndex={-1} className="block w-[84px] md:w-32">
        <MiniField orgId={orgId} m={m} width={128} />
      </Link>
      <div className="min-w-0">
        <h3 className="m-0">
          <Link href={base} className="font-slant text-[17px] leading-tight text-ink no-underline hover:underline md:text-[22px]">
            {m.kind === "training" ? tm("training") : m.opponent_name}
          </Link>
        </h3>
        <p className="m-0 text-[15px] text-ink-2 md:text-[15px]">
          <span className="md:hidden">{format.dateTime(date, { day: "2-digit", month: "2-digit" })} · </span>
          {["matches.status_processing", "matches.status_uploading", "matches.status_failed"].includes(state.label) ? (
            tm(state.label.replace("matches.", "") as "status_processing")
          ) : !m.has_video ? (
            <>
              {t("reportOnly")}
              {canWrite && m.score_own != null && (
                <>
                  {" · "}
                  <Link href={`${base}?tab=video`} className={cn(linkClass, "inline-flex min-h-11 items-center")}>
                    {t("uploadVideo")}
                  </Link>
                </>
              )}
            </>
          ) : (
            <RowSummary orgId={orgId} m={m} />
          )}
        </p>
      </div>
      {result ? (
        <p className="m-0 text-right">
          <span className="sr-only">{`${t("scoreLabel", { own: m.score_own ?? 0, opp: m.score_opponent ?? 0 })}, ${t(result)}`}</span>
          <b className="font-num block text-[28px] leading-[.85] md:text-[44px]" aria-hidden>
            {m.score_own}:{m.score_opponent}
          </b>
          <small aria-hidden className={cn("mt-1 block text-[15px] font-bold md:mt-1.5 md:text-sm", result === "win" ? "text-win" : result === "loss" ? "text-loss" : "text-ink-2")}>
            {/* «draw» is also the drawing tool: the result has its own word (UX test B50) */}
            {t(result === "draw" ? "drawResult" : result)}
          </small>
        </p>
      ) : (
        <span />
      )}
    </div>
  );
}

type Row = { teamId?: number; name?: string; rank?: number; games?: number; won?: number; drawn?: number; lost?: number; goalsFor?: number; goalsAgainst?: number; goalDifference?: number; points?: number };
const fold = (v: string) => v.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]/g, "");

/**
 * Nächster Gegner (SPEC 7.1, UX test B40): three facts from the federation's table and our own
 * last duel, the table underneath. Without a table and without a duel there is nothing to say:
 * then only the name and the date, no empty field.
 */
export function NextOpponent({ orgId, teamId, next, played }: { orgId: string; teamId?: string; next: Match; played: Match[] }) {
  const t = useTranslations("anlauf");
  const format = useFormatter();
  const date = new Date(next.kickoff_at);
  // the last duel with video: its Minifeld and a line
  const met = played.find((m) => m.opponent_name === next.opponent_name && m.score_own != null && m.has_video);
  const duel = played.find((m) => m.opponent_name === next.opponent_name && m.score_own != null);
  const g = useMatchGraphics(orgId, met?.id ?? "");
  const text = useThingText();
  const first = g.data ? threeThings(goalRuns(g.data))[0] : undefined;
  const link = useQuery({
    queryKey: ["official", teamId],
    enabled: Boolean(teamId),
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/official", { params: { path: { org_id: orgId, team_id: teamId! } } })).data ?? null,
  });
  const table = (link.data?.standing ?? []) as Row[];
  const ownId = link.data?.official_team_id;
  const opp = next.opponent_name ? fold(next.opponent_name) : "";
  const row = opp ? table.find((r) => r.name && (fold(r.name) === opp || fold(r.name).includes(opp) || opp.includes(fold(r.name)))) : undefined;
  const facts: string[] = [];
  if (row?.rank != null && row.points != null && row.games != null) facts.push(t("oppRank", { rank: row.rank, points: row.points, games: row.games }));
  if (row?.won != null && row.drawn != null && row.lost != null) facts.push(t("oppRecord", { won: row.won, drawn: row.drawn, lost: row.lost }));
  if (row?.goalsFor != null && row.goalsAgainst != null && row.games) facts.push(t("oppGoals", { scored: Math.round(row.goalsFor / row.games), conceded: Math.round(row.goalsAgainst / row.games) }));
  if (duel) facts.push(t("lastMeeting", { score: `${duel.score_own}:${duel.score_opponent}` }) + (met && first ? `, ${text(first)}` : ""));
  // the table around both teams: at most six rows, own and opponent marked
  const marked = (r: Row) => (ownId != null && r.teamId === ownId) || r === row;
  const around = table.length <= 6 ? table : table.filter((r, i) => table.slice(Math.max(0, i - 1), i + 2).some(marked)).slice(0, 6);
  return (
    <section data-testid="next-opponent">
      <p className="m-0 text-[15px] font-semibold text-ink-2">
        {t("nextOpponent")} · {format.dateTime(date, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
      </p>
      <h3 className="mt-1 mb-3 text-[30px] leading-[.95] md:text-4xl">
        <Link href={`/app/${orgId}/matches/${next.id}`} className="font-slant text-ink no-underline hover:underline">
          {next.is_home ? next.opponent_name : `${t("away")} ${next.opponent_name}`}
        </Link>
      </h3>
      {met && (
        <Link href={`/app/${orgId}/matches/${met.id}`} aria-hidden tabIndex={-1} className="mb-2 block">
          <MiniField orgId={orgId} m={met} width={340} />
        </Link>
      )}
      {facts.length > 0 ? (
        <ul className="m-0 list-none p-0" data-testid="next-facts">
          {facts.slice(0, 3).map((f) => (
            <li key={f} className="border-t border-rule py-2.5 text-base">
              {f}
            </li>
          ))}
        </ul>
      ) : (
        <p className="m-0 border-t border-rule py-2.5 text-base text-ink-2">{t("noVideoAgainst", { opponent: next.opponent_name })}</p>
      )}
      {around.length > 0 && (
        <table className="mt-4 w-full border-collapse text-[15px]" data-testid="next-table">
          <caption className="mb-1 text-left text-[15px] font-semibold text-ink-2">{link.data?.league || link.data?.group_name || t("table")}</caption>
          <thead className="sr-only">
            <tr>
              <th scope="col">{t("tableRank")}</th>
              <th scope="col">{t("tableTeam")}</th>
              <th scope="col">{t("tableGames")}</th>
              <th scope="col">{t("tablePoints")}</th>
            </tr>
          </thead>
          <tbody>
            {around.map((r) => (
              <tr key={`${r.rank}-${r.name}`} className={cn("border-t border-rule", marked(r) && "font-bold")}>
                <td className="w-8 py-2 tabular-nums">{r.rank}</td>
                <td className="py-2">{r.name}</td>
                <td className="py-2 text-right text-ink-2 tabular-nums">{r.games}</td>
                <td className="w-10 py-2 text-right tabular-nums">{r.points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
