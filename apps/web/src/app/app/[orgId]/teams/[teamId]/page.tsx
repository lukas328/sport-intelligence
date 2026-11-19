import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getFormatter, getTranslations } from "next-intl/server";
import type { Schemas } from "@handball/api-client";
import { AttnTag, linkClass, SectionHead } from "@/components/anlauf/blocks";
import { PageHead } from "@/components/anlauf/heads";
import { RosterEditor } from "@/components/roster/roster-editor";
import { AreaSubNav } from "@/components/shell/section-nav";
import { buttonClass } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { serverApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { AccessRequests } from "@/components/official/requests";
import { InviteDialog } from "@/components/people/invite-dialog";
import { TeamLifeCard } from "@/components/settings/team-life";
import { coachRights } from "@/lib/roles";
import { ConsentCopy } from "./consent-copy";
import { MarkKeepers } from "@/components/roster/mark-keepers";
import { MarkPositions } from "@/components/roster/mark-positions";

type Entry = Schemas["RosterEntryOut"];

// the squad as it lines up on the match sheet (team-desk.jpg): goal, back court, wings and pivot
const GROUPS = [
  ["goal", ["TW"]],
  ["back", ["RL", "RM", "RR"]],
  ["wingPivot", ["LA", "RA", "KM"]],
] as const;
const ORDER = ["TW", "RL", "RM", "RR", "LA", "RA", "KM"];

/**
 * Team (SPEC 7.10): the title says the state of the squad, three groups by position with the
 * number, the name, one season figure and what is missing. At the side the consents (one link for
 * the team chat) and the bench. Editing the squad (add, import, status, accounts) moves to
 * «Kader bearbeiten» (?edit=1): nothing of it is lost.
 */
export async function generateMetadata({ params }: { params: Promise<{ orgId: string; teamId: string }> }): Promise<Metadata> {
  const { orgId, teamId } = await params;
  const { data } = await (await serverApi()).GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: teamId } } });
  return { title: `${(await getTranslations("shell"))("team")}${data ? ` · ${data.name}` : ""}` };
}

export default async function TeamPage({ params, searchParams }: { params: Promise<{ orgId: string; teamId: string }>; searchParams: Promise<{ edit?: string }> }) {
  const { orgId, teamId } = await params;
  const { edit } = await searchParams;
  const client = await serverApi();
  const path = { params: { path: { org_id: orgId, team_id: teamId } } };
  const [team, org, official] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", path),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/official", path),
  ]);
  if (!team.data || !org.data) notFound();
  const t = await getTranslations("teamPage");
  const tr = await getTranslations();
  const format = await getFormatter();
  const season = team.data.current_season;
  // Trainer and Co-Trainer edit the squad and see the side (K18)
  const canEdit = coachRights(org.data.my_role, team.data.my_role);
  const staff = canEdit;
  const isAdmin = org.data.my_role === "org_admin";
  const base = `/app/${orgId}/teams/${teamId}`;
  if (!season) return null;

  const linked = official.data?.linked ?? false;
  const source = linked && official.data?.synced_at ? t("fromOfficial", { when: format.relativeTime(new Date(official.data.synced_at), new Date()) }) : t("season", { label: season.label });
  const kick = t("kick", { team: team.data.name, source });

  if (edit != null && canEdit) {
    const open = linked ? (official.data?.open_suggestions ?? 0) : 0;
    return (
      <div className="space-y-6">
        <AreaSubNav />
        {/* the Seitenkopf like every page (UX test B34) */}
        <div className="bleed-x">
          <PageHead kick={kick} title={t("editTitle")} actions={<Link href={base} className={linkClass}>{t("back")}</Link>} />
        </div>
        {open > 0 && (
          <p className="text-sm" data-testid="official-open">
            <Link href={`${base}/official`} className={linkClass}>
              {t("openSuggestions", { n: open })}
            </Link>
          </p>
        )}
        <RosterEditor orgId={orgId} teamId={teamId} seasonId={season.id} canEdit={canEdit} />
      </div>
    );
  }

  const seasonPath = { params: { path: { org_id: orgId, team_id: teamId, season_id: season.id } } };
  const [roster, stats, matchList, members] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster", seasonPath),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/stats", seasonPath),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", path),
    // the staff list feeds only the side, which players do not get; they may not read it, so it
    // is not asked for (a 403 on every visit otherwise)
    staff ? client.GET("/v1/orgs/{org_id}/teams/{team_id}/members", path) : Promise.resolve({ data: [] as Schemas["TeamMemberOut"][] }),
  ]);
  // before the first video nothing is missing yet (UX test H04): consents matter once scenes
  // are shared, numbers once scenes are named
  const firstVideo = (matchList.data ?? []).some((m) => m.has_video);
  const entries: Entry[] = roster.data ?? [];
  const players = ((stats.data as unknown as { players?: { player_id: string; goals: number; saves: number }[] } | undefined)?.players ?? []).reduce<Record<string, { goals: number; saves: number }>>((m, p) => ((m[p.player_id] = p), m), {});
  // what is missing: the consent is staff business, the number everyone sees
  // after the first video the consents stand once, at the side (count and the link to ask for
  // them), not as a badge in every row and not in the title (UX test H04: no alarm right after
  // the first success); a missing number stays a badge, everyone sees it
  const missing = firstVideo ? entries.filter((p) => p.jersey_number == null).length : 0;
  const consents = entries.filter((p) => p.consent_complete).length;
  const title =
    entries.length === 0
      ? t("empty")
      : !firstVideo
        ? `${t("title", { n: entries.length })}${linked ? ` ${t("fromHandball")}` : ""}`
        : `${t("title", { n: entries.length })} ${missing > 0 ? t("missing", { k: missing }) : t("allThere")}`;
  const figure = (p: Entry) => {
    const s = players[p.player_id];
    if (!s) return null;
    return p.main_position === "TW" ? (s.saves > 0 ? t("saves", { n: s.saves }) : null) : s.goals > 0 ? t("goals", { n: s.goals }) : null;
  };
  const sort = (a: Entry, b: Entry) => ORDER.indexOf(a.main_position ?? "") - ORDER.indexOf(b.main_position ?? "") || (a.jersey_number ?? 100) - (b.jersey_number ?? 100);
  const known: string[] = ORDER;
  const groups = [
    ...GROUPS.map(([g, ps]) => ({ key: g, rows: entries.filter((p) => (ps as readonly string[]).includes(p.main_position ?? "")).sort(sort) })),
    { key: "other" as const, rows: entries.filter((p) => !known.includes(p.main_position ?? "")).sort(sort) },
  ].filter((g) => g.rows.length > 0);
  // without positions there are no position groups: one list, «Ohne Position» is no shortcoming
  const onlyOther = groups.length === 1 && groups[0]!.key === "other";
  const bench = (members.data ?? []).filter((m) => m.person_role === "trainer" || m.person_role === "co_trainer");
  const shellTeam = { id: teamId, name: team.data.name, team_features: team.data.settings.team_features ?? false };

  return (
    <div>
      <AreaSubNav />
      <PageHeader
        eyebrow={kick}
        title={title}
        actions={
          canEdit ? (
            <Link href={`${base}?edit=1`} className={linkClass} data-testid="roster-edit">
              {t("edit")}
            </Link>
          ) : undefined
        }
      />
      <div className={cn("grid gap-x-8 gap-y-12", staff ? "lg:grid-cols-[minmax(0,1fr)_300px] xl:grid-cols-[minmax(0,1fr)_340px]" : "")}>
        {/* three position groups side by side; beside the staff column at 1024 px two, so names keep one line (A18) */}
        <div className={cn("grid gap-x-8 gap-y-8 md:grid-cols-3", staff && "lg:grid-cols-2 xl:grid-cols-3")}>
          {/* an empty squad: what it is for and the one way to fill it (K8) */}
          {entries.length === 0 && (
            <section className="max-w-[60ch] space-y-4 md:col-span-full" data-testid="roster-empty">
              <p className="m-0 text-[17px]">{canEdit ? t("emptyText") : t("emptyTextPlayer")}</p>
              {canEdit && (
                <Link href={`${base}?edit=1`} className={buttonClass("primary")}>
                  {t("emptyAction")}
                </Link>
              )}
            </section>
          )}
          {/* what the squad is for, said once (review R37) */}
          {canEdit && entries.length > 0 && (
            <p className="m-0 max-w-[70ch] text-[15px] text-ink-2 md:col-span-full" data-testid="roster-why">
              {t("why")}
            </p>
          )}
          {/* the keepers, one tap each; open while nobody is keeper, else one line (review R37) */}
          {canEdit && entries.length > 0 && (
            <MarkKeepers orgId={orgId} teamId={teamId} players={[...entries].sort((a, b) => (a.jersey_number ?? 100) - (b.jersey_number ?? 100))} />
          )}
          {/* the court positions the same way: a position, then the players (A14) */}
          {canEdit && entries.length > 0 && <MarkPositions orgId={orgId} teamId={teamId} players={entries} />}
          {groups.map((g) => (
            <section key={g.key} aria-labelledby={`group-${g.key}`} className={cn(g.key === "other" && "md:col-span-full")}>
              <h2 id={`group-${g.key}`} className="font-slant mb-3 flex items-baseline gap-2.5 border-b border-rule pb-3 text-xl">
                {onlyOther ? t("group_all") : t(`group_${g.key}`)}
                <span className="font-sans text-[15px] font-medium text-ink-2 tabular-nums">{g.rows.length}</span>
              </h2>
              <ul className="m-0 list-none p-0">
                {g.rows.map((p) => {
                  const name = `${p.first_name} ${p.last_name}`;
                  const fig = figure(p);
                  return (
                    // on a phone a compact row (finding A14: one column of tall rows): number, name,
                    // and position with the figure on the right; from md three columns of full rows
                    <li key={p.id} className="grid min-h-14 grid-cols-[44px_minmax(0,1fr)_auto] items-center gap-x-3 border-b border-rule py-1.5 md:min-h-[76px] md:grid-cols-[64px_minmax(0,1fr)_auto] md:py-3" data-testid="team-row">
                      <span
                        className={cn("font-num text-right text-[32px] leading-[.8] md:text-[44px]", p.jersey_number == null || p.status ? "text-ink-2" : "text-club-text")}
                        aria-label={p.jersey_number == null ? t("noNumber") : `${tr("roster.number")} ${p.jersey_number}`}
                      >
                        {p.jersey_number ?? "?"}
                      </span>
                      <span className="min-w-0">
                        <span className="font-slant block text-[17px] leading-tight md:text-[19px]">
                          {staff ? (
                            <Link href={`${base}/players/${p.player_id}`} className="inline-flex min-h-11 items-center hover:underline hover:underline-offset-4">
                              {name}
                            </Link>
                          ) : (
                            name
                          )}
                        </span>
                        <span className="mt-1 flex flex-wrap items-center gap-1.5 text-[15px] text-ink-2 max-md:hidden">
                          {firstVideo && p.jersey_number == null ? <AttnTag>{t("numberMissing")}</AttnTag> : fig}
                          {p.status && <span>{t("out")}</span>}
                        </span>
                      </span>
                      <span className="flex flex-col items-end text-right">
                        <abbr title={p.main_position ? tr(`positions.${p.main_position}`) : undefined} className="text-[15px] font-bold text-ink-2 no-underline">
                          {p.main_position}
                        </abbr>
                        <span className="flex flex-wrap justify-end gap-1.5 text-[15px] leading-tight text-ink-2 md:hidden">
                          {firstVideo && p.jersey_number == null ? <AttnTag>{t("numberMissing")}</AttnTag> : fig}
                          {p.status && <span>{t("out")}</span>}
                        </span>
                      </span>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
        </div>
        {staff && (
          <aside className="space-y-12">
            {/* a second coach who chose this team on handball.ch waits here for the admins (K17) */}
            {isAdmin && <AccessRequests orgId={orgId} teams={[{ id: teamId, name: team.data.name }]} teamId={teamId} />}
            <section aria-labelledby="consents">
              <SectionHead as="h2" title={<span id="consents">{t("consents")}</span>} />
              {firstVideo ? (
                <>
                  <p className="m-0 flex items-baseline gap-3" data-testid="roster-consents">
                    <b className="font-num text-[64px] leading-[.85]">{consents}</b>
                    <span className="font-slant text-[22px] text-ink-2">{t("ofTotal", { total: entries.length })}</span>
                  </p>
                  <p className="mt-3 text-[15px] leading-snug">{t("consentText")}</p>
                </>
              ) : (
                <p className="m-0 text-[17px] leading-snug" data-testid="roster-consents-later">
                  {t("consentLater")}
                </p>
              )}
              <ConsentCopy orgId={orgId} teamId={teamId} />
            </section>
            <section aria-labelledby="bench">
              <SectionHead as="h2" title={<span id="bench">{t("bench")}</span>} />
              {bench.length === 0 ? (
                <p className="text-[15px] text-ink-2">{t("benchEmpty")}</p>
              ) : (
                <ul className="m-0 list-none p-0">
                  {bench.map((m) => (
                    <li key={m.user_id} className="flex min-h-12 items-center justify-between gap-3 border-b border-rule text-[17px] font-medium">
                      {m.name}
                      <span className="text-[15px] font-normal text-ink-2">{tr(`personRoles.${m.person_role ?? "co_trainer"}`)}</span>
                    </li>
                  ))}
                </ul>
              )}
              {/* inviting right here (K17): the roles say what each person sees */}
              <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2">
                <InviteDialog orgId={orgId} team={shellTeam} isAdmin={isAdmin} label={t("invite")} />
                <Link href={`/app/${orgId}/club/teams#people`} className={linkClass}>
                  {t("allPeople")}
                </Link>
              </div>
            </section>
            {/* Teamleben where the coach looks for it (K16) */}
            <TeamLifeCard orgId={orgId} teamId={teamId} teamName={team.data.name} initial={shellTeam.team_features} />
          </aside>
        )}
      </div>
    </div>
  );
}
