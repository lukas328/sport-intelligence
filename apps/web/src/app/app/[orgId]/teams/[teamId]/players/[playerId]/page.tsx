import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { SeasonLineView } from "./season-line";

type Params = { params: Promise<{ orgId: string; teamId: string; playerId: string }> };

/** The player's name as the page title (A12), the page's word only when the name is unknown. */
export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { orgId, teamId, playerId } = await params;
  const fallback = { title: (await getTranslations("seasonLine"))("title") };
  try {
    const client = await serverApi();
    const team = (await client.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: teamId } } })).data;
    if (!team?.current_season) return fallback;
    const roster = (
      await client.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster", {
        params: { path: { org_id: orgId, team_id: teamId, season_id: team.current_season.id } },
      })
    ).data;
    const p = roster?.find((r) => r.player_id === playerId);
    const name = p ? `${p.first_name} ${p.last_name}`.trim() : "";
    return name ? { title: name } : fallback;
  } catch {
    return fallback;
  }
}

export default async function PlayerPage({ params }: Params) {
  const { orgId, teamId, playerId } = await params;
  return <SeasonLineView orgId={orgId} teamId={teamId} playerId={playerId} />;
}
