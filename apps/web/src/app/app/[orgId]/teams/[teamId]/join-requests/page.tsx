import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { JoinRequests } from "@/components/official/requests";
import { PageHeader } from "@/components/ui/page-header";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("requests"))("joinTitle") };
}

export default async function JoinRequestsPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const t = await getTranslations("requests");
  return (
    <div className="space-y-6">
      <PageHeader eyebrow={`${t("eyebrow")} · ${t("joinHint")}`} title={t("joinTitle")} />
      <JoinRequests orgId={orgId} teamId={teamId} />
    </div>
  );
}
