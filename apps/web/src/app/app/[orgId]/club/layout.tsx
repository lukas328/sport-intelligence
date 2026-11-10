import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { PageTabs } from "@/components/shell/page-tabs";
import { PageHeader } from "@/components/ui/page-header";
import { clubTabs, hasClub } from "@/lib/settings-model";
import { loadSettings } from "../settings/load";

/** "Verein": the club, its teams and roles, billing and the federation link; one level of tabs. */
export default async function ClubLayout({ children, params }: { children: ReactNode; params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  const { access } = await loadSettings(orgId);
  if (!hasClub(access)) notFound();
  const t = await getTranslations("settings");
  return (
    <div className="space-y-8">
      <div className="space-y-5">
        <PageHeader title={t("club")} />
        <PageTabs label={t("club")} items={clubTabs(orgId, access).map((x) => ({ ...x, label: t(`tab_${x.key}`) }))} />
      </div>
      <div className="max-w-3xl space-y-12">{children}</div>
    </div>
  );
}
