import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { modeFor, startHref } from "@/lib/nav-model";
import { TodayView } from "../today-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("shell"))("today") };
}

/** The club's start: Spiele for staff (SPEC section 6), the start page for players and parents. */
export default async function TodayPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  const client = await serverApi();
  const path = { params: { path: { org_id: orgId } } };
  const [{ data: org }, { data: teams = [] }] = await Promise.all([client.GET("/v1/orgs/{org_id}", path), client.GET("/v1/orgs/{org_id}/teams", path)]);
  const saved = (await cookies()).get("hb_team")?.value;
  const team = teams.find((x) => x.id === saved) ?? teams[0] ?? null;
  const mode = modeFor(org?.my_role, team?.my_role);
  const start = startHref(mode, orgId, team?.id ?? null);
  if (start !== `/app/${orgId}`) redirect(start);
  return <TodayView orgId={orgId} />;
}
