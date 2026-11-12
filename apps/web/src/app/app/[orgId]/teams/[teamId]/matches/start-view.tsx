"use client";

import type { Schemas } from "@handball/api-client";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import type { ComponentProps, CSSProperties, ReactNode } from "react";
import { AttnTag, linkClass, SectionHead } from "@/components/anlauf/blocks";
import { Bundle, EmptyField } from "@/components/anlauf/bundle";
import { WurfHead } from "@/components/anlauf/heads";
import { ThreeThingsView, useThingText } from "@/components/anlauf/three-things-view";
import { FromMatchButton } from "@/components/collections/from-match";
import { useShell } from "@/components/shell/context";
import { buttonClass } from "@/components/ui/button";
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
  const { org } = useShell();
  const last = played.find((m) => m.kind !== "training" && m.score_own != null) ?? played[0] ?? null;
  const next = upcoming.find((m) => m.kind !== "training") ?? null;
  const withoutVideo = played.filter((m) => !m.has_video).length;
  return (
    <div className="space-y-8">
      <LastMatch orgId={orgId} m={last} next={next} teamName={org.name} canWrite={canWrite} club={[org.primary_color, org.secondary_color ?? null]} />
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
        <aside className="flex min-w-0 flex-col gap-8">{next && <NextOpponent orgId={orgId} next={next} played={played} />}</aside>
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
  return (
    <div style={matchStyle(club, m?.opponent_color ? [m.opponent_color] : null) as CSSProperties} className="space-y-6">
      {/* no match played yet: the head waits (ink outline, no club area) and says what comes */}
      <div className="bleed-x -mt-6 lg:-mt-8">
        <WurfHead {...head} />
      </div>
      <div className="flex flex-wrap items-center gap-3">
        {m && base && (
          <Link href={base} className={buttonClass("primary")} data-testid="open-match">
            {t("openMatch")}
          </Link>
        )}
        {m && canWrite && m.has_video && <FromMatchButton orgId={orgId} teamId={m.team_id} matchId={m.id} opponent={m.opponent_name} />}
        {canWrite && checks > 0 && base && (
          <span className="flex items-center gap-2.5">
            <AttnTag>{t("check")}</AttnTag>
            <Link href={`${base}/check`} className={linkClass}>
              {t("checksOpen", { count: checks, minutes: Math.max(1, Math.round(checks / 3)) })}
            </Link>
          </span>
        )}
      </div>
      {m?.has_video && g.data && base && <ThreeThingsView orgId={orgId} matchId={m.id} graphics={g.data} oppName={m.opponent_name} hrefScenes={(_, n) => `${base}?tab=video&thing=${n}`} />}
    </div>
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
      <p className="m-0 text-[13px] leading-tight text-ink-2 max-md:hidden">
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
        <p className="m-0 text-[13px] text-ink-2 md:text-[15px]">
          <span className="md:hidden">{format.dateTime(date, { day: "2-digit", month: "2-digit" })} · </span>
          {["matches.status_processing", "matches.status_uploading", "matches.status_failed"].includes(state.label) ? (
            tm(state.label.replace("matches.", "") as "status_processing")
          ) : !m.has_video ? (
            <>
              {t("reportOnly")}
              {canWrite && m.score_own != null && (
                <>
                  {" · "}
                  <Link href={`${base}?tab=video`} className={linkClass}>
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
          <small aria-hidden className={cn("mt-1 block text-[13px] font-bold md:mt-1.5 md:text-sm", result === "win" ? "text-win" : result === "loss" ? "text-loss" : "text-ink-2")}>
            {t(result)}
          </small>
        </p>
      ) : (
        <span />
      )}
    </div>
  );
}

function NextOpponent({ orgId, next, played }: { orgId: string; next: Match; played: Match[] }) {
  const t = useTranslations("anlauf");
  const format = useFormatter();
  const date = new Date(next.kickoff_at);
  // the last duel with video: its Minifeld and a line; otherwise say there is none yet
  const met = played.find((m) => m.opponent_name === next.opponent_name && m.score_own != null && m.has_video);
  const g = useMatchGraphics(orgId, met?.id ?? "");
  const text = useThingText();
  const first = g.data ? threeThings(goalRuns(g.data))[0] : undefined;
  return (
    <section data-testid="next-opponent">
      <p className="m-0 text-[13px] font-semibold text-ink-2">
        {t("nextOpponent")} · {format.dateTime(date, { weekday: "short", hour: "2-digit", minute: "2-digit" })}
      </p>
      <h3 className="mt-1 mb-3 text-[30px] leading-[.95] md:text-4xl">
        <Link href={`/app/${orgId}/matches/${next.id}`} className="font-slant text-ink no-underline hover:underline">
          {next.is_home ? next.opponent_name : `${t("away")} ${next.opponent_name}`}
        </Link>
      </h3>
      {met ? (
        <>
          <Link href={`/app/${orgId}/matches/${met.id}`} aria-hidden tabIndex={-1} className="block">
            <MiniField orgId={orgId} m={met} width={340} />
          </Link>
          <p className="mt-2 mb-0 border-t border-rule py-2.5 text-base">
            {t("lastMeeting", { score: `${met.score_own}:${met.score_opponent}` })}
            {first && `, ${text(first)}`}
          </p>
        </>
      ) : (
        <>
          <EmptyField />
          <p className="mt-2 mb-0 border-t border-rule py-2.5 text-base text-ink-2">{t("noVideoAgainst", { opponent: next.opponent_name })}</p>
        </>
      )}
    </section>
  );
}
