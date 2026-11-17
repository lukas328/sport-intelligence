"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as M from "@radix-ui/react-dropdown-menu";
import { Bell } from "lucide-react";
import Link from "next/link";
import { useFormatter, useNow, useTranslations } from "next-intl";
import { MENU_SURFACE } from "@/components/ui/menu";
import { api } from "@/lib/client";
import { checkMinutes } from "@/lib/shot-spot";
import { cn } from "@/lib/utils";

type Note = Schemas["NotificationOut"];

/** Notification bell: polls once a minute (and on focus), list of the latest 50. */
export function NotificationBell({ orgId }: { orgId: string }) {
  const t = useTranslations("notifications");
  const format = useFormatter();
  // relative times ("vor 5 Minuten") against a clock that moves on each minute
  const now = useNow({ updateInterval: 60_000 });
  const qc = useQueryClient();
  const key = ["notifications", orgId];
  const q = useQuery({
    queryKey: key,
    refetchInterval: 60_000,
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/me/notifications", { params: { path: { org_id: orgId } } })).data ?? { unread: 0, items: [] },
  });
  const read = useMutation({
    mutationFn: async (ids: string[]) =>
      api.POST("/v1/orgs/{org_id}/me/notifications/read", { params: { path: { org_id: orgId } }, body: { ids } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: key }),
  });
  const unread = q.data?.unread ?? 0;
  const items = q.data?.items ?? [];
  // a kind the web has no text for yet still shows as a notification, not as a raw key
  // with the match's name where the note carries it (UX test H06, B29)
  const text = (n: Note) => {
    const named = `${n.kind}_match`;
    // the questions with about how long they take: «3 Fragen, etwa 1 Minute» (second round A6)
    const questions = Number((n.params as { questions?: number } | null)?.questions ?? 0);
    const params = { ...(n.params as object), minutes: checkMinutes(questions, 0) };
    if ((n.params as { opponent?: string } | null)?.opponent && t.has(named as "assignment")) return t(named as "assignment", params as never);
    // who asks for which team (K17); older notes without a name keep the plain text
    const person = `${n.kind}_${(n.params as { team?: string } | null)?.team ? "team" : "named"}`;
    if ((n.params as { name?: string } | null)?.name && t.has(person as "assignment")) return t(person as "assignment", n.params as never);
    return t.has(n.kind as "assignment") ? t(n.kind as "assignment", n.params as never) : t("other");
  };
  return (
    <M.Root>
      <M.Trigger
        aria-label={t("open", { count: unread })}
        className="relative grid size-11 shrink-0 cursor-pointer place-items-center text-ink"
        data-testid="bell"
      >
        {/* with a count the bell moves aside, so the number sits beside it, not over it (UX test A01) */}
        <Bell aria-hidden className={cn("size-5", unread > 0 && "-translate-x-1 translate-y-1")} strokeWidth={1.8} />
        {unread > 0 && (
          <span
            className="absolute top-0 right-0 grid min-w-[1.375rem] place-items-center bg-accent px-1 font-mono text-[13px] font-bold leading-[1.375rem] text-accent-contrast ring-2 ring-background"
            data-testid="unread"
          >
            {unread}
          </span>
        )}
      </M.Trigger>
      <M.Portal>
        <M.Content
          align="end"
          sideOffset={6}
          collisionPadding={12}
          aria-label={t("title")}
          className={cn(MENU_SURFACE, "w-[22rem] max-w-[calc(100vw-1.5rem)]")}
        >
          <div className="flex items-center justify-between border-b-2 border-ink px-4 py-3">
            <p className="font-bold">{t("title")}</p>
            {unread > 0 && (
              <button className="text-xs font-medium text-accent underline decoration-[1.5px] underline-offset-4" onClick={() => read.mutate([])}>
                {t("markAll")}
              </button>
            )}
          </div>
          <div className="max-h-[26rem] overflow-auto p-1.5">
            {/* empty: say what will come here (K8) */}
            {items.length === 0 && (
              <div className="px-3 py-5" data-testid="bell-empty">
                <p className="m-0 font-semibold">{t("none")}</p>
                <p className="mt-1 mb-0 text-[15px] text-ink-2">{t("noneHint")}</p>
              </div>
            )}
            {items.map((n) => (
              <M.Item key={n.id} asChild>
                <Link
                  href={n.link ?? `/app/${orgId}`}
                  onClick={() => !n.read_at && read.mutate([n.id])}
                  className={cn("group flex gap-3 px-3 py-2.5 no-underline outline-none data-[highlighted]:bg-ink data-[highlighted]:text-ground", !n.read_at && "font-semibold")}
                >
                  <span aria-hidden className={cn("mt-1.5 size-2 shrink-0 rounded-full", n.read_at ? "bg-transparent" : "bg-accent group-data-[highlighted]:bg-ground")} />
                  <span className="min-w-0">
                    {text(n)}
                    <span className="block text-xs font-normal text-muted group-data-[highlighted]:text-ground/80">{format.relativeTime(new Date(n.created_at), now)}</span>
                  </span>
                </Link>
              </M.Item>
            ))}
          </div>
        </M.Content>
      </M.Portal>
    </M.Root>
  );
}
