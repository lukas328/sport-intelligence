import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { TrainingView } from "./training-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("training"))("title") };
}

export default async function TrainingPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const client = await serverApi();
  const [{ data: team }, { data: org }] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: teamId } } }),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
  ]);
  const role = team?.my_role ?? "";
  const canPlan = org?.my_role === "org_admin" || ["coach", "analyst", "goalkeeper_coach", "athletic_coach", "team_manager"].includes(role);
  return <TrainingView orgId={orgId} teamId={teamId} canPlan={canPlan} />;
}
