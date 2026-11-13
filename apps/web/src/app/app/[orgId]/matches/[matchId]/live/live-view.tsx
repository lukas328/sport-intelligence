"use client";

import { Check, Clock3 } from "lucide-react";
import type { Schemas } from "@handball/api-client";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { api } from "@/lib/client";
import { adjust, clockSeconds, enqueue, flush, load, remove, toggle, type Clock } from "@/lib/live-queue";
import { cn } from "@/lib/utils";
import { useOptionalShell } from "@/components/shell/context";
import { matchStyle } from "@/lib/color";
import { useOpponentName } from "@/lib/opponent";

type Match = Schemas["MatchOut"];
type Roster = Schemas["RosterEntryOut"][];
type Logged = { client_id: string; id?: string; side: "own" | "opponent"; label: string; goal: boolean; clock: string; synced: boolean };
type Action = { key: string; label: string; body: Record<string, unknown>; goal?: boolean };

/** The first visit happens before the service worker controls the page: cache this page and the
 * scripts it already loaded, so a reload in the hall works without connection. */
async function precache(): Promise<void> {
  if (!("caches" in window)) return;
  const cache = await caches.open("hb-live-v1");
  const assets = performance
    .getEntriesByType("resource")
    .map((e) => e.name)
    .filter((u) => u.startsWith(`${location.origin}/_next/static/`));
  await Promise.all([cache.add(location.href), ...assets.map((u) => cache.add(u).catch(() => undefined))]);
}

const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const store = () => (typeof window === "undefined" ? { getItem: () => null, setItem: () => undefined } : window.localStorage);

function useCached<T>(key: string, fetcher: () => Promise<T | undefined>, ready = true): T | null {
  const [value, setValue] = useState<T | null>(() => {
    try {
      const raw = window.localStorage.getItem(key);
      return raw ? (JSON.parse(raw) as T) : null;
    } catch {
      return null;
    }
  });
  useEffect(() => {
    if (!ready) return;
    void fetcher()
      .then((v) => {
        if (v === undefined) return;
        setValue(v);
        try {
          window.localStorage.setItem(key, JSON.stringify(v));
        } catch {
          /* ignore */
        }
      })
      .catch(() => undefined); // offline: keep the cached copy
  }, [key, ready]); // eslint-disable-line react-hooks/exhaustive-deps
  return value;
}

/**
 * Courtside live tagging (phone or tablet): running match clock, big buttons, offline queue.
 * Events carry the match clock (no video time); kickoff marks align them with a video later.
 */
export function LiveView({ orgId, matchId }: { orgId: string; matchId: string }) {
  const t = useTranslations("live");
  const oppName = useOpponentName();
  const shell = useOptionalShell();
  const ownName = shell?.team?.name ?? null;
  const te = useTranslations("events");
  const path = { org_id: orgId, match_id: matchId };
  const match = useCached<Match>(`hb.live.match.${matchId}`, async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}", { params: { path } })).data);
  const roster = useCached<Roster>(
    `hb.live.roster.${matchId}`,
    async () => {
      if (!match) return undefined;
      return (
        await api.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster", {
          params: { path: { org_id: orgId, team_id: match.team_id, season_id: match.season_id } },
        })
      ).data;
    },
    match !== null,
  );
  const clockKey = `hb.live.clock.${matchId}`;
  const [clock, setClockState] = useState<Clock>(() => {
    try {
      return (JSON.parse(window.localStorage.getItem(clockKey) ?? "null") as Clock | null) ?? { period: 1, base_s: 0, started_at: null };
    } catch {
      return { period: 1, base_s: 0, started_at: null };
    }
  });
  const setClock = (c: Clock) => {
    setClockState(c);
    try {
      window.localStorage.setItem(clockKey, JSON.stringify(c));
    } catch {
      /* ignore */
    }
  };
  const [, tick] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => tick((n) => n + 1), 500);
    return () => window.clearInterval(id);
  }, []);
  const [player, setPlayer] = useState<string | null>(null);
  const [oppNumber, setOppNumber] = useState("");
  const [seven, setSeven] = useState(false);
  const [log, setLog] = useState<Logged[]>(() =>
    load(store(), matchId).map((q) => ({
      client_id: q.client_id,
      side: q.body.side as "own" | "opponent",
      label: String(q.body.__label ?? ""),
      goal: q.body.outcome === "goal",
      clock: fmt(Number(q.body.clock_s ?? 0)),
      synced: false,
    })),
  );
  const [online, setOnline] = useState(true);
  const [rejected, setRejected] = useState(0);
  const syncing = useRef(false);

  const sync = useCallback(async () => {
    if (syncing.current) return;
    syncing.current = true;
    try {
      const r = await flush(store(), matchId, async (body) => {
        const { __label: _label, ...clean } = body;
        void _label;
        const res = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/events", {
          params: { path },
          body: clean as Schemas["EventIn"],
        });
        return { ok: !res.error, status: res.response.status, id: res.data?.id };
      });
      setOnline(r.pending === 0 || r.sent.length > 0);
      if (r.rejected.length) setRejected((n) => n + r.rejected.length);
      if (r.sent.length || r.rejected.length) {
        const sent = new Map(r.sent.map((s) => [s.client_id, s.id]));
        const dropped = new Set(r.rejected.map((x) => x.client_id));
        setLog((l) => l.filter((e) => !dropped.has(e.client_id)).map((e) => (sent.has(e.client_id) ? { ...e, synced: true, id: sent.get(e.client_id) } : e)));
      }
    } catch {
      setOnline(false);
    } finally {
      syncing.current = false;
    }
  }, [matchId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    void sync();
    const id = window.setInterval(() => void sync(), 5000);
    const on = () => void sync();
    window.addEventListener("online", on);
    if ("serviceWorker" in navigator) {
      void navigator.serviceWorker
        .register("/sw.js")
        .then(() => navigator.serviceWorker.ready)
        .then(() => precache())
        .catch(() => undefined);
    }
    return () => (window.clearInterval(id), window.removeEventListener("online", on));
  }, [sync]);

  const players = useMemo(
    () => (roster ?? []).filter((r) => r.active).sort((a, b) => (a.jersey_number ?? 999) - (b.jersey_number ?? 999)),
    [roster],
  );
  const pending = log.filter((e) => !e.synced).length;
  const score = useMemo(() => ({ own: log.filter((e) => e.goal && e.side === "own").length, opp: log.filter((e) => e.goal && e.side === "opponent").length }), [log]);
  const seconds = clockSeconds(clock);
  const playerLabel = (id: string | null) => {
    const p = players.find((x) => x.player_id === id);
    return p ? `#${p.jersey_number ?? "?"} ${p.first_name}` : "";
  };

  function record(side: "own" | "opponent", label: string, body: Record<string, unknown>, goal = false) {
    const clockS = Math.round(seconds);
    const full: Record<string, unknown> = {
      side,
      period: clock.period,
      // match clock over all periods; period length from the match format (addendum 01, 4.8)
      clock_s: clockS + (clock.period - 1) * (match?.period_s ?? 1800),
      player_id: side === "own" ? player : null,
      number: side === "opponent" && oppNumber ? Number(oppNumber) : null,
      ...body,
      __label: label,
    };
    if (seven && body.type === "shot") full.shot_type = "penalty";
    const item = enqueue(store(), matchId, full);
    setLog((l) => [{ client_id: item.client_id, side, label: `${label}${side === "own" && player ? ` ${playerLabel(player)}` : ""}`, goal, clock: fmt(seconds), synced: false }, ...l]);
    setSeven(false);
    void sync();
  }

  async function undo() {
    const last = log[0];
    if (!last) return;
    setLog((l) => l.slice(1));
    if (!last.synced) return remove(store(), matchId, last.client_id);
    if (last.id) await api.DELETE("/v1/orgs/{org_id}/events/{event_id}", { params: { path: { org_id: orgId, event_id: last.id } } });
  }

  const own: Action[] = [
    { key: "goal", label: te("goal"), body: { type: "shot", outcome: "goal" }, goal: true },
    { key: "miss", label: te("miss"), body: { type: "shot", outcome: "miss" } },
    { key: "save", label: t("savedByKeeper"), body: { type: "shot", outcome: "save" } },
    { key: "post", label: te("post"), body: { type: "shot", outcome: "post" } },
    { key: "turnover", label: te("turnover"), body: { type: "turnover", turnover_type: "other" } },
    { key: "two", label: te("suspension"), body: { type: "suspension_2min" } },
  ];
  const opp: Action[] = [
    { key: "goal", label: t("goalAgainst"), body: { type: "shot", outcome: "goal" }, goal: true },
    { key: "save", label: t("ourSave"), body: { type: "shot", outcome: "save" } },
    { key: "miss", label: t("oppMiss"), body: { type: "shot", outcome: "miss" } },
    { key: "turnover", label: t("oppTurnover"), body: { type: "turnover", turnover_type: "other" } },
    { key: "two", label: t("oppTwo"), body: { type: "suspension_2min" } },
  ];

  // what was captured before this page load comes from the server (UX test B03): the score and
  // the list stay after a reload, and nobody captures the same goal twice
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    let off = false;
    void api
      .GET("/v1/orgs/{org_id}/matches/{match_id}/events", { params: { path } })
      .then(({ data }) => {
        if (off || !data) return;
        const live = data.filter((e) => e.client_id && (e.type === "shot" || e.type === "turnover" || e.type === "suspension_2min"));
        const labelOf = (e: (typeof live)[number]) => {
          const list = e.side === "own" ? own : opp;
          const hit = list.find((a) => a.body.type === e.type && (a.body.outcome == null || a.body.outcome === e.outcome));
          const who = e.side === "own" ? playerLabel(e.player_id ?? null) : e.number != null ? `#${e.number}` : "";
          return [hit?.label ?? e.type, who].filter(Boolean).join(" ");
        };
        const periodLen = match?.period_s ?? 1800;
        const fromServer: Logged[] = live
          .sort((a, b) => (b.clock_s ?? 0) - (a.clock_s ?? 0))
          .map((e) => ({
            client_id: e.client_id!,
            id: e.id,
            side: e.side as "own" | "opponent",
            label: labelOf(e),
            goal: e.type === "shot" && e.outcome === "goal",
            clock: fmt(Math.max(0, (e.clock_s ?? 0) - ((e.period ?? 1) - 1) * periodLen)),
            synced: true,
          }));
        setLog((l) => {
          const known = new Set(l.map((x) => x.client_id));
          return [...l, ...fromServer.filter((x) => !known.has(x.client_id))];
        });
        setLoaded(true);
      })
      .catch(() => setLoaded(true));
    return () => {
      off = true;
    };
  }, [roster, match?.period_s]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      className="mx-auto max-w-xl space-y-4 pb-24"
      data-testid="live"
      data-loaded={loaded ? "" : undefined}
      style={
        matchStyle(
          [shell?.org.primary_color ?? null, shell?.org.secondary_color ?? null],
          match?.opponent_colors ? [match.opponent_colors.color, match.opponent_colors.second ?? null] : null,
        ) as CSSProperties
      }
    >
      {/* head and actions only stick where the window is tall enough for both and the players
          between them (UX test H01: phone held sideways, 200 % zoom) */}
      <div className="z-10 -mx-4 space-y-2 [@media(min-height:600px)]:sticky [@media(min-height:600px)]:top-0 border-b border-border/70 bg-background/90 backdrop-blur-xl px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <Link href={`/app/${orgId}/matches/${matchId}`} className="text-sm underline">
            {t("back")}
          </Link>
          <span className={cn("px-2 py-0.5 text-xs", pending ? "border border-accent" : "bg-surface")} data-testid="sync-state" aria-live="polite">
            {pending ? (online ? t("syncing", { count: pending }) : t("offline", { count: pending })) : t("synced")}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <p className="font-score text-6xl leading-none" data-testid="live-score">
            {score.own}:{score.opp}
          </p>
          <div className="text-right">
            <p className="font-score text-5xl leading-none" data-testid="live-clock">
              {fmt(seconds)}
            </p>
            <p className="text-xs text-muted">{t("period", { period: clock.period })}</p>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-1">
          <button className="col-span-2 min-h-12 border-2 border-ink bg-ink px-3 font-bold text-ground" onClick={() => setClock(toggle(clock))}>
            {clock.started_at !== null ? t("pause") : t("start")}
          </button>
          <button className="min-h-12 border-2 border-ink font-bold" onClick={() => setClock(adjust(clock, -10))} aria-label={t("minus10")}>
            −10 s
          </button>
          <button className="min-h-12 border-2 border-ink font-bold" onClick={() => setClock(adjust(clock, 10))} aria-label={t("plus10")}>
            +10 s
          </button>
        </div>
        {clock.period < (match?.periods ?? 2) && seconds >= 60 && (
          <button
            className="w-full ring-1 ring-inset ring-border py-2 text-sm"
            onClick={() => setClock({ period: clock.period + 1, base_s: 0, started_at: null })}
          >
            {t("secondHalf")}
          </button>
        )}
        {match && <p className="truncate text-xs text-muted">{t("vs", { opponent: oppName(match) })}</p>}
      </div>

      <section aria-label={t("own")} className="space-y-2">
        <h2 className="font-semibold">{ownName ?? t("own")}</h2>
        <div className="grid grid-cols-4 gap-1 sm:grid-cols-6" role="group" aria-label={t("player")}>
          {players.map((p) => (
            <button
              key={p.player_id}
              aria-pressed={player === p.player_id}
              onClick={() => setPlayer((cur) => (cur === p.player_id ? null : p.player_id))}
              className={cn("min-h-14 border py-2 text-sm", player === p.player_id ? "border-foreground bg-foreground text-background" : "border-border bg-raised hover:bg-surface")}
            >
              <span className="block text-lg font-bold tabular-nums">{p.jersey_number ?? "?"}</span>
              <span className="block truncate text-xs">{p.first_name}</span>
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={seven} onChange={(e) => setSeven(e.target.checked)} />
          {te("penaltyShot")}
        </label>
        {/* the actions stay at the thumb while the player grid scrolls; the own goal in ink (red
            means a goal against) */}
        <div className="z-10 grid grid-cols-3 gap-1 bg-background/95 py-1 backdrop-blur [@media(min-height:600px)]:sticky [@media(min-height:600px)]:bottom-2">
          {own.map((a) => (
            <button key={a.key} onClick={() => record("own", a.label, a.body, a.goal)} className={cn("min-h-[88px] border-2 px-3 text-base font-bold", a.goal ? "border-club-edge bg-club text-club-ink" : "border-ink bg-transparent text-ink")}>
              {a.label}
            </button>
          ))}
        </div>
      </section>

      <section aria-label={t("opponent")} className="space-y-2">
        <h2 className="font-semibold">{match ? oppName(match) : t("opponent")}</h2>
        <label className="flex items-center gap-2 text-sm">
          {te("opponentNumber")}
          <input inputMode="numeric" value={oppNumber} onChange={(e) => setOppNumber(e.target.value.replace(/\D/g, "").slice(0, 2))} className="min-h-10 w-16 bg-raised ring-1 ring-inset ring-border px-2" />
        </label>
        <div className="grid grid-cols-3 gap-1">
          {opp.map((a) => (
            <button
              key={a.key}
              onClick={() => record("opponent", a.label, a.body, a.goal)}
              className={cn(
                "min-h-[88px] border-2 border-ink px-3 text-base font-bold",
                // the opponent's goal in ink with its colour as a band (SPEC 7.11)
                a.goal ? "bg-ink text-ground shadow-[inset_0_-10px_0_var(--opp),inset_0_-12px_0_var(--opp-edge)]" : "bg-transparent text-ink",
              )}
            >
              {a.label}
            </button>
          ))}
        </div>
      </section>

      <section aria-label={t("log")} className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">{t("log")}</h2>
          <button className="ring-1 ring-inset ring-border px-3 py-2 text-sm" onClick={() => void undo()} disabled={log.length === 0}>
            {t("undo")}
          </button>
        </div>
        {rejected > 0 && <p className="text-sm text-error">{t("rejected", { count: rejected })}</p>}
        {log.length === 0 && <p className="text-sm text-muted">{t("logEmpty")}</p>}
        <ol className="space-y-1 text-sm" data-testid="live-log">
          {log.slice(0, 30).map((e) => (
            <li key={e.client_id} className="flex justify-between gap-2 bg-surface px-2 py-1.5">
              <span>
                <span className="mr-2 font-score text-xs text-muted tabular-nums">{e.clock}</span>
                {e.label}
              </span>
              <span className="text-xs text-muted">{e.synced ? <Check aria-label={t("eventSynced")} className="size-3.5 text-ok" /> : <Clock3 aria-label={t("eventPending")} className="size-3.5" />}</span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
