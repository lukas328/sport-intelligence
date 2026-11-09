"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useState, type FormEvent } from "react";
import { Button, buttonClass } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { FOLD_AT, groupByClub, searchable, type OfficialTeam } from "@/lib/official-teams";

type Claimed = Schemas["ClaimOut"];

/** Step one of the onboarding with the official data: find the team, then take it over (the
 * schedule, results and squad come with it), ask its club for access, or ask to join as a player.
 * Creating a club by hand stays one click away. */
export function OfficialTeamSearch({ onManual, onClaimed }: { onManual: () => void; onClaimed?: (club: string) => void }) {
  const t = useTranslations("officialTeams");
  const tr = useTranslations();
  const [q, setQ] = useState("");
  const [term, setTerm] = useState("");
  // the team being acted on, and how: a coach's access request or a player's join request
  const [acting, setActing] = useState<{ team: OfficialTeam; as: "coach" | "player" } | null>(null);
  const [claimed, setClaimed] = useState<{ team: OfficialTeam; out: Claimed } | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  const [error, setError] = useState<ErrorKey | null>(null);
  const [busy, setBusy] = useState(false);
  const [unfolded, setUnfolded] = useState<number[]>([]);

  // search as the coach types, a moment after the last key
  useEffect(() => {
    const id = setTimeout(() => setTerm(q.trim()), 300);
    return () => clearTimeout(id);
  }, [q]);
  const hits = useQuery({
    queryKey: ["official-teams", term],
    enabled: searchable(term),
    staleTime: 60_000,
    queryFn: async () => {
      const r = await api.GET("/v1/official/teams", { params: { query: { q: term } } });
      if (r.error) throw r.error;
      return r.data ?? [];
    },
  });
  const searchError = hits.error ? errorKey(hits.error) : null;

  async function claim(team: OfficialTeam, message?: string) {
    setBusy(true);
    setError(null);
    const r = await api.POST("/v1/official/teams/{official_id}/claim", {
      params: { path: { official_id: team.official_id } },
      body: { club_id: team.club.id, ...(message ? { message } : {}) },
    });
    setBusy(false);
    if (r.error || !r.data) return setError(errorKey(r.error));
    if (r.data.status === "access_requested") {
      setActing(null);
      return setSent(t("accessSent", { club: team.club.name }));
    }
    setClaimed({ team, out: r.data });
    onClaimed?.(team.club.name);
  }

  async function join(e: FormEvent<HTMLFormElement>, team: OfficialTeam) {
    e.preventDefault();
    if (!team.team_id) return;
    const f = new FormData(e.currentTarget);
    const number = String(f.get("jersey_number") ?? "").trim();
    setBusy(true);
    setError(null);
    const r = await api.POST("/v1/teams/{team_id}/join-requests", {
      params: { path: { team_id: team.team_id } },
      body: {
        first_name: String(f.get("first_name")),
        last_name: String(f.get("last_name")),
        jersey_number: number ? Number(number) : null,
        role: f.get("role") === "goalkeeper" ? "goalkeeper" : "player",
        message: String(f.get("message") ?? "").trim() || null,
      },
    });
    setBusy(false);
    if (r.error) return setError(errorKey(r.error));
    setActing(null);
    setSent(t("joinSent", { team: team.name }));
  }

  // after taking a team over: what came with it, and the next step (the squad)
  if (claimed) {
    const p = claimed.out.prefill;
    const org = claimed.out.organization_id;
    const team = claimed.out.team_id;
    return (
      <section className="space-y-4" data-testid="claim-done" aria-live="polite">
        <h2 className="text-2xl">{t("claimedTitle", { team: claimed.team.name })}</h2>
        {p && (
          <p className="text-[0.9375rem]">
            {t("claimedFound", { matches: p.matches_created ?? 0, players: p.roster_suggestions ?? 0, reports: p.report_suggestions ?? 0 })}
          </p>
        )}
        {(p?.matches_held_back ?? 0) > 0 && org && (
          <p className="text-sm text-muted">
            {t("heldBack", { n: p?.matches_held_back ?? 0 })}{" "}
            <Link className="font-medium text-foreground underline underline-offset-4" href={`/app/${org}/settings#billing`}>
              {t("upgrade")}
            </Link>
          </p>
        )}
        {claimed.out.verification === "unverified" && <p className="text-sm text-muted">{t("unverifiedHint")}</p>}
        {org && team && (
          <Link className={buttonClass("primary", "md")} href={`/app/${org}/teams/${team}/official`}>
            {t("confirmSquad")}
          </Link>
        )}
      </section>
    );
  }

  const groups = groupByClub(hits.data ?? []);
  return (
    <section className="space-y-5" data-testid="official-search">
      <div className="space-y-1">
        <h2 className="text-2xl">{t("title")}</h2>
        <p className="text-muted">{t("intro")}</p>
      </div>
      <div className="relative">
        <Input
          label={t("label")}
          value={q}
          onChange={(e) => (setQ(e.target.value), setSent(null), setError(null))}
          placeholder={t("placeholder")}
          autoComplete="off"
          autoFocus
          hint={t("hint")}
          className="pl-9"
          type="search"
        />
        <Search aria-hidden className="pointer-events-none absolute top-[2.35rem] left-3 size-4 text-muted" />
      </div>

      <div aria-live="polite" className="space-y-2">
        {sent && <Alert kind="success">{sent}</Alert>}
        {error && <Alert>{tr(`errors.${error}`)}</Alert>}
        {searchError && <Alert>{tr(`errors.${searchError}`)}</Alert>}
        {searchable(term) && hits.isSuccess && groups.length === 0 && <p className="text-sm text-muted">{t("noHits", { q: term })}</p>}
      </div>

      {groups.length > 0 && (
        <ul className="space-y-6" aria-label={t("results")}>
          {groups.map((g) => (
            <li key={g.id}>
              <h3 className="border-b-2 border-foreground pb-1 font-semibold">
                {g.name}
                {g.city && <span className="font-normal text-muted">{` · ${g.city}`}</span>}
              </h3>
              <ul className="divide-y divide-foreground/10">
                {(unfolded.includes(g.id) ? g.teams : g.teams.slice(0, FOLD_AT)).map((team) => {
                  const open = acting?.team.official_id === team.official_id ? acting : null;
                  return (
                    <li key={team.official_id} className="py-2.5" data-testid="official-team">
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                        <span className="min-w-0 flex-1">
                          <span className="block font-medium">{team.name}</span>
                          <span className="block text-sm text-muted">{[team.league, team.group_name].filter(Boolean).join(" · ")}</span>
                        </span>
                        {team.status === "member" && team.organization_id && team.team_id ? (
                          <Link className={buttonClass("secondary", "sm")} href={`/app/${team.organization_id}/teams/${team.team_id}`}>
                            {t("open")}
                          </Link>
                        ) : team.status === "available" ? (
                          <Button size="sm" variant="secondary" loading={busy && open == null} onClick={() => void claim(team)} data-testid="claim">
                            {t("claim")}
                          </Button>
                        ) : (
                          // in the app already: its people decide
                          <span className="flex flex-wrap gap-2">
                            <span className="self-center text-sm text-muted">{t("inApp")}</span>
                            <Button size="sm" variant="secondary" aria-expanded={open?.as === "coach"} onClick={() => setActing(open?.as === "coach" ? null : { team, as: "coach" })}>
                              {t("askAccess")}
                            </Button>
                            {team.team_id && (
                              <Button size="sm" variant="secondary" aria-expanded={open?.as === "player"} onClick={() => setActing(open?.as === "player" ? null : { team, as: "player" })}>
                                {t("join")}
                              </Button>
                            )}
                          </span>
                        )}
                      </div>
                      {open?.as === "coach" && (
                        <form
                          className="mt-3 space-y-3 border-l-2 border-foreground/20 pl-4"
                          onSubmit={(e) => {
                            e.preventDefault();
                            void claim(team, String(new FormData(e.currentTarget).get("message") ?? "").trim());
                          }}
                        >
                          <p className="text-sm text-muted">{t("accessIntro", { club: team.club.name })}</p>
                          <Input label={`${t("message")} (${tr("common.optional")})`} name="message" maxLength={500} />
                          <Button type="submit" size="sm" loading={busy}>
                            {t("sendAccess")}
                          </Button>
                        </form>
                      )}
                      {open?.as === "player" && (
                        <form className="mt-3 space-y-3 border-l-2 border-foreground/20 pl-4" onSubmit={(e) => void join(e, team)}>
                          <p className="text-sm text-muted">{t("joinIntro")}</p>
                          <div className="grid gap-3 sm:grid-cols-2">
                            <Input label={t("firstName")} name="first_name" required autoComplete="given-name" />
                            <Input label={t("lastName")} name="last_name" required autoComplete="family-name" />
                            <Input label={`${t("number")} (${tr("common.optional")})`} name="jersey_number" type="number" min={0} max={99} inputMode="numeric" />
                            <Select label={t("role")} name="role" defaultValue="player">
                              <option value="player">{t("rolePlayer")}</option>
                              <option value="goalkeeper">{t("roleGoalkeeper")}</option>
                            </Select>
                          </div>
                          <Input label={`${t("message")} (${tr("common.optional")})`} name="message" maxLength={500} />
                          <Button type="submit" size="sm" loading={busy}>
                            {t("sendJoin")}
                          </Button>
                        </form>
                      )}
                    </li>
                  );
                })}
              </ul>
              {g.teams.length > FOLD_AT && !unfolded.includes(g.id) && (
                <button
                  type="button"
                  className="mt-1 text-sm font-medium underline underline-offset-4"
                  onClick={() => setUnfolded([...unfolded, g.id])}
                >
                  {t("showAll", { n: g.teams.length, club: g.name })}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      <p className="border-t border-foreground/15 pt-4 text-sm text-muted">
        {t("notFound")}{" "}
        <button type="button" className="font-medium text-foreground underline underline-offset-4" onClick={onManual} data-testid="manual-club">
          {t("manual")}
        </button>
      </p>
    </section>
  );
}
