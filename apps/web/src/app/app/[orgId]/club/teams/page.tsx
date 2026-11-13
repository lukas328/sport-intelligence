import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { TeamFeaturesSection } from "@/components/settings/team-features";
import { PeopleSection } from "../../settings/settings-view";
import { loadSettings } from "../../settings/load";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("settings"))("tab_teams") };
}

/** Teams, roles and invitations, and "Teamfunktionen" per team. */
export default async function ClubTeamsPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  const { org, teams, isAdmin } = await loadSettings(orgId);
  const own = teams.filter((tm) => isAdmin || tm.my_role === "coach");
  return (
    <>
      <div id="people-section">
        <PeopleSection orgId={org.id} isAdmin={isAdmin} teams={own.map((tm) => ({ id: tm.id, name: tm.name }))} allTeams={teams} />
      </div>
      <TeamFeaturesSection orgId={org.id} teams={own} />
    </>
  );
}
