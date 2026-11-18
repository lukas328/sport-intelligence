"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, Check, X } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { AreaOrPageHeader } from "@/components/shell/section-nav";
import { EmptyState, Skeleton } from "@/components/ui/card";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { buttonClass } from "@/components/ui/button";
import { useShell } from "@/components/shell/context";

type Item = Schemas["ScheduleItem"];

export function useSchedule(orgId: string) {
  const qc = useQueryClient();
  const items = useQuery({
    queryKey: ["schedule", orgId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/me/schedule", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  const reply = useMutation({
    mutationFn: async ({ item, response }: { item: Item; response: "yes" | "no" }) =>
      api.PUT("/v1/orgs/{org_id}/me/attendance", {
        params: { path: { org_id: orgId } },
        body: { kind: item.kind, id: item.id, player_id: item.player_id, response },
      }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["schedule", orgId] }),
  });
  return { items, reply: (item: Item, response: "yes" | "no") => reply.mutate({ item, response }) };
}

/** One date with the yes / no reply, for oneself or for a child. */
export function ScheduleRow({ item: i, onReply }: { item: Item; onReply: (item: Item, r: "yes" | "no") => void }) {
  const t = useTranslations("schedule");
  const format = useFormatter();
  const self = i.relation === "self";
  const when = i.starts_at ? new Date(i.starts_at) : new Date(`${i.on_date}T12:00:00`);
  const choice = (r: "yes" | "no") => (
    <button
      type="button"
      aria-pressed={i.response === r}
      onClick={() => onReply(i, r)}
      className={cn(
        "inline-flex min-h-10 items-center gap-1.5 px-4 text-sm font-medium transition-colors",
        i.response === r
          ? r === "yes"
            ? "bg-ok text-white"
            : "bg-error text-white"
          : "bg-raised text-foreground ring-1 ring-inset ring-border hover:bg-surface",
      )}
    >
      {r === "yes" ? <Check aria-hidden className="size-4" /> : <X aria-hidden className="size-4" />}
      {self ? t(r) : t(r === "yes" ? "forYes" : "forNo")}
    </button>
  );
  return (
    <div className="flex flex-wrap items-center gap-4 px-4 py-3.5 sm:px-5">
      <span className="w-11 shrink-0 text-center leading-none">
        <span className="block text-lg font-bold font-wide tabular-nums">{format.dateTime(when, { day: "numeric" })}</span>
        <span className="mt-1 block text-[0.875rem] font-medium text-muted">{format.dateTime(when, { month: "short" })}</span>
      </span>
      {/* the text keeps a width of its own: on a phone the replies move under it instead of
          squeezing it to one word per line */}
      <div className="min-w-0 flex-1 basis-48">
        <p className="font-semibold">
          {i.kind === "match" ? t("match", { opponent: i.title ?? "" }) : i.title || t("training")}
          {!self && <span className="font-normal text-muted"> {t("for", { name: i.player_name })}</span>}
        </p>
        <p className="text-[0.9375rem] text-muted">
          {[i.team, format.dateTime(when, i.starts_at ? { weekday: "long", hour: "2-digit", minute: "2-digit" } : { weekday: "long" })].join(" · ")}
        </p>
      </div>
      <div className="flex flex-wrap gap-2 max-sm:pl-[60px]">
        {choice("yes")}
        {choice("no")}
      </div>
      {i.response && <span className="sr-only">{t(`answered_${i.response}`)}</span>}
    </div>
  );
}

/** One date of the team for the staff (A7): what, when, where, the replies so far. */
export function TeamDateRow({ orgId, item: i }: { orgId: string; item: Schemas["TeamDate"] }) {
  const t = useTranslations("schedule");
  const format = useFormatter();
  const when = i.starts_at ? new Date(i.starts_at) : new Date(`${i.on_date}T12:00:00`);
  const what = i.kind === "match" ? t("match", { opponent: i.title ?? "" }) : i.title || t("training");
  const replies = (i.yes ?? 0) + (i.no ?? 0) > 0 ? t("replies", { yes: i.yes ?? 0, no: i.no ?? 0 }) : t("noReplies");
  return (
    <div className="flex flex-wrap items-center gap-4 px-4 py-3.5 sm:px-5">
      <span className="w-11 shrink-0 text-center leading-none">
        <span className="block text-lg font-bold font-wide tabular-nums">{format.dateTime(when, { day: "numeric" })}</span>
        <span className="mt-1 block text-[0.875rem] font-medium text-muted">{format.dateTime(when, { month: "short" })}</span>
      </span>
      <div className="min-w-0 flex-1 basis-48">
        <p className="font-semibold">
          {i.kind === "match" ? (
            <Link href={`/app/${orgId}/matches/${i.id}`} className="text-foreground underline decoration-[1.5px] underline-offset-4">
              {what}
            </Link>
          ) : (
            what
          )}
          {i.official && <span className="ml-2 inline-block border-[1.5px] border-foreground px-1.5 text-[0.8125rem] font-semibold">{t("official")}</span>}
        </p>
        <p className="text-[0.9375rem] text-muted">
          {[format.dateTime(when, i.starts_at ? { weekday: "long", hour: "2-digit", minute: "2-digit" } : { weekday: "long" }), i.venue, replies].filter(Boolean).join(" · ")}
        </p>
      </div>
    </div>
  );
}

/** The staff's dates (A7): the team's trainings and matches, the official schedule's matches
 * among them without being set up twice; «Spiel ansetzen» only for a match outside it. */
function StaffDates({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("schedule");
  const path = { params: { path: { org_id: orgId, team_id: teamId } } };
  const dates = useQuery({
    queryKey: ["team-dates", orgId, teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/dates", path)).data ?? [],
  });
  const team = useQuery({
    queryKey: ["team", orgId, teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}", path)).data ?? null,
  });
  const linked = team.data?.official_team_id != null;
  const list = dates.data ?? [];
  const teamBase = `/app/${orgId}/teams/${teamId}`;
  const actions = (
    <span className="flex flex-wrap gap-2">
      <Link href={`${teamBase}/training`} className={buttonClass("secondary", "sm")}>
        {t("planTraining")}
      </Link>
      <Link href={`${teamBase}/matches?new=1`} className={buttonClass("ghost", "sm")} data-testid="schedule-match">
        {t(linked ? "scheduleOther" : "scheduleMatch")}
      </Link>
    </span>
  );
  if (dates.isLoading) return <Skeleton className="h-40" />;
  return (
    <>
      {linked && <p className="-mt-4 text-sm text-muted">{t("officialHint")}</p>}
      {list.length === 0 ? (
        <EmptyState icon={<CalendarDays />} title={t("noneStaff")} action={actions} />
      ) : (
        <>
          <ul className="divide-y divide-border/70 border-t-2 border-foreground" data-testid="schedule">
            {list.map((i) => (
              <li key={`${i.kind}-${i.id}`}>
                <TeamDateRow orgId={orgId} item={i} />
              </li>
            ))}
          </ul>
          {actions}
        </>
      )}
    </>
  );
}

/** Players and parents reply to sessions and matches (addendum 01, 5.7); the staff see the
 * team's dates with the replies (A7). */
export function ScheduleView({ orgId }: { orgId: string }) {
  const t = useTranslations("schedule");
  const { items, reply } = useSchedule(orgId);
  const list = items.data ?? [];
  // staff plan the dates; players and parents reply to them
  const { mode, team } = useShell();
  const staff = mode === "staff";
  if (staff && team) {
    return (
      <div className="space-y-8">
        <AreaOrPageHeader title={t("titleStaff")} />
        <p className="-mt-4 text-sm text-muted">{t("hintStaff")}</p>
        <StaffDates orgId={orgId} teamId={team.id} />
      </div>
    );
  }
  return (
    <div className="space-y-8">
      <AreaOrPageHeader title={t("title")} />
      <p className="-mt-4 text-sm text-muted">{t("hint")}</p>
      {items.isLoading ? (
        <Skeleton className="h-40" />
      ) : list.length === 0 ? (
        <EmptyState icon={<CalendarDays />} title={t("none")} />
      ) : (
        <ul className="divide-y divide-border/70 border-t-2 border-foreground" data-testid="schedule">
          {list.map((i) => (
            <li key={`${i.kind}-${i.id}-${i.player_id}`}>
              <ScheduleRow item={i} onReply={reply} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
