"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as M from "@radix-ui/react-dropdown-menu";
import { Bell } from "lucide-react";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";

type Note = Schemas["NotificationOut"];

/** Notification bell: polls once a minute (and on focus), list of the latest 50. */
export function NotificationBell({ orgId }: { orgId: string }) {
  const t = useTranslations("notifications");
  const format = useFormatter();
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
  const text = (n: Note) => t(n.kind as "assignment", n.params as never);
  return (
    <M.Root>
      <M.Trigger
        aria-label={t("open", { count: unread })}
        className="relative grid size-10 shrink-0 place-items-center rounded-md text-muted hover:bg-surface hover:text-foreground"
        data-testid="bell"
      >
        <Bell aria-hidden className="size-5" strokeWidth={1.8} />
        {unread > 0 && (
          <span
            className="absolute top-1 right-1 grid min-w-[1.125rem] place-items-center rounded-md bg-accent px-1 text-[0.625rem] font-bold leading-[1.125rem] text-accent-contrast ring-2 ring-background"
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
          className="club z-50 w-[22rem] max-w-[calc(100vw-1.5rem)] overflow-hidden rounded-lg bg-raised text-sm shadow-xl ring-1 ring-border animate-fade"
        >
          <div className="flex items-center justify-between border-b border-border/70 px-4 py-3">
            <p className="font-semibold">{t("title")}</p>
            {unread > 0 && (
              <button className="text-xs font-medium text-accent hover:underline" onClick={() => read.mutate([])}>
                {t("markAll")}
              </button>
            )}
          </div>
          <div className="max-h-[26rem] overflow-auto p-1.5">
            {items.length === 0 && <p className="px-3 py-6 text-center text-muted">{t("none")}</p>}
            {items.map((n) => (
              <M.Item key={n.id} asChild>
                <Link
                  href={n.link ?? `/app/${orgId}`}
                  onClick={() => !n.read_at && read.mutate([n.id])}
                  className={cn("flex gap-3 rounded-md px-3 py-2.5 outline-none data-[highlighted]:bg-surface", !n.read_at && "font-medium")}
                >
                  <span aria-hidden className={cn("mt-1.5 size-2 shrink-0 rounded-full", n.read_at ? "bg-transparent" : "bg-accent")} />
                  <span className="min-w-0">
                    {text(n)}
                    <span className="block text-xs font-normal text-muted">{format.relativeTime(new Date(n.created_at))}</span>
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
