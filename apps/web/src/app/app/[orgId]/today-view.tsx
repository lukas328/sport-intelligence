"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useFormatter, useNow, useTranslations } from "next-intl";
import { useEffect, type ReactNode } from "react";
import { useShell } from "@/components/shell/context";
import { AreaSubNav } from "@/components/shell/section-nav";
import { LifeHint } from "@/components/shell/life-hint";
import { IconScenes } from "@/components/shell/icons";
import { OnboardingChecklist } from "@/components/support/checklist";
import { Badge } from "@/components/ui/badge";
import { EmptyState, Skeleton } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { api } from "@/lib/client";
import { startHref } from "@/lib/nav-model";
import { cn } from "@/lib/utils";
import { ScheduleRow, useSchedule } from "./schedule/schedule-view";

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

/**
 * The club's root (nav-model `startHref`): everyone in a team starts on Spiele, so this page is
 * only for parents (their overview, the first tab of Teamleben) and for an account without a team.
 * `notice`: one quiet line for the club's admins.
 */
export function TodayView({ orgId, notice }: { orgId: string; notice?: ReactNode }) {
  const { mode, team, teams } = useShell();
  if (teams.length === 0) return <NoTeam orgId={orgId} notice={notice} />;
  if (mode === "family") return <FamilyToday orgId={orgId} />;
  return <ToStart href={startHref(mode, orgId, team?.id ?? null)} />;
}

/** The server sends everyone else on already; this covers a team switched in another tab. */
function ToStart({ href }: { href: string }) {
  const router = useRouter();
  useEffect(() => router.replace(href), [router, href]);
  return <Skeleton className="h-40" />;
}

function NoTeam({ orgId, notice }: { orgId: string; notice?: ReactNode }) {
  const t = useTranslations("today");
  const greeting = useGreeting();
  return (
    <div className="space-y-8">
      <PageHeader eyebrow={greeting} title={t("teams")} />
      {notice}
      <OnboardingChecklist orgId={orgId} teamId={null} />
      <EmptyState title={t("noTeam")} />
    </div>
  );
}

/** What a parent's overview reads: the dates (with Teamleben) and the scenes of the child. */
function useMember(orgId: string) {
  const schedule = useSchedule(orgId);
  const feeds = useQuery({
    queryKey: ["my-feeds", orgId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/me/feeds", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  return { schedule, feeds };
}

/* ---------------- parents: the calm workbench, no stage ---------------- */

function FamilyToday({ orgId }: { orgId: string }) {
  const t = useTranslations();
  const greeting = useGreeting();
  const { schedule, feeds } = useMember(orgId);
  const { teams } = useShell();
  const dates = (schedule.items.data ?? []).slice(0, 4);
  // dates and replies are Teamfunktionen (ADR 029): without them the tab is gone, so is this block
  const datesOn = teams.some((x) => x.team_features);
  return (
    <div className="space-y-12">
      <PageHeader title={greeting.split(" · ")[0]!} eyebrow={greeting.split(" · ")[1]} />
      {/* parents: the overview is the first tab of Teamleben (K16) */}
      <AreaSubNav />
      <LifeHint />
      {datesOn && (
      <Block title={t("today.myDates")} href={`/app/${orgId}/schedule`} linkLabel={t("today.allDates")}>
        {schedule.items.isLoading ? (
          <Skeleton className="h-32" />
        ) : dates.length === 0 ? (
          <p className="text-[0.9375rem] text-muted">{t("today.noDates")}</p>
        ) : (
          <ul className="divide-y divide-foreground/10 overflow-hidden border border-border bg-raised">
            {dates.map((i) => (
              <li key={`${i.kind}-${i.id}-${i.player_id}`}>
                <ScheduleRow item={i} onReply={schedule.reply} />
              </li>
            ))}
          </ul>
        )}
      </Block>
      )}
      <Block title={t("today.newScenesFamily")} href={`/app/${orgId}/feed`} linkLabel={t("today.allScenes")}>
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
            {/* the self-assessment is the player's: a parent is not asked for it */}
            {!f.assessed && f.relation !== "guardian" && <Badge tone="accent">{t("feed.assessNow")}</Badge>}
          </Link>
        </li>
      ))}
    </ul>
  );
}
