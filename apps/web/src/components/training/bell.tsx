"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";

type Note = Schemas["NotificationOut"];

/** Notification bell: polls once a minute (and on focus), dropdown with the latest 50. */
export function NotificationBell({ orgId }: { orgId: string }) {
  const t = useTranslations("notifications");
  const format = useFormatter();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
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
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => !box.current?.contains(e.target as Node) && setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => (document.removeEventListener("mousedown", close), document.removeEventListener("keydown", esc));
  }, [open]);
  const unread = q.data?.unread ?? 0;
  const text = (n: Note) => t(n.kind as "assignment", n.params as never);
  return (
    <div className="relative" ref={box}>
      <button
        aria-label={t("open", { count: unread })}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="relative rounded px-3 py-2 hover:bg-surface"
        data-testid="bell"
      >
        <svg aria-hidden width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
          <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
        </svg>
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 min-w-5 rounded-full bg-accent px-1 text-center text-xs font-semibold text-accent-contrast" data-testid="unread">
            {unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-20 mt-1 w-80 max-w-[90vw] rounded-lg border border-border bg-background p-2 shadow-lg" role="dialog" aria-label={t("title")}>
          <div className="flex items-center justify-between px-2 py-1">
            <p className="font-semibold">{t("title")}</p>
            {unread > 0 && (
              <button className="text-xs underline" onClick={() => read.mutate([])}>
                {t("markAll")}
              </button>
            )}
          </div>
          <ul className="max-h-96 overflow-auto text-sm">
            {(q.data?.items ?? []).length === 0 && <li className="px-2 py-3 text-muted">{t("none")}</li>}
            {(q.data?.items ?? []).map((n) => (
              <li key={n.id}>
                <Link
                  href={n.link ?? `/app/${orgId}`}
                  onClick={() => (setOpen(false), !n.read_at && read.mutate([n.id]))}
                  className={cn("block rounded px-2 py-2 hover:bg-surface", !n.read_at && "font-medium")}
                >
                  {!n.read_at && <span aria-hidden className="mr-1.5 inline-block size-2 rounded-full bg-accent" />}
                  {text(n)}
                  <span className="block text-xs font-normal text-muted">{format.relativeTime(new Date(n.created_at))}</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
