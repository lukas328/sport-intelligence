"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ArrowUp, Binoculars, Clapperboard, Dumbbell, Film, ListTodo, Radio, Sparkles, Upload } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useFormatter, useNow, useTranslations } from "next-intl";
import { useMemo, useState, type ReactNode } from "react";
import { useInsightText, type InsightsData } from "@/components/analysis/insights";
import { useRosterNames } from "@/components/analysis/tagger";
import { Scoreboard } from "@/components/domain/scoreboard";
import { useShell } from "@/components/shell/context";
import { OnboardingChecklist } from "@/components/support/checklist";
import { Badge } from "@/components/ui/badge";
import { buttonClass } from "@/components/ui/button";
import { Card, EmptyState, Skeleton } from "@/components/ui/card";
import { control } from "@/components/ui/field";
import { api } from "@/lib/client";
import { matchState } from "@/lib/match-state";
import { cn } from "@/lib/utils";
import { ScheduleRow, useSchedule } from "./schedule/schedule-view";
import { targetLink } from "./assignments/my-assignments";

type Match = Schemas["MatchSummary"];

function Greeting() {
  const t = useTranslations("today");
  const format = useFormatter();
  const now = useNow({ updateInterval: 60_000 });
  const { me } = useShell();
  const first = me.name.split(/\s+/)[0] ?? me.name;
  const h = now.getHours();
  return (
    <header className="space-y-1">
      <p className="eyebrow">{format.dateTime(now, { weekday: "long", day: "numeric", month: "long" })}</p>
      <h1 className="text-[1.75rem] font-bold sm:text-4xl">{t(h < 11 ? "morning" : h < 17 ? "day" : "evening", { name: first })}</h1>
    </header>
  );
}

function Block({ title, href, linkLabel, children, className }: { title: string; href?: string; linkLabel?: string; children: ReactNode; className?: string }) {
  return (
    <section className={cn("space-y-3", className)}>
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="eyebrow">{title}</h2>
        {href && (
          <Link href={href} className="inline-flex items-center gap-1 text-[0.8125rem] font-medium text-muted hover:text-foreground">
            {linkLabel}
            <ArrowRight aria-hidden className="size-3.5" />
          </Link>
        )}
      </div>
      {children}
    </section>
  );
}

export function TodayView({ orgId }: { orgId: string }) {
  const { mode, team, teams } = useShell();
  return (
    <div className="space-y-10">
      <Greeting />
      {teams.length === 0 ? (
        <NoTeam orgId={orgId} />
      ) : mode === "staff" && team ? (
        <StaffToday orgId={orgId} teamId={team.id} />
      ) : (
        <MemberToday orgId={orgId} family={mode === "family"} />
      )}
    </div>
  );
}

function NoTeam({ orgId }: { orgId: string }) {
  const t = useTranslations("today");
  return (
    <div className="space-y-6">
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
  const base = `/app/${orgId}/teams/${teamId}`;
  return (
    <div className="space-y-10">
      <OnboardingChecklist orgId={orgId} teamId={teamId} />
      <div className="grid gap-x-8 gap-y-10 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="min-w-0 space-y-10">
          <Block title={t("today.next")} href={`${base}/matches`} linkLabel={t("shell.matches")}>
            {matches.isLoading ? <Skeleton className="h-40" /> : upcoming ? <NextMatch orgId={orgId} m={upcoming} /> : <NoNextMatch base={base} />}
          </Block>
          {(matches.isLoading || last) && (
            <Block title={t("today.last")}>{last ? <LastMatch orgId={orgId} m={last} /> : <Skeleton className="h-56" />}</Block>
          )}
        </div>
        <aside className="space-y-10">
          <AskBox base={base} />
          <NextTraining orgId={orgId} teamId={teamId} />
        </aside>
      </div>
    </div>
  );
}

function NextMatch({ orgId, m }: { orgId: string; m: Match }) {
  const t = useTranslations();
  const format = useFormatter();
  const now = useNow({ updateInterval: 60_000 });
  const when = new Date(m.kickoff_at);
  const days = Math.max(0, Math.round((new Date(when).setHours(0, 0, 0, 0) - new Date(now).setHours(0, 0, 0, 0)) / 86400000));
  const href = `/app/${orgId}/matches/${m.id}`;
  return (
    <Card className="relative overflow-hidden sm:p-8">
      <span aria-hidden className="absolute inset-y-0 left-0 w-1.5 bg-club" />
      <p className="text-sm font-semibold text-accent">{t("today.inDays", { n: days })}</p>
      <h3 className="mt-1 text-2xl font-bold sm:text-3xl">
        <Link href={href} className="hover:underline">
          {m.kind === "training" ? t("matches.training") : m.opponent_name}
        </Link>
      </h3>
      <p className="mt-1 text-sm text-muted">
        {[format.dateTime(when, { weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" }), m.kind === "training" ? null : m.is_home ? t("matches.homeShort") : t("matches.awayShort"), m.competition]
          .filter(Boolean)
          .join(" · ")}
      </p>
      <div className="mt-6 flex flex-wrap gap-2">
        {m.kind !== "training" && (
          <Link href={`${href}/scouting`} className={buttonClass("primary")}>
            <Binoculars aria-hidden />
            {t("today.prepare")}
          </Link>
        )}
        <Link href={`${href}/live`} className={buttonClass("secondary")}>
          <Radio aria-hidden />
          {t("live.open")}
        </Link>
      </div>
    </Card>
  );
}

function NoNextMatch({ base }: { base: string }) {
  const t = useTranslations();
  return (
    <Card className="flex flex-wrap items-center justify-between gap-4">
      <div className="min-w-0 max-w-md">
        <p className="font-semibold">{t("today.noNext")}</p>
        <p className="mt-1 text-sm text-muted">{t("today.noNextHint")}</p>
      </div>
      <Link href={`${base}/matches?new=1`} className={buttonClass("secondary")}>
        {t("matches.newShort")}
      </Link>
    </Card>
  );
}

function LastMatch({ orgId, m }: { orgId: string; m: Match }) {
  const t = useTranslations();
  const { team } = useShell();
  const format = useFormatter();
  const state = matchState(m);
  const href = `/app/${orgId}/matches/${m.id}`;
  const own = team?.name ?? "";
  const [home, away] = m.is_home ? [own, m.opponent_name] : [m.opponent_name, own];
  const [hs, as] = m.is_home ? [m.score_own, m.score_opponent] : [m.score_opponent, m.score_own];
  return (
    <Card className="space-y-6 sm:p-8">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted">{[format.dateTime(new Date(m.kickoff_at), { weekday: "short", day: "numeric", month: "long" }), m.competition].filter(Boolean).join(" · ")}</p>
        <Badge tone={state.tone}>{t(state.label)}</Badge>
      </div>
      {m.kind === "training" ? (
        <p className="text-2xl font-bold font-wide">{t("matches.training")}</p>
      ) : (
        <Scoreboard home={home} away={away} homeScore={hs} awayScore={as} ownSide={m.is_home ? "home" : "away"} vsLabel={t("matches.vs")} className="[&_[data-testid=score]]:text-4xl sm:[&_[data-testid=score]]:text-5xl" />
      )}
      {m.has_video && m.status === "ready" ? (
        <TopInsights orgId={orgId} m={m} />
      ) : m.status === "processing" || m.status === "uploading" ? (
        <p className="rounded-md bg-surface px-4 py-3 text-sm text-muted">{t("today.analysing")}</p>
      ) : !m.has_video ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md bg-surface px-4 py-3">
          <p className="text-sm text-muted">{t("today.uploadHint")}</p>
          <Link href={`${href}#upload`} className={buttonClass("primary", "sm")}>
            <Upload aria-hidden />
            {t("upload.title")}
          </Link>
        </div>
      ) : null}
      <Link href={href} className={buttonClass("secondary")}>
        <Clapperboard aria-hidden />
        {t("today.openMatch")}
      </Link>
    </Card>
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
  const top = (q.data?.insights ?? []).slice(0, 3);
  if (q.isLoading) return <Skeleton className="h-24" />;
  if (top.length === 0) return <p className="text-sm text-muted">{t("today.noInsights")}</p>;
  return (
    <div className="space-y-2">
      <p className="eyebrow">{t("today.insightsTitle")}</p>
      <ul className="space-y-2">
        {top.map((i) => (
          <li key={i.id} className="flex items-start gap-3 text-[0.9375rem]">
            <span aria-hidden className={cn("mt-2 size-2 shrink-0 rounded-full", i.kind === "strength" ? "bg-ok" : i.kind === "weakness" ? "bg-error" : "bg-muted")} />
            <span>
              <span className="sr-only">{t(`insights.${i.kind}`)}: </span>
              {text(i)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function AskBox({ base }: { base: string }) {
  const t = useTranslations("today");
  const router = useRouter();
  const [q, setQ] = useState("");
  return (
    <section className="space-y-3">
      <h2 className="eyebrow flex items-center gap-1.5">
        <Sparkles aria-hidden className="size-3.5" />
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
        <input id="today-ask" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("askPlaceholder")} maxLength={500} className={cn(control, "min-h-12 rounded-full pr-12 pl-4")} />
        <button type="submit" aria-label={t("ask")} disabled={q.trim().length < 3} className="absolute top-1.5 right-1.5 grid size-9 place-items-center rounded-full bg-accent text-accent-contrast disabled:opacity-40">
          <ArrowUp aria-hidden className="size-4" />
        </button>
      </form>
      <p className="text-xs text-muted">{t("askHint")}</p>
    </section>
  );
}

function NextTraining({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("today");
  const format = useFormatter();
  const today = new Date().toISOString().slice(0, 10);
  const q = useQuery({
    queryKey: ["sessions-next", teamId, today],
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/sessions", { params: { path: { org_id: orgId, team_id: teamId }, query: { from: today } } })).data ?? [],
  });
  const next = (q.data ?? []).filter((s) => s.on_date >= today).sort((a, b) => a.on_date.localeCompare(b.on_date))[0];
  const href = `/app/${orgId}/teams/${teamId}/training`;
  return (
    <Block title={t("nextTraining")} href={href} linkLabel={t("planTraining")}>
      {q.isLoading ? (
        <Skeleton className="h-24" />
      ) : next ? (
        <Link href={href} className="block rounded-lg bg-raised p-5 border border-border transition-colors hover:bg-surface/60">
          <p className="text-sm font-semibold text-accent">
            {format.dateTime(new Date(next.starts_at ?? `${next.on_date}T12:00:00`), next.starts_at ? { weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" } : { weekday: "long", day: "numeric", month: "long" })}
          </p>
          <p className="mt-1 font-semibold">{next.title || t("nextTraining")}</p>
          <p className="mt-1 text-sm text-muted">{t("trainingLength", { minutes: next.total_minutes, drills: next.drills.length })}</p>
        </Link>
      ) : (
        <div className="flex items-center gap-3 rounded-lg bg-surface/60 p-5 text-sm text-muted">
          <Dumbbell aria-hidden className="size-5 shrink-0" />
          {t("noTraining")}
        </div>
      )}
    </Block>
  );
}

/* ---------------- players and parents ---------------- */

function MemberToday({ orgId, family }: { orgId: string; family: boolean }) {
  const t = useTranslations();
  const format = useFormatter();
  const { items, reply } = useSchedule(orgId);
  const tasks = useQuery({
    queryKey: ["my-assignments", orgId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/me/assignments", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  const feeds = useQuery({
    queryKey: ["my-feeds", orgId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/me/feeds", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  const dates = (items.data ?? []).slice(0, 3);
  const open = (tasks.data ?? []).filter((a) => !a.done_at).slice(0, 4);
  const scenes = (feeds.data ?? []).slice(0, 4);
  const base = `/app/${orgId}`;
  return (
    <div className="grid gap-x-8 gap-y-10 lg:grid-cols-2">
      <Block title={t("today.myDates")} href={`${base}/schedule`} linkLabel={t("today.allDates")} className="lg:col-span-2">
        {items.isLoading ? (
          <Skeleton className="h-32" />
        ) : dates.length === 0 ? (
          <p className="rounded-lg bg-surface/60 p-5 text-sm text-muted">{t("schedule.none")}</p>
        ) : (
          <ul className="divide-y divide-border/70 overflow-hidden rounded-lg bg-raised border border-border">
            {dates.map((i) => (
              <li key={`${i.kind}-${i.id}-${i.player_id}`}>
                <ScheduleRow item={i} onReply={reply} />
              </li>
            ))}
          </ul>
        )}
      </Block>
      {!family && (
        <Block title={t("today.myTasks")} href={`${base}/assignments`} linkLabel={t("today.allTasks")}>
          {open.length === 0 ? (
            <p className="flex items-center gap-3 rounded-lg bg-surface/60 p-5 text-sm text-muted">
              <ListTodo aria-hidden className="size-5" />
              {t("today.nothing")}
            </p>
          ) : (
            <ul className="space-y-2">
              {open.map((a) => (
                <li key={a.id}>
                  <Link href={targetLink(orgId, a)} className="flex items-center gap-3 rounded-lg bg-raised px-4 py-3 border border-border hover:bg-surface/60">
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium">{a.title}</span>
                      <span className="block text-[0.8125rem] text-muted">
                        {t(`assignments.kind_${a.kind as "drill"}`)}
                        {a.due_at && ` · ${t("today.due", { date: format.dateTime(new Date(a.due_at), { day: "numeric", month: "short" }) })}`}
                      </span>
                    </span>
                    <ArrowRight aria-hidden className="size-4 text-muted" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Block>
      )}
      <Block title={t("today.newScenes")} href={`${base}/feed`} linkLabel={t("today.allScenes")}>
        {scenes.length === 0 ? (
          <p className="flex items-center gap-3 rounded-lg bg-surface/60 p-5 text-sm text-muted">
            <Film aria-hidden className="size-5" />
            {t("feed.none")}
          </p>
        ) : (
          <ul className="space-y-2">
            {scenes.map((f) => (
              <li key={`${f.player_id}-${f.match_id}`}>
                <Link href={`${base}/feed/${f.match_id}?player=${f.player_id}`} className="flex items-center gap-3 rounded-lg bg-raised px-4 py-3 border border-border hover:bg-surface/60">
                  <Film aria-hidden className="size-4 text-muted" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{f.opponent ?? t("matches.training")}</span>
                    <span className="block text-[0.8125rem] text-muted">
                      {format.dateTime(new Date(f.kickoff_at), { day: "numeric", month: "short" })}
                      {f.relation === "guardian" && ` · ${f.player_first_name}`}
                    </span>
                  </span>
                  {!f.assessed && <Badge tone="accent">{t("feed.assessNow")}</Badge>}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Block>
    </div>
  );
}

