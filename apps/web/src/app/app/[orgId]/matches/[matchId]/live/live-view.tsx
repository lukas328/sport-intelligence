"use client";

import type { Schemas } from "@handball/api-client";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/client";
import { adjust, clockSeconds, enqueue, flush, load, remove, toggle, type Clock } from "@/lib/live-queue";
import { cn } from "@/lib/utils";

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
      clock_s: clock.period === 2 ? clockS + 1800 : clockS,
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

  return (
    <div className="mx-auto max-w-xl space-y-4 pb-24" data-testid="live">
      <div className="sticky top-0 z-10 -mx-4 space-y-2 border-b border-border bg-background px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <Link href={`/app/${orgId}/matches/${matchId}`} className="text-sm underline">
            {t("back")}
          </Link>
          <span className={cn("rounded-full px-2 py-0.5 text-xs", pending ? "border border-accent" : "bg-surface")} data-testid="sync-state" aria-live="polite">
            {pending ? (online ? t("syncing", { count: pending }) : t("offline", { count: pending })) : t("synced")}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <p className="text-4xl font-bold tabular-nums" data-testid="live-score">
            {score.own}:{score.opp}
          </p>
          <div className="text-right">
            <p className="font-mono text-3xl tabular-nums" data-testid="live-clock">
              {fmt(seconds)}
            </p>
            <p className="text-xs text-muted">{t("period", { period: clock.period })}</p>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-1">
          <button className="col-span-2 rounded-md bg-accent px-3 py-3 font-semibold text-accent-contrast" onClick={() => setClock(toggle(clock))}>
            {clock.started_at !== null ? t("pause") : t("start")}
          </button>
          <button className="rounded-md border border-border py-3" onClick={() => setClock(adjust(clock, -10))} aria-label={t("minus10")}>
            −10 s
          </button>
          <button className="rounded-md border border-border py-3" onClick={() => setClock(adjust(clock, 10))} aria-label={t("plus10")}>
            +10 s
          </button>
        </div>
        {clock.period === 1 && seconds >= 60 && (
          <button className="w-full rounded-md border border-border py-2 text-sm" onClick={() => setClock({ period: 2, base_s: 0, started_at: null })}>
            {t("secondHalf")}
          </button>
        )}
        {match && <p className="truncate text-xs text-muted">{t("vs", { opponent: match.opponent.name })}</p>}
      </div>

      <section aria-label={t("own")} className="space-y-2">
        <h2 className="font-semibold">{t("own")}</h2>
        <div className="grid grid-cols-4 gap-1 sm:grid-cols-6" role="group" aria-label={t("player")}>
          {players.map((p) => (
            <button
              key={p.player_id}
              aria-pressed={player === p.player_id}
              onClick={() => setPlayer((cur) => (cur === p.player_id ? null : p.player_id))}
              className={cn("rounded-md border py-2 text-sm", player === p.player_id ? "border-accent bg-accent text-accent-contrast" : "border-border")}
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
        <div className="grid grid-cols-3 gap-1">
          {own.map((a) => (
            <button key={a.key} onClick={() => record("own", a.label, a.body, a.goal)} className={cn("rounded-md py-4 text-base font-semibold", a.goal ? "bg-accent text-accent-contrast" : "border border-border")}>
              {a.label}
            </button>
          ))}
        </div>
      </section>

      <section aria-label={t("opponent")} className="space-y-2">
        <h2 className="font-semibold">{t("opponent")}</h2>
        <label className="flex items-center gap-2 text-sm">
          {te("opponentNumber")}
          <input inputMode="numeric" value={oppNumber} onChange={(e) => setOppNumber(e.target.value.replace(/\D/g, "").slice(0, 2))} className="min-h-10 w-16 rounded-md border border-border bg-background px-2" />
        </label>
        <div className="grid grid-cols-3 gap-1">
          {opp.map((a) => (
            <button key={a.key} onClick={() => record("opponent", a.label, a.body, a.goal)} className="rounded-md border border-border py-4 text-base font-semibold">
              {a.label}
            </button>
          ))}
        </div>
      </section>

      <section aria-label={t("log")} className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">{t("log")}</h2>
          <button className="rounded-md border border-border px-3 py-2 text-sm" onClick={() => void undo()} disabled={log.length === 0}>
            {t("undo")}
          </button>
        </div>
        {rejected > 0 && <p className="text-sm text-error">{t("rejected", { count: rejected })}</p>}
        <ol className="space-y-1 text-sm" data-testid="live-log">
          {log.slice(0, 30).map((e) => (
            <li key={e.client_id} className="flex justify-between gap-2 rounded bg-surface px-2 py-1.5">
              <span>
                <span className="mr-2 font-mono text-xs text-muted">{e.clock}</span>
                {e.label}
              </span>
              <span className="text-xs text-muted">{e.synced ? "✓" : "…"}</span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
