import { notFound } from "next/navigation";
import { serverApi } from "@/lib/api";
import type { ClubAccess } from "@/lib/settings-model";

/** Org, teams and the signed-in person for the pages "Ich" and "Verein". */
export async function loadSettings(orgId: string) {
  const client = await serverApi();
  const path = { params: { path: { org_id: orgId } } };
  const [org, teams, me] = await Promise.all([client.GET("/v1/orgs/{org_id}", path), client.GET("/v1/orgs/{org_id}/teams", path), client.GET("/v1/me")]);
  if (!org.data || !me.data) notFound();
  const all = teams.data ?? [];
  const isAdmin = org.data.my_role === "org_admin";
  const access: ClubAccess = { isAdmin, coachOf: all.filter((x) => x.my_role === "coach").length, official: org.data.official_club_id != null };
  return { org: org.data, teams: all, me: me.data, isAdmin, access };
}
