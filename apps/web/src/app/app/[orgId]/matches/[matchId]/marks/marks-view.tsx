"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import type { CSSProperties } from "react";
import { SectionHead } from "@/components/anlauf/blocks";
import { Strip } from "@/components/anlauf/heads";
import { useShell } from "@/components/shell/context";
import { matchStyle } from "@/lib/color";
import { useFormatter, useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/client";
import { flush, mark, pending } from "@handball/client-core";

const SESSION_KEY = (matchId: string) => `hb.marks.session.${matchId}`;

/**
 * Spieltag (SPEC 7.11, addendum 01, 5.3): big keys for courtside marks with the phone's clock,
 * offline first; the head of the match with the score from the goal keys, at the side what was
 * marked. Marks cannot be taken back yet (the API has no delete): a wrong one is ignored in the
 * video. «Pro Spielerin erfassen» opens the detailed capture.
 */
export function MarksView({
  orgId,
  matchId,
  teamId,
  own,
  opp,
  kickoffAt,
  oppColor = null,
}: {
  orgId: string;
  matchId: string;
  teamId: string;
  own: string;
  opp: string;
  kickoffAt: string | null;
  oppColor?: string | null;
}) {
  const t = useTranslations("marks");
  const format = useFormatter();
  const [count, setCount] = useState(0);
  const [open, setOpen] = useState(0);
  const [half, setHalf] = useState(1);
  const session = useRef<string | null>(null);
  // what was marked on this phone, newest first (the queue only holds what is not uploaded yet)
  const [log, setLog] = useState<{ id: string; key: string; label: string; at: Date }[]>([]);
  // what was marked before this page load comes from the server and the offline queue (UX test
  // B03): the score and «Bisher» stay after a reload
  useEffect(() => {
    let off = false;
    const queued = pending(localStorage, matchId).map((q) => ({ id: q.client_id, key: q.key, label: "", at: new Date(q.device_time) }));
    void api
      .GET("/v1/orgs/{org_id}/matches/{match_id}/marks", { params: { path: { org_id: orgId, match_id: matchId } } })
      .then(({ data }) => {
        if (off) return;
        const server = (data?.marks ?? []).map((m) => ({ id: m.id, key: m.key, label: m.label ?? "", at: new Date(m.device_time) }));
        setLog((l) => {
          const all = [...l, ...queued, ...server];
          const seen = new Set<string>();
          return all.filter((x) => (seen.has(x.id) ? false : (seen.add(x.id), true))).sort((a, b) => b.at.getTime() - a.at.getTime());
        });
        if (server.some((m) => m.key === "halftime") || queued.some((m) => m.key === "halftime")) setHalf(2);
      })
      .catch(() => setLog((l) => (l.length ? l : queued)));
    return () => {
      off = true;
    };
  }, [orgId, matchId]);
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 15000);
    return () => window.clearInterval(id);
  }, []);
  const { org } = useShell();
  const style = matchStyle([org.primary_color, org.secondary_color ?? null], oppColor ? [oppColor] : null);
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
    const item = mark(localStorage, matchId, key);
    if (key === "halftime") setHalf(2);
    setLog((l) => [{ id: item.client_id, key, label, at: new Date() }, ...l]);
    setCount((n) => n + 1);
    setOpen(pending(localStorage, matchId).length);
    if (navigator.vibrate) navigator.vibrate(40);
    void sync();
  };

  const list = keys.data ?? [];
  const labelOf = (k: { key: string; label?: string | null }) =>
    k.label || (k.key === "goal_own" && own ? t("goalUs") : k.key === "goal_opp" && opp ? t("goalFor", { team: opp }) : t(`key_${k.key}` as "key_good"));
  const sub = (key: string) => (key === "good" || key === "mistake" ? t("subMark") : key === "defence" || key === "review" ? t("subLater") : null);
  const goals = list.filter((k) => k.key === "goal_own" || k.key === "goal_opp");
  const rest = list.filter((k) => k.key !== "goal_own" && k.key !== "goal_opp");
  const score = { own: log.filter((l) => l.key === "goal_own").length, opp: log.filter((l) => l.key === "goal_opp").length };
  const shown = (l: { key: string; label: string }) => l.label || (l.key === "halftime" ? t("halftime") : labelOf({ key: l.key }));
  const time = (d: Date) => format.dateTime(d, { hour: "2-digit", minute: "2-digit" });
  const back = `/app/${orgId}/matches/${matchId}`;
  return (
    <div style={style as CSSProperties} data-testid="marks">
      {/* full screen: its own narrow top bar, the head of the match, the keys, what was marked */}
      <div className="bleed-x -mt-6 flex h-[60px] items-center justify-between gap-3 border-b-2 border-ink px-4 md:px-8 lg:-mt-8">
        <span className="text-[15px] font-bold">{t("top")}</span>
        <Link href={back} className="inline-flex min-h-11 items-center border-2 border-ink px-3.5 text-[15px] font-bold text-ink no-underline">
          {t("end")}
        </Link>
      </div>
      <div className="bleed-x">
        <Strip
          name={<h1 className="m-0 text-[length:inherit] leading-[inherit]">{own}</h1>}
          sub={[opp && `${t("vs")} ${opp}`, kickoffAt && format.dateTime(new Date(kickoffAt), { weekday: "short", day: "numeric", month: "numeric", hour: "2-digit", minute: "2-digit" })].filter(Boolean).join(" · ")}
          own={score.own}
          opp={score.opp}
        >
          <p className="mt-3 flex items-baseline gap-2 font-sans not-italic">
            <b className="font-num text-[26px] md:text-[34px]">{time(now)}</b>
            <span className="text-[13px] font-semibold md:text-[15px]">{t("half", { n: half })}</span>
          </p>
        </Strip>
      </div>
      <div className="grid gap-x-10 gap-y-8 py-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="min-w-0">
          <div className="grid grid-cols-2 gap-2.5">
            {goals.map((k) => (
              <button
                key={k.key}
                type="button"
                onClick={() => tap(k.key, labelOf(k))}
                className={cn(
                  "min-h-[72px] cursor-pointer border-2 px-3.5 py-2.5 text-left active:scale-[0.98] md:min-h-[88px]",
                  k.key === "goal_own" ? "border-club-edge bg-club text-club-ink" : "border-ink bg-ink text-ground",
                )}
              >
                <span className="font-slant block text-[22px] leading-tight md:text-[28px]">{labelOf(k)}</span>
                <span className="text-[13px] font-semibold md:text-[15px]">{t("sofar", { n: k.key === "goal_own" ? score.own : score.opp })}</span>
              </button>
            ))}
            {rest.map((k) => (
              <button key={k.key} type="button" onClick={() => tap(k.key, labelOf(k))} className="min-h-[72px] cursor-pointer border-2 border-ink bg-transparent px-3.5 py-2.5 text-left text-ink active:scale-[0.98] md:min-h-[88px]">
                <span className="font-slant block text-[20px] leading-tight md:text-[26px]">{labelOf(k)}</span>
                {sub(k.key) && <span className="text-[13px] md:text-[15px]">{sub(k.key)}</span>}
              </button>
            ))}
            <button
              type="button"
              disabled={half === 2}
              onClick={() => tap("halftime", t("halftime"))}
              className="col-span-2 min-h-12 cursor-pointer border-2 border-ink bg-transparent text-[15px] font-bold disabled:cursor-default disabled:opacity-50"
            >
              {half === 2 ? t("secondHalf") : t("halftime")}
            </button>
          </div>
          <p className="mt-4 flex flex-wrap items-baseline justify-between gap-x-4 border-t-2 border-ink pt-3 text-[15px]" aria-live="polite">
            <span>{log[0] ? `${time(log[0].at)} ${shown(log[0])}` : t("noneYet")}</span>
            <a href={`/app/${orgId}/matches/${matchId}/matchday?mode=detail`} data-testid="per-player" className="font-bold text-ink underline decoration-[1.5px] underline-offset-4">
              {t("perPlayer")}
            </a>
          </p>
          <p className="mt-2 text-[13px] text-ink-2">{t("hint")}</p>
        </div>
        <aside className="min-w-0">
          <SectionHead title={t("sofarTitle")} note={t("newestFirst")} />
          {log.length === 0 ? (
            <p className="text-[15px] text-ink-2">{t("noneYet")}</p>
          ) : (
            <ul className="m-0 list-none p-0" data-testid="marks-log">
              {log.slice(0, 12).map((l) => (
                <li key={l.id} className="flex min-h-11 items-center gap-3 border-b border-rule text-[15px]">
                  <b className="font-num w-14">{time(l.at)}</b>
                  {l.key === "goal_own" && <span aria-hidden className="inline-block h-2.5 w-3 -skew-x-12 bg-club-text" />}
                  {l.key === "goal_opp" && <span aria-hidden className="inline-block h-2.5 w-3 -skew-x-12 bg-ink" />}
                  {shown(l)}
                </li>
              ))}
            </ul>
          )}
          <p className="mt-4 text-[13px] text-ink-2">{count === 0 && open === 0 ? "" : open > 0 ? t("pending", { n: open }) : t("synced")}</p>
        </aside>
      </div>
    </div>
  );
}
