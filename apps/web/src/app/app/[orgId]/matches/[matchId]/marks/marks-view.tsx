"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/client";
import { flush, mark, pending } from "@handball/client-core";

const SESSION_KEY = (matchId: string) => `hb.marks.session.${matchId}`;

/** Big buttons for courtside marks with the phone's clock, offline first (addendum 01, 5.3). */
export function MarksView({ orgId, matchId, teamId }: { orgId: string; matchId: string; teamId: string }) {
  const t = useTranslations("marks");
  const [open, setOpen] = useState(0);
  const [last, setLast] = useState<string | null>(null);
  const [half, setHalf] = useState(1);
  const session = useRef<string | null>(null);
  const keys = useQuery({
    queryKey: ["mark-keys", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/mark-keys", { params: { path: { org_id: orgId, team_id: teamId } } })).data ?? [],
    enabled: !!teamId,
  });

  const sync = useCallback(async () => {
    try {
      if (!session.current) session.current = localStorage.getItem(SESSION_KEY(matchId));
      if (!session.current) {
        const r = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/mark-sessions", {
          params: { path: { org_id: orgId, match_id: matchId } },
          body: { device: navigator.userAgent.slice(0, 120) },
        });
        if (!r.data) return;
        session.current = r.data.id;
        localStorage.setItem(SESSION_KEY(matchId), r.data.id);
      }
      const sid = session.current;
      const left = await flush(localStorage, matchId, async (marks) => {
        const r = await api.POST("/v1/orgs/{org_id}/mark-sessions/{session_id}/marks", {
          params: { path: { org_id: orgId, session_id: sid } },
          body: { marks },
        });
        return { ok: !!r.data, stored: r.data ? (r.data as { stored: { client_id: string }[] }).stored.map((s) => s.client_id) : [] };
      });
      setOpen(left);
    } catch {
      setOpen(pending(localStorage, matchId).length);
    }
  }, [orgId, matchId]);

  useEffect(() => {
    setOpen(pending(localStorage, matchId).length);
    void sync();
    const id = window.setInterval(() => void sync(), 15000);
    window.addEventListener("online", sync);
    return () => {
      window.clearInterval(id);
      window.removeEventListener("online", sync);
    };
  }, [matchId, sync]);

  const tap = (key: string, label: string) => {
    mark(localStorage, matchId, key);
    if (key === "halftime") setHalf(2);
    setLast(label);
    setOpen(pending(localStorage, matchId).length);
    if (navigator.vibrate) navigator.vibrate(40);
    void sync();
  };

  const list = keys.data ?? [];
  return (
    <div className="mx-auto max-w-xl space-y-4">
      <div className="flex items-baseline justify-between">
        <h1 className="text-xl font-semibold">{t("title")}</h1>
        <span className="text-sm text-muted" aria-live="polite">
          {open > 0 ? t("pending", { n: open }) : t("synced")}
        </span>
      </div>
      <p className="text-sm text-muted">{t("hint")}</p>
      <div className="grid grid-cols-2 gap-3">
        {list.map((k) => {
          const label = k.label || t(`key_${k.key}`);
          return (
            <button
              key={k.key}
              type="button"
              onClick={() => tap(k.key, label)}
              className="min-h-24 rounded-md border-2 px-3 text-lg font-semibold active:scale-[0.98]"
              style={{ borderColor: k.color ?? "var(--border)" }}
            >
              {label}
            </button>
          );
        })}
      </div>
      <button
        type="button"
        disabled={half === 2}
        onClick={() => tap("halftime", t("halftime"))}
        className="w-full rounded-md border border-border py-3 text-sm disabled:opacity-50"
      >
        {half === 2 ? t("secondHalf") : t("halftime")}
      </button>
      <p className="min-h-6 text-center text-sm" aria-live="polite">
        {last ? t("marked", { label: last }) : ""}
      </p>
    </div>
  );
}
