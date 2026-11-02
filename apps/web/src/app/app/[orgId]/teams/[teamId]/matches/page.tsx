import Link from "next/link";
import { getFormatter, getTranslations } from "next-intl/server";
import { EmptyState } from "@/components/ui/card";
import { serverApi } from "@/lib/api";
import { NewMatchForm } from "./new-match-form";

const STATUS_STYLE: Record<string, string> = {
  ready: "bg-ok/10 text-ok",
  failed: "bg-error/10 text-error",
  processing: "bg-accent/10 text-accent",
  uploading: "bg-accent/10 text-accent",
  scheduled: "bg-surface text-muted",
};

export default async function MatchesPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const t = await getTranslations();
  const format = await getFormatter();
  const client = await serverApi();
  const path = { params: { path: { org_id: orgId, team_id: teamId } } };
  const [matches, team, org] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", path),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
  ]);
  const canWrite = org.data?.my_role === "org_admin" || ["coach", "analyst"].includes(team.data?.my_role ?? "");
  const list = matches.data ?? [];
  return (
    <div className="space-y-6">
      {list.length === 0 ? (
        <EmptyState title={t("matches.empty")}>{canWrite && t("matches.emptyHint")}</EmptyState>
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border" data-testid="match-list">
          {list.map((m) => (
            <li key={m.id}>
              <Link href={`/app/${orgId}/matches/${m.id}`} className="flex flex-wrap items-center gap-3 px-4 py-3 hover:bg-surface">
                <span className="w-28 text-sm text-muted tabular-nums">
                  {format.dateTime(new Date(m.kickoff_at), { dateStyle: "medium" })}
                </span>
                <span className="flex-1 font-medium">
                  {m.is_home ? "" : "@ "}
                  {m.opponent_name}
                  {m.competition && <span className="ml-2 text-sm font-normal text-muted">{m.competition}</span>}
                </span>
                {m.score_own != null && m.score_opponent != null && (
                  <span className="font-semibold tabular-nums">
                    {m.score_own}:{m.score_opponent}
                  </span>
                )}
                {m.is_demo && <span className="rounded-full bg-surface px-2 py-0.5 text-xs">{t("matches.demo")}</span>}
                <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_STYLE[m.status] ?? ""}`}>
                  {t(`matches.status_${m.status}`)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {canWrite && <NewMatchForm orgId={orgId} teamId={teamId} />}
    </div>
  );
}
