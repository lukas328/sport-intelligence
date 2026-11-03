"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, Check, X } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { TrainingOrPageHeader } from "@/components/shell/section-nav";
import { EmptyState, Skeleton } from "@/components/ui/card";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";

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
        "inline-flex min-h-10 items-center gap-1.5 rounded-full px-4 text-sm font-medium transition-colors",
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
        <span className="mt-1 block text-[0.6875rem] font-medium uppercase tracking-wide text-muted">{format.dateTime(when, { month: "short" })}</span>
      </span>
      <div className="min-w-0 flex-1">
        <p className="font-semibold">
          {i.kind === "match" ? t("match", { opponent: i.title ?? "" }) : i.title || t("training")}
          {!self && <span className="font-normal text-muted"> {t("for", { name: i.player_name })}</span>}
        </p>
        <p className="text-[0.8125rem] text-muted">
          {[i.team, format.dateTime(when, i.starts_at ? { weekday: "long", hour: "2-digit", minute: "2-digit" } : { weekday: "long" })].join(" · ")}
        </p>
      </div>
      <div className="flex gap-2">
        {choice("yes")}
        {choice("no")}
      </div>
      {i.response && <span className="sr-only">{t(`answered_${i.response}`)}</span>}
    </div>
  );
}

/** Players and parents reply to sessions and matches (addendum 01, 5.7). */
export function ScheduleView({ orgId }: { orgId: string }) {
  const t = useTranslations("schedule");
  const { items, reply } = useSchedule(orgId);
  const list = items.data ?? [];
  return (
    <div className="space-y-8">
      <TrainingOrPageHeader title={t("title")} />
      <p className="-mt-4 text-sm text-muted">{t("hint")}</p>
      {items.isLoading ? (
        <Skeleton className="h-40" />
      ) : list.length === 0 ? (
        <EmptyState icon={<CalendarDays />} title={t("none")} />
      ) : (
        <ul className="divide-y divide-border/70 overflow-hidden rounded-2xl bg-raised ring-1 ring-border/70" data-testid="schedule">
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
