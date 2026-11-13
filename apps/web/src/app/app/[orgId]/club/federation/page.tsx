import type { Metadata } from "next";
import { redirect } from "next/navigation";
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
  // not a 404 (UX test B32): others go to the club; a club without the link learns how it comes
  if (!access.isAdmin) redirect(`/app/${orgId}/club`);
  if (!access.official) {
    const t = await getTranslations("verification");
    return (
      <section id="official-section" className="space-y-3" data-testid="federation-none">
        <h2 className="text-[26px]">{t("federationTitle")}</h2>
        <p className="max-w-[60ch] text-[17px] text-ink-2">{t("notOfficial")}</p>
      </section>
    );
  }
  return (
    <section id="official-section" className="space-y-8">
      <Verification orgId={org.id} />
      <AccessRequests orgId={org.id} teams={teams.map((x) => ({ id: x.id, name: x.name }))} />
    </section>
  );
}
