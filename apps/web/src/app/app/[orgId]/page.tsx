import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { OnboardingChecklist } from "@/components/support/checklist";
import { Card, EmptyState } from "@/components/ui/card";
import { serverApi } from "@/lib/api";

export default async function OrgHome({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  const t = await getTranslations();
  const { data: teams = [] } = await (await serverApi()).GET("/v1/orgs/{org_id}/teams", {
    params: { path: { org_id: orgId } },
  });
  return (
    <div className="space-y-6">
      <OnboardingChecklist orgId={orgId} teamId={teams[0]?.id ?? null} />
      <h1 className="text-2xl font-semibold">{t("dashboard.teamsTitle")}</h1>
      {teams.length === 0 ? (
        <EmptyState title={t("dashboard.noTeams")} />
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {teams.map((team) => (
            <li key={team.id}>
              <Card className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <h2 className="text-lg font-semibold">{team.name}</h2>
                  {team.is_youth && (
                    <span className="rounded-full bg-surface px-2 py-0.5 text-xs">{t("dashboard.youthBadge")}</span>
                  )}
                </div>
                <p className="text-sm text-muted">
                  {[t(`genders.${team.gender}`), team.league, team.current_season?.label].filter(Boolean).join(" · ")}
                </p>
                {team.my_role && <p className="text-sm">{t("dashboard.myRole", { role: t(`roles.${team.my_role}`) })}</p>}
                <div className="flex gap-4">
                  <Link
                    href={`/app/${orgId}/teams/${team.id}/matches`}
                    className="inline-block text-sm font-medium text-accent underline underline-offset-4"
                  >
                    {t("team.matches")}
                  </Link>
                  <Link
                    href={`/app/${orgId}/teams/${team.id}`}
                    className="inline-block text-sm font-medium text-accent underline underline-offset-4"
                  >
                    {t("dashboard.openRoster")}
                  </Link>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
