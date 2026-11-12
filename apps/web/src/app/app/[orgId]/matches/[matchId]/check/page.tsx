import { notFound } from "next/navigation";
import { serverApi } from "@/lib/api";
import { CheckView } from "./check-view";

/** Prüfen (SPEC 7.5): full screen, one question at a time, each answer saved at once. */
export default async function CheckPage({ params }: { params: Promise<{ orgId: string; matchId: string }> }) {
  const { orgId, matchId } = await params;
  const { data: match } = await (await serverApi()).GET("/v1/orgs/{org_id}/matches/{match_id}", { params: { path: { org_id: orgId, match_id: matchId } } });
  if (!match) notFound();
  return <CheckView orgId={orgId} match={match} />;
}
