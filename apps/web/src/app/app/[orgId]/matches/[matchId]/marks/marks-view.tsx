"use client";

import { useQuery } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/client";
import { flush, mark, pending } from "@handball/client-core";

const SESSION_KEY = (matchId: string) => `hb.marks.session.${matchId}`;

/** Big buttons for courtside marks with the phone's clock, offline first (addendum 01, 5.3). */
export function MarksView({
  orgId,
  matchId,
  teamId,
  own,
  opp,
  kickoffAt,
}: {
  orgId: string;
  matchId: string;
  teamId: string;
  own: string;
  opp: string;
  kickoffAt: string | null;
}) {
  const t = useTranslations("marks");
  const format = useFormatter();
  const [count, setCount] = useState(0);
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
    setLast(t("lastAt", { label, time: format.dateTime(new Date(), { hour: "2-digit", minute: "2-digit", second: "2-digit" }) }));
    setCount((n) => n + 1);
    setOpen(pending(localStorage, matchId).length);
    if (navigator.vibrate) navigator.vibrate(40);
    void sync();
  };

  const list = keys.data ?? [];
  return (
    <div className="mx-auto max-w-xl space-y-4">
      <div className="space-y-1">
        <h1 className="text-xl font-semibold">{t("title")}</h1>
        {/* which match, so a coach with two games in a day marks the right one */}
        {opp && (
          <p className="text-sm text-muted">
            {[own && `${own} ${t("vs")} ${opp}`, kickoffAt && format.dateTime(new Date(kickoffAt), { weekday: "short", day: "numeric", month: "numeric", hour: "2-digit", minute: "2-digit" }), t("half", { n: half })]
              .filter(Boolean)
              .join(" · ")}
          </p>
        )}
      </div>
      {/* what the last tap did: a count, the last mark with its time, and the upload state */}
      <p className="flex flex-wrap items-baseline justify-between gap-x-4 border-y border-foreground/15 py-2 text-sm" aria-live="polite">
        <span>{count > 0 ? `${t("count", { n: count })} · ${last}` : t("noneYet")}</span>
        <span className="text-muted">{count === 0 && open === 0 ? "" : open > 0 ? t("pending", { n: open }) : t("synced")}</span>
      </p>
      <p className="text-sm text-muted">{t("hint")}</p>
      <div className="grid grid-cols-2 gap-3">
        {list.map((k) => {
          // the team's name instead of "wir" and "Gegner"
          const label =
            k.label ||
            (k.key === "goal_own" && own ? t("goalFor", { team: own }) : k.key === "goal_opp" && opp ? t("goalFor", { team: opp }) : t(`key_${k.key}`));
          return (
            <button
              key={k.key}
              type="button"
              onClick={() => tap(k.key, label)}
              // one ink outline for all; the word says the meaning, red only for a goal against
              className={cn(
                "min-h-24 border-2 border-foreground/25 px-3 text-lg font-semibold active:scale-[0.98] active:bg-surface",
                k.key === "goal_opp" && "border-error/60 text-error",
              )}
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
        className="w-full border border-border py-3 text-sm disabled:opacity-50"
      >
        {half === 2 ? t("secondHalf") : t("halftime")}
      </button>

    </div>
  );
}
