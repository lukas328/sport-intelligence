"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ArrowUp, Check, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useFormatter, useNow, useTranslations } from "next-intl";
import { useMemo, useState, type ReactNode } from "react";
import { useInsightText, type InsightsData } from "@/components/analysis/insights";
import { useRosterNames } from "@/components/analysis/tagger";
import { MatchScore } from "@/components/domain/match-score";
import { Stage, StageTag, stageButton, stageLink } from "@/components/domain/stage";
import { useShell } from "@/components/shell/context";
import { IconAsk, IconScenes } from "@/components/shell/icons";
import { OnboardingChecklist } from "@/components/support/checklist";
import { Badge } from "@/components/ui/badge";
import { EmptyState, Skeleton } from "@/components/ui/card";
import { control } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";
import { matchStatement } from "@/lib/voice";
import { targetLink } from "./assignments/my-assignments";
import { ScheduleRow, useSchedule } from "./schedule/schedule-view";

type Match = Schemas["MatchSummary"];

/** "Guten Abend, Andrea · Dienstag, 3. November": warm, one line, above the stage headline. */
function useGreeting() {
  const t = useTranslations("today");
  const format = useFormatter();
  const now = useNow({ updateInterval: 60_000 });
  const { me } = useShell();
  const first = me.name.split(/\s+/)[0] ?? me.name;
  const h = now.getHours();
  return `${t(h < 11 ? "morning" : h < 17 ? "day" : "evening", { name: first })} · ${format.dateTime(now, { weekday: "long", day: "numeric", month: "long" })}`;
}

/** A workbench block: a condensed title with an optional link, content below. */
function Block({ title, href, linkLabel, children, className }: { title: string; href?: string; linkLabel?: string; children: ReactNode; className?: string }) {
  return (
    <section className={cn("space-y-3", className)}>
      <div className="flex items-baseline justify-between gap-3 border-b border-foreground/15 pb-2">
        <h2 className="text-2xl">{title}</h2>
        {href && (
          <Link href={href} className="inline-flex items-center gap-1 text-sm font-semibold text-accent hover:underline">
            {linkLabel}
            <ArrowRight aria-hidden className="size-3.5" />
          </Link>
        )}
      </div>
      {children}
    </section>
  );
}

/** A row of a workbench list: label on the left, value or link on the right. */
function Row({ label, children, href }: { label: string; children: ReactNode; href?: string }) {
  const body = (
    <>
      <span className="w-24 shrink-0 text-sm font-semibold text-muted">{label}</span>
      <span className="min-w-0 flex-1">{children}</span>
      {href && <ArrowRight aria-hidden className="size-4 shrink-0 text-muted transition-transform group-hover:translate-x-0.5" />}
    </>
  );
  return (
    <li className="border-b border-foreground/10 last:border-0">
      {href ? (
        <Link href={href} className="group flex items-center gap-4 py-3.5 hover:text-accent">
          {body}
        </Link>
      ) : (
        <div className="flex items-center gap-4 py-3.5">{body}</div>
      )}
    </li>
  );
}

export function TodayView({ orgId }: { orgId: string }) {
  const { mode, team, teams } = useShell();
  if (teams.length === 0) return <NoTeam orgId={orgId} />;
  if (mode === "staff" && team) return <StaffToday orgId={orgId} teamId={team.id} />;
  if (mode === "family") return <FamilyToday orgId={orgId} />;
  return <PlayerToday orgId={orgId} />;
}

function NoTeam({ orgId }: { orgId: string }) {
  const t = useTranslations("today");
  const greeting = useGreeting();
  return (
    <div className="space-y-8">
      <PageHeader eyebrow={greeting} title={t("teams")} />
      <OnboardingChecklist orgId={orgId} teamId={null} />
      <EmptyState title={t("noTeam")} />
    </div>
  );
}

/* ---------------- coaches and analysts ---------------- */

function StaffToday({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations();
  const now = useNow({ updateInterval: 60_000 });
  const matches = useQuery({
    queryKey: ["team-matches", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", { params: { path: { org_id: orgId, team_id: teamId } } })).data ?? [],
  });
  const list = matches.data ?? [];
  const upcoming = list
    .filter((m) => new Date(m.kickoff_at).getTime() > now.getTime() - 3 * 3600_000 && m.score_own == null && !m.has_video)
    .sort((a, b) => a.kickoff_at.localeCompare(b.kickoff_at))[0];
  const last = list.filter((m) => m !== upcoming && new Date(m.kickoff_at) <= now).sort((a, b) => b.kickoff_at.localeCompare(a.kickoff_at))[0];
  // the stage answers the coach's first question: the match ahead when it is close, else the last one
  const soon = upcoming && new Date(upcoming.kickoff_at).getTime() - now.getTime() < 3 * 86400_000;
  const base = `/app/${orgId}/teams/${teamId}`;
  return (
    <div className="space-y-12">
      {matches.isLoading ? (
        <Stage>
          <Skeleton className="h-28 w-80 max-w-full bg-club-ink/15" />
        </Stage>
      ) : soon || (!last && upcoming) ? (
        <NextStage orgId={orgId} m={upcoming!} />
      ) : last ? (
        <LastStage orgId={orgId} m={last} base={base} />
      ) : (
        <FirstStage base={base} />
      )}
      <OnboardingChecklist orgId={orgId} teamId={teamId} />
      <div className="grid gap-x-12 gap-y-12 lg:grid-cols-2">
        <Block title={t("today.standsOut")} href={last ? `/app/${orgId}/matches/${last.id}` : undefined} linkLabel={t("today.openMatch")}>
          {last && last.has_video && last.status === "ready" ? <TopInsights orgId={orgId} m={last} /> : <p className="text-[0.9375rem] text-muted">{t("today.notAnalysed")}</p>}
        </Block>
        <div className="space-y-12">
          <Block title={t("today.upNext")}>
            {upcoming && !soon && <MatchAhead orgId={orgId} m={upcoming} />}
            <ul>
              {(!upcoming || soon) && (
                <Row label={t("today.match")} href={upcoming ? `/app/${orgId}/matches/${upcoming.id}` : `${base}/matches?new=1`}>
                  {upcoming ? <UpcomingLine m={upcoming} /> : <span className="text-muted">{t("today.noMatchPlanned")}</span>}
                </Row>
              )}
              <NextTrainingRow orgId={orgId} teamId={teamId} />
            </ul>
          </Block>
          <AskBox base={base} />
        </div>
      </div>
    </div>
  );
}

/** The next match as a fixture announcement: date in scoreboard type, opponent, how many days to go. */
function MatchAhead({ orgId, m }: { orgId: string; m: Match }) {
  const t = useTranslations();
  const format = useFormatter();
  const now = useNow({ updateInterval: 60_000 });
  const when = new Date(m.kickoff_at);
  return (
    <Link href={`/app/${orgId}/matches/${m.id}`} className="group mb-1 grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-5 border-b border-foreground/10 py-4">
      <span className="text-center leading-none">
        <span className="block font-display text-sm uppercase text-muted">{format.dateTime(when, { weekday: "short" })}</span>
        <span className="mt-1 block font-score text-[2.75rem] leading-[0.9]">{format.dateTime(when, { day: "2-digit", month: "2-digit" })}</span>
      </span>
      <span className="min-w-0">
        <span className="block truncate font-display text-[1.75rem] leading-tight group-hover:text-accent">{m.opponent_name}</span>
        <span className="block text-sm text-muted">
          {[format.dateTime(when, { hour: "2-digit", minute: "2-digit" }), m.is_home ? t("matches.homeShort") : t("matches.awayShort"), format.relativeTime(when, now)].join(" · ")}
        </span>
      </span>
    </Link>
  );
}

function UpcomingLine({ m }: { m: Match }) {
  const t = useTranslations();
  const format = useFormatter();
  const when = new Date(m.kickoff_at);
  return (
    <>
      <span className="block truncate font-semibold">{m.kind === "training" ? t("matches.training") : m.opponent_name}</span>
      <span className="block text-sm text-muted">
        {[format.dateTime(when, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }), m.kind === "training" ? null : m.is_home ? t("matches.homeShort") : t("matches.awayShort")]
          .filter(Boolean)
          .join(" · ")}
      </span>
    </>
  );
}

function NextStage({ orgId, m }: { orgId: string; m: Match }) {
  const t = useTranslations();
  const format = useFormatter();
  const now = useNow({ updateInterval: 60_000 });
  const greeting = useGreeting();
  const when = new Date(m.kickoff_at);
  const days = Math.max(0, Math.round((new Date(when).setHours(0, 0, 0, 0) - new Date(now).setHours(0, 0, 0, 0)) / 86400000));
  const href = `/app/${orgId}/matches/${m.id}`;
  return (
    <Stage
      eyebrow={greeting}
      aside={
        <div className="text-left xl:text-center" aria-hidden>
          <span className="block font-score text-[5rem] leading-[0.85] xl:text-[clamp(3.25rem,4.2vw,4.75rem)]">{format.dateTime(when, { hour: "2-digit", minute: "2-digit" })}</span>
          <span className="mt-2 block text-[0.9375rem] font-semibold">{format.dateTime(when, { weekday: "long", day: "numeric", month: "long" })}</span>
        </div>
      }
    >
      <p className="mt-6 text-lg font-semibold">
        {t("today.inDays", { n: days })} · {m.kind === "training" ? t("matches.training") : m.is_home ? t("matches.homeShort") : t("matches.awayShort")}
      </p>
      <h1 className="mt-1 text-[2.75rem] leading-[0.95] sm:text-6xl lg:text-[4.25rem]">{m.kind === "training" ? t("matches.training") : m.opponent_name}</h1>
      {m.competition && <p className="mt-3 text-lg">{m.competition}</p>}
      <div className="mt-7 flex flex-wrap gap-3">
        {m.kind !== "training" && (
          <Link href={`${href}/scouting`} className={stageButton("solid")}>
            {t("today.prepare")}
          </Link>
        )}
        <Link href={`${href}/live`} className={stageButton(m.kind === "training" ? "solid" : "outline")}>
          {t("live.open")}
        </Link>
      </div>
    </Stage>
  );
}

function LastStage({ orgId, m, base }: { orgId: string; m: Match; base: string }) {
  const t = useTranslations();
  const format = useFormatter();
  const greeting = useGreeting();
  const href = `/app/${orgId}/matches/${m.id}`;
  const statement = matchStatement({ own: m.score_own, opp: m.score_opponent, opponent: m.opponent_name });
  const needsVideo = !m.has_video && m.status !== "processing" && m.status !== "uploading";
  const teamName = useShell().team?.name;
  return (
    <Stage
      eyebrow={greeting}
      aside={
        m.score_own != null && m.score_opponent != null ? (
          <Link href={href} className="group block text-left xl:text-center">
            <MatchScore own={m.score_own} opp={m.score_opponent} className="text-[6rem] leading-[0.85] xl:text-[clamp(3.5rem,4.6vw,5.25rem)]" />
            <span className="mt-1 block max-w-[16rem] truncate text-[0.9375rem] font-semibold group-hover:underline xl:mx-auto">
              {teamName ? `${teamName} – ${m.opponent_name}` : m.opponent_name}
            </span>
          </Link>
        ) : undefined
      }
    >
      <p className="mt-6 text-lg font-semibold">{t("today.lastMatchOn", { date: format.dateTime(new Date(m.kickoff_at), { day: "numeric", month: "long" }) })}</p>
      <h1 className="mt-1 text-[2.75rem] leading-[0.95] sm:text-6xl lg:text-[4.25rem]">
        {statement ? t(statement.headline.key as "voice.won", statement.headline.params as never) : m.kind === "training" ? t("matches.training") : m.opponent_name}
      </h1>
      {/* the state only when it asks for something (running, or a video to upload) */}
      {(m.status === "processing" || m.status === "uploading" || needsVideo) && (
        <p className="mt-3 text-lg">{m.status === "processing" || m.status === "uploading" ? t("today.analysing") : t("today.uploadHint")}</p>
      )}
      {m.is_demo && (
        <p className="mt-3">
          <StageTag>{t("matches.demo")}</StageTag>
        </p>
      )}
      <div className="mt-7 flex flex-wrap gap-3">
        {needsVideo ? (
          <Link href={`${href}#upload`} className={stageButton("solid")}>
            {t("upload.title")}
          </Link>
        ) : (
          <Link href={href} className={stageButton("solid")}>
            {t("today.openMatch")}
          </Link>
        )}
        <Link href={`${base}/assistant`} className={stageLink}>
          <IconAsk />
          {t("palette.ask")}
        </Link>
      </div>
    </Stage>
  );
}

function FirstStage({ base }: { base: string }) {
  const t = useTranslations();
  const greeting = useGreeting();
  return (
    <Stage eyebrow={greeting}>
      <h1 className="mt-6 text-[2.75rem] leading-[0.95] sm:text-6xl">{t("today.firstMatch")}</h1>
      <p className="mt-3 text-lg">{t("today.firstMatchHint")}</p>
      <div className="mt-7">
        <Link href={`${base}/matches?new=1`} className={stageButton("solid")}>
          {t("matches.newShort")}
        </Link>
      </div>
    </Stage>
  );
}

function TopInsights({ orgId, m }: { orgId: string; m: Match }) {
  const t = useTranslations();
  const { team } = useShell();
  const q = useQuery({
    queryKey: ["insights", m.id],
    queryFn: async () => ((await api.GET("/v1/orgs/{org_id}/matches/{match_id}/insights", { params: { path: { org_id: orgId, match_id: m.id } } })).data ?? null) as InsightsData | null,
  });
  const roster = useRosterNames(orgId, m.team_id, team?.season_id ?? "");
  const names = useMemo(() => Object.fromEntries((roster.data ?? []).map((r) => [r.player_id, `${r.first_name} ${r.last_name}`])), [roster.data]);
  const text = useInsightText(names);
  // the same order as on the match page: a win opens with what worked
  const won = m.score_own != null && m.score_opponent != null && m.score_own > m.score_opponent;
  const rank = (k: string) => (k === "strength" ? (won ? 0 : 1) : k === "weakness" ? (won ? 1 : 0) : 2);
  const top = [...(q.data?.insights ?? [])].sort((a, b) => rank(a.kind) - rank(b.kind)).slice(0, 3);
  if (q.isLoading) return <Skeleton className="h-24" />;
  if (top.length === 0) return <p className="text-[0.9375rem] text-muted">{t("today.noInsights")}</p>;
  // the first weakness carries the signal: the one thing to take into the next training
  const focus = top.find((i) => i.kind === "weakness")?.id;
  return (
    <ul>
      {top.map((i) => (
        <li key={i.id} className="border-b border-foreground/10 last:border-0">
          <Link
            href={`/app/${orgId}/matches/${m.id}`}
            className="flex items-start gap-3 px-2 py-3 text-[0.9375rem] transition-colors hover:bg-surface"
          >
            {/* the same marks as on the match page: strength green, the first weakness the signal */}
            <span
              aria-hidden
              className={cn(
                "mt-1.5 size-2.5 shrink-0 rounded-[2px]",
                i.kind === "strength" ? "bg-ok" : i.id === focus ? "bg-signal ring-1 ring-foreground/30" : "bg-foreground/45",
              )}
            />
            <span>
              <span className="sr-only">{t(`insights.${i.kind}`)}: </span>
              {text(i)}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function AskBox({ base }: { base: string }) {
  const t = useTranslations("today");
  const router = useRouter();
  const [q, setQ] = useState("");
  return (
    <section className="space-y-2">
      <h2 className="flex items-center gap-2 text-lg">
        <IconAsk className="size-5" />
        {t("ask")}
      </h2>
      <form
        className="relative"
        onSubmit={(e) => {
          e.preventDefault();
          if (q.trim().length >= 3) router.push(`${base}/assistant?q=${encodeURIComponent(q.trim())}`);
        }}
      >
        <label className="sr-only" htmlFor="today-ask">
          {t("ask")}
        </label>
        <input id="today-ask" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("askPlaceholder")} maxLength={500} className={cn(control, "min-h-12 pr-14 pl-4 text-base")} />
        <button type="submit" aria-label={t("ask")} disabled={q.trim().length < 3} className="absolute top-1.5 right-1.5 grid size-9 place-items-center rounded-md bg-accent text-accent-contrast disabled:opacity-40">
          <ArrowUp aria-hidden className="size-4" />
        </button>
      </form>
      <p className="text-sm text-muted">{t("askHint")}</p>
    </section>
  );
}

function NextTrainingRow({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("today");
  const format = useFormatter();
  const today = new Date().toISOString().slice(0, 10);
  const q = useQuery({
    queryKey: ["sessions-next", teamId, today],
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/sessions", { params: { path: { org_id: orgId, team_id: teamId }, query: { from: today } } })).data ?? [],
  });
  const next = (q.data ?? []).filter((s) => s.on_date >= today).sort((a, b) => a.on_date.localeCompare(b.on_date))[0];
  return (
    <Row label={t("trainingRow")} href={`/app/${orgId}/teams/${teamId}/training`}>
      {next ? (
        <>
          <span className="block truncate font-semibold">{next.title || t("nextTraining")}</span>
          <span className="block text-sm text-muted">
            {format.dateTime(new Date(next.starts_at ?? `${next.on_date}T12:00:00`), next.starts_at ? { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" } : { weekday: "short", day: "numeric", month: "short" })} ·{" "}
            {t("trainingLength", { minutes: next.total_minutes, drills: next.drills.length })}
          </span>
        </>
      ) : (
        <span className="text-muted">{q.isLoading ? "" : t("noTraining")}</span>
      )}
    </Row>
  );
}

/* ---------------- players ---------------- */

function useMember(orgId: string) {
  const schedule = useSchedule(orgId);
  const tasks = useQuery({
    queryKey: ["my-assignments", orgId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/me/assignments", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  const feeds = useQuery({
    queryKey: ["my-feeds", orgId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/me/feeds", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  return { schedule, tasks, feeds };
}

function PlayerToday({ orgId }: { orgId: string }) {
  const t = useTranslations();
  const format = useFormatter();
  const greeting = useGreeting();
  const { schedule, tasks, feeds } = useMember(orgId);
  const dates = schedule.items.data ?? [];
  const next = dates[0];
  const when = next ? new Date(next.starts_at ?? `${next.on_date}T12:00:00`) : null;
  const choice = (r: "yes" | "no") =>
    next && (
      <button
        type="button"
        aria-pressed={next.response === r}
        onClick={() => schedule.reply(next, r)}
        className={cn(stageButton(next.response === r ? "solid" : "outline"))}
      >
        {r === "yes" ? <Check aria-hidden /> : <X aria-hidden />}
        {t(`schedule.${r}`)}
      </button>
    );
  return (
    <div className="space-y-12">
      <Stage
        eyebrow={greeting}
        aside={
          when ? (
            <div className="text-left xl:text-center" aria-hidden>
              <span className="block font-score text-[5rem] leading-[0.85] xl:text-[clamp(3.25rem,4.2vw,4.75rem)]">{format.dateTime(when, next?.starts_at ? { hour: "2-digit", minute: "2-digit" } : { day: "numeric", month: "numeric" })}</span>
              <span className="mt-2 block text-[0.9375rem] font-semibold">{format.dateTime(when, { weekday: "long", day: "numeric", month: "long" })}</span>
            </div>
          ) : undefined
        }
      >
        <p className="mt-6 text-lg font-semibold">{t("today.yourNext")}</p>
        <h1 className="mt-1 text-[2.75rem] leading-[0.95] sm:text-6xl">
          {schedule.items.isLoading ? "" : next ? (next.kind === "match" ? t("schedule.match", { opponent: next.title ?? "" }) : next.title || t("schedule.training")) : t("today.noDates")}
        </h1>
        {next && <div className="mt-7 flex flex-wrap gap-3">{choice("yes")}{choice("no")}</div>}
      </Stage>
      <div className="grid gap-x-12 gap-y-12 lg:grid-cols-2">
        <Block title={t("today.newScenes")} href={`/app/${orgId}/feed`} linkLabel={t("today.allScenes")}>
          <Scenes orgId={orgId} feeds={feeds.data ?? []} loading={feeds.isLoading} />
        </Block>
        <div className="space-y-12">
          <Block title={t("today.myTasks")} href={`/app/${orgId}/assignments`} linkLabel={t("today.allTasks")}>
            <Tasks orgId={orgId} tasks={(tasks.data ?? []).filter((a) => !a.done_at)} />
          </Block>
          {dates.length > 1 && (
            <Block title={t("today.myDates")} href={`/app/${orgId}/schedule`} linkLabel={t("today.allDates")}>
              <ul className="-mx-4 divide-y divide-foreground/10 overflow-hidden rounded-lg border border-border bg-raised sm:mx-0">
                {dates.slice(1, 4).map((i) => (
                  <li key={`${i.kind}-${i.id}-${i.player_id}`}>
                    <ScheduleRow item={i} onReply={schedule.reply} />
                  </li>
                ))}
              </ul>
            </Block>
          )}
        </div>
      </div>
    </div>
  );
}

/* ---------------- parents: the calm workbench, no stage ---------------- */

function FamilyToday({ orgId }: { orgId: string }) {
  const t = useTranslations();
  const greeting = useGreeting();
  const { schedule, feeds } = useMember(orgId);
  const dates = (schedule.items.data ?? []).slice(0, 4);
  return (
    <div className="space-y-12">
      <PageHeader title={greeting.split(" · ")[0]!} eyebrow={greeting.split(" · ")[1]} />
      <Block title={t("today.myDates")} href={`/app/${orgId}/schedule`} linkLabel={t("today.allDates")}>
        {schedule.items.isLoading ? (
          <Skeleton className="h-32" />
        ) : dates.length === 0 ? (
          <p className="text-[0.9375rem] text-muted">{t("today.noDates")}</p>
        ) : (
          <ul className="divide-y divide-foreground/10 overflow-hidden rounded-lg border border-border bg-raised">
            {dates.map((i) => (
              <li key={`${i.kind}-${i.id}-${i.player_id}`}>
                <ScheduleRow item={i} onReply={schedule.reply} />
              </li>
            ))}
          </ul>
        )}
      </Block>
      <Block title={t("today.newScenes")} href={`/app/${orgId}/feed`} linkLabel={t("today.allScenes")}>
        <Scenes orgId={orgId} feeds={feeds.data ?? []} loading={feeds.isLoading} />
      </Block>
    </div>
  );
}

function Scenes({ orgId, feeds, loading }: { orgId: string; feeds: Schemas["FeedListItem"][]; loading: boolean }) {
  const t = useTranslations();
  const format = useFormatter();
  if (loading) return <Skeleton className="h-24" />;
  if (feeds.length === 0) return <p className="text-[0.9375rem] text-muted">{t("feed.none")}</p>;
  return (
    <ul>
      {feeds.slice(0, 4).map((f) => (
        <li key={`${f.player_id}-${f.match_id}`} className="border-b border-foreground/10 last:border-0">
          <Link href={`/app/${orgId}/feed/${f.match_id}?player=${f.player_id}`} className="group flex items-center gap-3 py-3.5 hover:text-accent">
            <IconScenes className="size-5 shrink-0 text-muted" />
            <span className="min-w-0 flex-1">
              <span className="block truncate font-semibold">{f.opponent ?? t("matches.training")}</span>
              <span className="block text-sm text-muted">
                {format.dateTime(new Date(f.kickoff_at), { day: "numeric", month: "short" })}
                {f.relation === "guardian" && ` · ${f.player_first_name}`}
              </span>
            </span>
            {!f.assessed && <Badge tone="accent">{t("feed.assessNow")}</Badge>}
          </Link>
        </li>
      ))}
    </ul>
  );
}

function Tasks({ orgId, tasks }: { orgId: string; tasks: Schemas["AssignmentOut"][] }) {
  const t = useTranslations();
  const format = useFormatter();
  if (tasks.length === 0) return <p className="text-[0.9375rem] text-muted">{t("today.nothing")}</p>;
  return (
    <ul>
      {tasks.slice(0, 4).map((a) => (
        <li key={a.id} className="border-b border-foreground/10 last:border-0">
          <Link href={targetLink(orgId, a)} className="group flex items-center gap-3 py-3.5 hover:text-accent">
            <span className="min-w-0 flex-1">
              <span className="block truncate font-semibold">{a.title}</span>
              <span className="block text-sm text-muted">
                {t(`assignments.kind_${a.kind as "drill"}`)}
                {a.due_at && ` · ${t("today.due", { date: format.dateTime(new Date(a.due_at), { day: "numeric", month: "short" }) })}`}
              </span>
            </span>
            <ArrowRight aria-hidden className="size-4 text-muted transition-transform group-hover:translate-x-0.5" />
          </Link>
        </li>
      ))}
    </ul>
  );
}
