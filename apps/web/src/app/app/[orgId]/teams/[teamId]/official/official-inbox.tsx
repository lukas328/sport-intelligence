"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Lock, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useFormatter, useNow, useTranslations } from "next-intl";
import { useState } from "react";
import { Button, buttonClass } from "@/components/ui/button";
import { Alert, EmptyState } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { duplicateNumbers, groupSuggestions, parseNumber, rosterStats, sevenM, standingByRank, type Suggestion } from "@/lib/official-suggestions";
import { cn } from "@/lib/utils";

const str = (v: unknown) => (typeof v === "string" ? v : "");
const num = (v: unknown) => (typeof v === "number" ? v : null);

/** The team's link to the official data and what it proposes: confirm the squad, import the
 * reports of played games, take schedule changes. Organisers only; a team made by hand says so. */
export function OfficialInbox({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("official");
  const tr = useTranslations();
  const format = useFormatter();
  const now = useNow({ updateInterval: 60_000 });
  const qc = useQueryClient();
  const path = { org_id: orgId, team_id: teamId };
  const [error, setError] = useState<ErrorKey | null>(null);
  const [said, setSaid] = useState<string | null>(null);
  // shirt numbers typed for new players, by suggestion id; unchecked rows are left for later
  const [numbers, setNumbers] = useState<Record<string, string>>({});
  // ticked or not, by suggestion id; untouched rows: ticked when the player has played
  const [picked, setPicked] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);

  const link = useQuery({
    queryKey: ["official-link", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/official", { params: { path } })).data ?? null,
  });
  const list = useQuery({
    queryKey: ["official-suggestions", teamId],
    enabled: link.data?.linked === true,
    queryFn: async () => {
      const r = await api.GET("/v1/orgs/{org_id}/teams/{team_id}/official/suggestions", { params: { path, query: { status: "open" } } });
      if (r.error) throw r.error;
      return r.data ?? [];
    },
  });
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["official-suggestions", teamId] });
    void qc.invalidateQueries({ queryKey: ["official-link", teamId] });
  };
  const stats = useMutation({
    mutationFn: async (on: boolean) => {
      const r = await api.PATCH("/v1/orgs/{org_id}/teams/{team_id}/official", { params: { path }, body: { roster_stats: on } });
      if (r.error) throw r.error;
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["official-link", teamId] }),
    onError: (e) => setError(errorKey(e)),
  });
  const sync = useMutation({
    mutationFn: async () => {
      const r = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/official/sync", { params: { path } });
      if (r.error) throw r.error;
    },
    onSuccess: () => (setSaid(t("synced")), refresh()),
    onError: (e) => setError(errorKey(e)),
  });

  async function decide(s: Suggestion, accept: boolean, body?: { jersey_number: number | null }) {
    const p = { params: { path: { ...path, suggestion_id: s.id } } };
    const r = accept
      ? await api.POST("/v1/orgs/{org_id}/teams/{team_id}/official/suggestions/{suggestion_id}/accept", { ...p, body: body ?? null })
      : await api.POST("/v1/orgs/{org_id}/teams/{team_id}/official/suggestions/{suggestion_id}/dismiss", p);
    if (r.error) {
      setError(errorKey(r.error));
      return false;
    }
    return true;
  }
  async function one(s: Suggestion, accept: boolean) {
    setError(null);
    if (await decide(s, accept)) {
      setSaid(accept ? t("accepted") : t("dismissed"));
      refresh();
      // a report or a new game shows up on the fixtures and the match page
      void qc.invalidateQueries({ queryKey: ["matches"] });
    }
  }
  // the squad in one go: every checked new player with the number typed, one request each
  async function takeSquad(rows: Suggestion[]) {
    setError(null);
    setBusy(true);
    let n = 0;
    for (const s of rows) {
      const typed = numbers[s.id];
      const jersey = typed == null ? num(s.payload.jersey_number) : parseNumber(typed);
      if (jersey === undefined) continue; // an invalid number stays for the coach to fix
      if (await decide(s, true, { jersey_number: jersey })) n++;
    }
    setBusy(false);
    setSaid(t("squadTaken", { n }));
    void qc.invalidateQueries({ queryKey: ["roster"] });
    refresh();
  }

  if (link.isPending) return null;
  const l = link.data;
  const header = <PageHeader eyebrow={[t("eyebrow"), ...(l?.linked ? [l.league, l.group_name] : [])].filter(Boolean).join(" · ")} title={t("title")} />;
  if (!l?.linked)
    return (
      <div className="space-y-6">
        {header}
        <EmptyState title={t("notLinked")}>{t("notLinkedHint")}</EmptyState>
      </div>
    );

  const g = groupSuggestions(list.data ?? []);
  const adds = g.roster.filter((s) => s.kind === "roster_add");
  const isPicked = (s: Suggestion) => picked[s.id] ?? (num(s.payload.appearances) ?? 0) > 0;
  const chosen = adds.filter(isPicked);
  const numberOf = (s: Suggestion) => (numbers[s.id] != null ? parseNumber(numbers[s.id]!) : num(s.payload.jersey_number));
  const invalid = chosen.filter((s) => numberOf(s) === undefined);
  const twice = duplicateNumbers(chosen.map(numberOf));
  const showStats = l.roster_stats === true;
  const anyStats = adds.some((s) => rosterStats(s) != null);
  const date = (iso: string) => (iso ? format.dateTime(new Date(iso), { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "");
  const who = (s: Suggestion) => `${str(s.payload.first_name)} ${str(s.payload.last_name)}`.trim();
  const own = l.official_team_id;
  const nothing = !list.isPending && g.roster.length + g.reports.length + g.schedule.length + g.seasons.length === 0;

  return (
    <div className="space-y-8">
      {header}
      <p className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted">
        {l.synced_at && t("syncedAt", { when: format.relativeTime(new Date(l.synced_at), now) })}
        <Button variant="quiet" size="sm" loading={sync.isPending} onClick={() => sync.mutate()}>
          <RefreshCw aria-hidden />
          {t("syncNow")}
        </Button>
      </p>
      <div aria-live="polite" className="space-y-2">
        {said && <p className="text-sm text-ok">{said}</p>}
        {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      </div>
      {nothing && <p className="text-[0.9375rem]">{t("nothingOpen")}</p>}

      {g.roster.length > 0 && (
        <section className="space-y-3" aria-labelledby="official-squad" data-testid="official-squad">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="space-y-1">
              <h2 id="official-squad" className="text-2xl">
                {t("squad")}
              </h2>
              <p className="text-sm text-muted">{t("squadHint")}</p>
              {adds.some((s) => (num(s.payload.appearances) ?? 0) === 0) && <p className="text-sm text-muted">{t("noAppearancesHint")}</p>}
            </div>
            {/* the coach decides whether figures from the official games sit next to the names */}
            <label className="flex items-center gap-2 text-sm font-medium">
              <input
                type="checkbox"
                className="size-4 accent-[var(--foreground)]"
                checked={showStats}
                disabled={stats.isPending}
                onChange={(e) => stats.mutate(e.target.checked)}
                data-testid="roster-stats"
              />
              {t("showStats")}
            </label>
          </div>
          {adds.length > 0 && (
            <div className="sheet overflow-x-auto">
              <table className="w-full text-[0.9375rem]">
                <caption className="sr-only">{t("squad")}</caption>
                <thead>
                  <tr>
                    <th scope="col" className="w-10">
                      <span className="sr-only">{t("take")}</span>
                    </th>
                    <th scope="col" className="text-left">
                      {t("name")}
                    </th>
                    <th scope="col">{t("number")}</th>
                    <th scope="col">{t("appearances")}</th>
                    {showStats && (
                      <>
                        <th scope="col">{t("goals")}</th>
                        <th scope="col">{t("sevenM")}</th>
                        <th scope="col">{t("twoMin")}</th>
                        <th scope="col">{t("saves")}</th>
                      </>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {adds.map((s) => {
                    const st = rosterStats(s);
                    const typed = numbers[s.id] ?? (num(s.payload.jersey_number)?.toString() ?? "");
                    const n = parseNumber(typed);
                    const bad = n === undefined || (n != null && isPicked(s) && twice.has(n));
                    return (
                      <tr key={s.id} className={cn(!isPicked(s) && "text-muted")} data-testid="roster-suggestion">
                        <td>
                          <input
                            type="checkbox"
                            className="size-4 accent-[var(--foreground)]"
                            checked={isPicked(s)}
                            onChange={(e) => setPicked({ ...picked, [s.id]: e.target.checked })}
                            aria-label={t("takePlayer", { name: who(s) })}
                          />
                        </td>
                        <th scope="row" className="text-left font-medium">
                          {who(s)}
                        </th>
                        <td>
                          <input
                            value={typed}
                            onChange={(e) => setNumbers({ ...numbers, [s.id]: e.target.value })}
                            inputMode="numeric"
                            maxLength={2}
                            aria-label={t("numberOf", { name: who(s) })}
                            aria-invalid={bad || undefined}
                            className="h-9 w-14 bg-raised px-2 text-center font-score tabular-nums ring-1 ring-foreground/20 ring-inset focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-none aria-[invalid=true]:ring-error"
                          />
                        </td>
                        <td className="tabular-nums">{num(s.payload.appearances) ?? "-"}</td>
                        {showStats && (
                          <>
                            <td className="tabular-nums">{st?.goals ?? "-"}</td>
                            <td className="tabular-nums">{sevenM(st)}</td>
                            <td className="tabular-nums">{st?.suspensions_2min ?? "-"}</td>
                            <td className="tabular-nums">{st?.goalkeeper ? (st.saves ?? "-") : ""}</td>
                          </>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          {showStats && !anyStats && <p className="text-xs text-muted">{t("noStatsYet")}</p>}
          {adds.length > 0 && (
            <div className="flex flex-wrap items-center gap-3">
              <Button loading={busy} disabled={chosen.length === 0 || invalid.length > 0 || twice.size > 0} onClick={() => void takeSquad(chosen)} data-testid="take-squad">
                {t("takeSquad", { n: chosen.length })}
              </Button>
              {invalid.length > 0 && <span className="text-sm text-error">{t("numberInvalid")}</span>}
              {twice.size > 0 && <span className="text-sm text-error">{t("numberTwice", { numbers: [...twice].sort((a, b) => a - b).join(", ") })}</span>}
            </div>
          )}
          {/* changes to players already in the squad, one decision each */}
          {g.roster.filter((s) => s.kind !== "roster_add").length > 0 && (
            <ul className="divide-y divide-foreground/10 border-t-2 border-foreground">
              {g.roster
                .filter((s) => s.kind !== "roster_add")
                .map((s) => (
                  <li key={s.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 py-2.5">
                    <span className="min-w-0 flex-1">
                      {s.kind === "roster_number"
                        ? t("numberChange", { name: who(s), from: num(s.payload.from) ?? "-", to: num(s.payload.to) ?? "-" })
                        : t("left", { name: who(s) })}
                    </span>
                    <Button size="sm" variant="secondary" onClick={() => void one(s, true)}>
                      {s.kind === "roster_left" ? t("remove") : t("accept")}
                    </Button>
                    <Button size="sm" variant="quiet" onClick={() => void one(s, false)}>
                      {s.kind === "roster_left" ? t("keep") : t("dismiss")}
                    </Button>
                  </li>
                ))}
            </ul>
          )}
        </section>
      )}

      {g.reports.length > 0 && (
        <section className="space-y-3" aria-labelledby="official-reports" data-testid="official-reports">
          <div className="space-y-1">
            <h2 id="official-reports" className="text-2xl">
              {t("reports")}
            </h2>
            <p className="text-sm text-muted">{t("reportsHint")}</p>
          </div>
          <ul className="divide-y divide-foreground/10 border-t-2 border-foreground">
            {g.reports.map((s) => (
              <li key={s.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 py-2.5">
                <span className="min-w-0 flex-1">
                  <span className="block font-medium">
                    {t(s.payload.is_home ? "home" : "away", { opponent: str(s.payload.opponent) })}
                  </span>
                  <span className="block text-sm text-muted">{date(str(s.payload.kickoff_at))}</span>
                </span>
                {num(s.payload.score_own) != null && (
                  <span className="font-score text-lg tabular-nums">
                    {num(s.payload.score_own)}:{num(s.payload.score_opponent)}
                  </span>
                )}
                <Button size="sm" variant="secondary" onClick={() => void one(s, true)}>
                  {t("import")}
                </Button>
                <Button size="sm" variant="quiet" onClick={() => void one(s, false)}>
                  {t("dismiss")}
                </Button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {(g.schedule.length > 0 || g.seasons.length > 0) && (
        <section className="space-y-3" aria-labelledby="official-schedule">
          <h2 id="official-schedule" className="text-2xl">
            {t("schedule")}
          </h2>
          <ul className="divide-y divide-foreground/10 border-t-2 border-foreground">
            {g.seasons.map((s) => (
              <li key={s.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 py-2.5">
                <span className="min-w-0 flex-1">{t("seasonNew", { label: str(s.payload.label) })}</span>
                <Button size="sm" variant="secondary" onClick={() => void one(s, true)}>
                  {t("accept")}
                </Button>
                <Button size="sm" variant="quiet" onClick={() => void one(s, false)}>
                  {t("dismiss")}
                </Button>
              </li>
            ))}
            {g.schedule.map((s) => {
              const from = (s.payload.from ?? {}) as { kickoff_at?: string };
              const to = (s.payload.to ?? {}) as { kickoff_at?: string };
              return (
                <li key={s.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 py-2.5">
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium">
                      {t(s.payload.is_home ? "home" : "away", { opponent: str(s.payload.opponent) })}
                    </span>
                    <span className="block text-sm text-muted">
                      {s.kind === "match_moved"
                        ? t("moved", { from: date(str(from.kickoff_at)), to: date(str(to.kickoff_at)) })
                        : date(str(s.payload.kickoff_at))}
                    </span>
                  </span>
                  {s.blocked === "plan_limit" ? (
                    // the plan holds no more games this season: an upgrade, not a dead button
                    <Link className={buttonClass("secondary", "sm")} href={`/app/${orgId}/club/billing`}>
                      <Lock aria-hidden />
                      {t("upgrade")}
                    </Link>
                  ) : (
                    <Button size="sm" variant="secondary" onClick={() => void one(s, true)}>
                      {t("accept")}
                    </Button>
                  )}
                  <Button size="sm" variant="quiet" onClick={() => void one(s, false)}>
                    {t("dismiss")}
                  </Button>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {(l.standing?.length ?? 0) > 0 && (
        <section className="space-y-3" aria-labelledby="official-standing">
          <h2 id="official-standing" className="text-2xl">
            {t("standing")}
          </h2>
          <div className="sheet overflow-x-auto">
            <table className="w-full text-[0.9375rem]" data-testid="official-standing">
              <caption className="sr-only">{t("standing")}</caption>
              <thead>
                <tr>
                  <th scope="col">{t("rank")}</th>
                  <th scope="col" className="text-left">
                    {t("team")}
                  </th>
                  <th scope="col">{t("games")}</th>
                  <th scope="col">{t("goalDiff")}</th>
                  <th scope="col">{t("points")}</th>
                </tr>
              </thead>
              <tbody>
                {standingByRank(l.standing ?? []).map((row) => {
                  const mine = row.teamId === own;
                  return (
                    <tr key={row.teamId ?? row.name} className={cn(mine && "font-semibold")} aria-current={mine || undefined}>
                      <td className="tabular-nums">{row.rank}</td>
                      <th scope="row" className={cn("text-left", mine ? "font-semibold" : "font-normal")}>
                        {mine ? <span className="underline decoration-resin decoration-[5px] underline-offset-[5px]">{row.name}</span> : row.name}
                      </th>
                      <td className="tabular-nums">{row.games}</td>
                      <td className="tabular-nums">{(row.goalDifference ?? 0) > 0 ? `+${row.goalDifference}` : row.goalDifference}</td>
                      <td className="tabular-nums">{row.points}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
