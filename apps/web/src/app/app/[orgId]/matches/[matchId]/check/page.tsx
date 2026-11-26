import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { CheckView } from "./check-view";
import { ShotQuick } from "./shot-quick";
import { SpotFill } from "./spot-fill";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("anlauf"))("check") };
}

/**
 * Prüfen (SPEC 7.5): full screen, one question at a time, each answer saved at once. `?spots=1`:
 * only «Von wo?» for the goals without the place of the shot («Wurfort nachtragen», H7);
 * `&goal=<event>` for one goal. `?shots=1`: «Würfe schnell prüfen», the shots the analysis found
 * one after the other with four answers.
 */
export default async function CheckPage({ params, searchParams }: { params: Promise<{ orgId: string; matchId: string }>; searchParams: Promise<{ spots?: string; goal?: string; shots?: string }> }) {
  const { orgId, matchId } = await params;
  const { spots, goal, shots } = await searchParams;
  const { data: match } = await (await serverApi()).GET("/v1/orgs/{org_id}/matches/{match_id}", { params: { path: { org_id: orgId, match_id: matchId } } });
  if (!match) notFound();
  if (spots) return <SpotFill orgId={orgId} match={match} goalId={goal ?? null} />;
  if (shots) return <ShotQuick orgId={orgId} match={match} />;
  return <CheckView orgId={orgId} match={match} />;
}
