import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { SettingsView } from "./settings-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("settings"))("title") };
}

export default async function SettingsPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  const client = await serverApi();
  const path = { params: { path: { org_id: orgId } } };
  const [org, teams, me] = await Promise.all([
    client.GET("/v1/orgs/{org_id}", path),
    client.GET("/v1/orgs/{org_id}/teams", path),
    client.GET("/v1/me"),
  ]);
  if (!org.data || !me.data) notFound();
  return <SettingsView org={org.data} teams={teams.data ?? []} me={me.data} />;
}
