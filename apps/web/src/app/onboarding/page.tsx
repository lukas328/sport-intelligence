import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { OnboardingWizard } from "./wizard";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("onboarding"))("title") };
}

export default async function OnboardingPage() {
  const client = await serverApi();
  const { data: me } = await client.GET("/v1/me");
  if (!me) redirect("/login?next=/onboarding");
  // A user who already admins a club without teams continues at the team step.
  const adminOrg = me.organizations.find((o) => o.role === "org_admin");
  if (adminOrg) {
    const { data: teams } = await client.GET("/v1/orgs/{org_id}/teams", { params: { path: { org_id: adminOrg.id } } });
    if (teams && teams.length > 0) redirect(`/app/${adminOrg.id}`);
    const { data: org } = await client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: adminOrg.id } } });
    return <OnboardingWizard existingOrg={org} />;
  }
  return <OnboardingWizard />;
}
