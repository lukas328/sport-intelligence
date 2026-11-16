"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { SectionHead, linkClass } from "@/components/anlauf/blocks";
import { api } from "@/lib/client";
import { topScorers } from "@/lib/telegram";
import type { Stats } from "./analysis-views";

type Match = Schemas["MatchOut"];
type Row = { teamId?: number; name?: string; rank?: number; points?: number; games?: number };

const fold = (v: string) => v.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/g, "");
const sameTeam = (a: string, b: string) => {
  const x = fold(a);
  const y = fold(b);
  return Boolean(x && y) && (x === y || x.includes(y) || y.includes(x));
};

/**
 * What is known already while the video is processed (K22): the official report, the scorers,
 * both teams' places in the table, the last meetings; what comes with the analysis, and what the
 * coach can do meanwhile. Only what the data carries; nothing when nothing is known.
 */
export function KnownFacts({
  orgId,
  match,
  ownName,
  oppName,
  stats,
  names,
  hasReport,
  checks,
  staff,
  onAttach,
}: {
  orgId: string;
  match: Match;
  ownName: string;
  oppName: string;
  stats: Stats | null;
  names: Record<string, string>;
  hasReport: boolean;
  checks: number;
  staff: boolean;
  /** to the files of the match (photo of the paper report, notes) */
  onAttach?: () => void;
}) {
  const t = useTranslations("progress");
  const ta = useTranslations("anlauf");
  const format = useFormatter();
  const scouting = match.kind === "scouting";
  const link = useQuery({
    queryKey: ["official", match.team_id],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/official", { params: { path: { org_id: orgId, team_id: match.team_id } } })).data ?? null,
    staleTime: 600_000,
  });
  const earlier = useQuery({
    queryKey: ["matches", match.team_id],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", { params: { path: { org_id: orgId, team_id: match.team_id } } })).data ?? [],
    staleTime: 60_000,
  });
  const linked = Boolean(link.data?.official_team_id);
  const table = (link.data?.standing ?? []) as Row[];
  const ownRow = scouting ? undefined : table.find((r) => r.teamId != null && r.teamId === link.data?.official_team_id);
  const oppRow = table.find((r) => r.name && sameTeam(r.name, oppName));
  const otherRow = scouting && match.scouting_other ? table.find((r) => r.name && sameTeam(r.name, match.scouting_other!)) : undefined;
  const meetings = scouting
    ? []
    : (earlier.data ?? [])
        .filter((m) => m.id !== match.id && m.opponent_name === match.opponent?.name && m.score_own != null && m.score_opponent != null)
        .slice(0, 3);
  const scorers = stats ? topScorers(Object.values(stats.players), names, 3) : [];
  const played = Date.parse(match.kickoff_at) < Date.now();
  const facts: { key: string; text: string }[] = [];
  if (hasReport) facts.push({ key: "report", text: t("factReport") });
  else if (linked && played && !scouting) facts.push({ key: "report", text: t("factReportComes") });
  if (scorers.length) facts.push({ key: "scorers", text: t("factScorers", { list: scorers.join(", ") }) });
  if (stats && (stats.own.suspensions || stats.opponent.suspensions)) {
    facts.push({ key: "pens", text: t("factPenalties", { own: stats.own.suspensions, opp: stats.opponent.suspensions, ownName, oppName }) });
  }
  const rank = (name: string, r: Row | undefined) => (r?.rank != null ? t("factRank", { team: name, rank: r.rank, points: r.points ?? 0 }) : null);
  const ranks = [rank(ownName, ownRow), rank(oppName, oppRow), otherRow && match.scouting_other ? rank(match.scouting_other, otherRow) : null].filter(Boolean);
  if (ranks.length) facts.push({ key: "table", text: `${link.data?.league || link.data?.group_name || t("factTable")}: ${ranks.join(", ")}` });
  if (meetings.length) {
    const list = meetings.map((m) => `${format.dateTime(new Date(m.kickoff_at), { day: "numeric", month: "numeric", year: "2-digit" })} ${m.score_own}:${m.score_opponent}`);
    facts.push({ key: "met", text: t("factMeetings", { list: list.join(", ") }) });
  }
  const base = `/app/${orgId}/matches/${match.id}`;
  return (
    <>
      {facts.length > 0 && (
        <section data-testid="known-facts">
          <SectionHead title={t("knownTitle")} as="h3" />
          <ul className="m-0 list-none p-0">
            {facts.map((f) => (
              <li key={f.key} className="border-b border-rule py-2.5 text-base">
                {f.text}
              </li>
            ))}
          </ul>
        </section>
      )}
      <section data-testid="what-comes">
        <SectionHead title={t("comesTitle")} as="h3" />
        <p className="m-0 text-base">{t(scouting ? "comesScouting" : "comesText")}</p>
        {staff && (
          <>
            <p className="m-0 mt-4 text-[17px] font-bold">{t("meanwhile")}</p>
            <ul className="m-0 mt-1 list-none space-y-1 p-0">
              {checks > 0 && (
                <li>
                  <Link href={`${base}/check`} className={`${linkClass} inline-flex min-h-11 items-center`}>
                    {ta("answerChecks", { n: checks })}
                  </Link>
                </li>
              )}
              {!scouting && (
                <li>
                  <Link href={`/app/${orgId}/teams/${match.team_id}`} className={`${linkClass} inline-flex min-h-11 items-center`}>
                    {t("doRoster")}
                  </Link>
                </li>
              )}
              {match.opponent && (
                <li>
                  <Link href={`/app/${orgId}/opponents/${match.opponent.id}`} className={`${linkClass} inline-flex min-h-11 items-center`}>
                    {t("doOpponent", { opponent: oppName })}
                  </Link>
                </li>
              )}
              {onAttach && (
                <li>
                  <button type="button" onClick={onAttach} className={`${linkClass} inline-flex min-h-11 cursor-pointer items-center border-0 bg-transparent p-0 text-base`}>
                    {t("doAttach")}
                  </button>
                </li>
              )}
            </ul>
          </>
        )}
      </section>
    </>
  );
}
