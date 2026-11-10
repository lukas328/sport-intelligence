import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { AccessRequests, Verification } from "@/components/official/requests";
import { loadSettings } from "../../settings/load";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("verification"))("section") };
}

/** The link to the federation: verification of a club taken over from the official data. */
export default async function ClubFederationPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  const { org, teams, access } = await loadSettings(orgId);
  if (!access.isAdmin || !access.official) notFound();
  return (
    <section id="official-section" className="space-y-8">
      <Verification orgId={org.id} />
      <AccessRequests orgId={org.id} teams={teams.map((x) => ({ id: x.id, name: x.name }))} />
    </section>
  );
}
