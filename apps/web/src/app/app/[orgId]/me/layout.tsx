import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { PageTabs } from "@/components/shell/page-tabs";
import { PageHeader } from "@/components/ui/page-header";
import { meTabs } from "@/lib/settings-model";

/** "Ich": everything about the signed-in person, one level of tabs. */
export default async function MeLayout({ children, params }: { children: ReactNode; params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  const t = await getTranslations("settings");
  return (
    <div className="space-y-8">
      <div className="space-y-5">
        <PageHeader title={t("me")} />
        <PageTabs label={t("me")} items={meTabs(orgId).map((x) => ({ ...x, label: t(`tab_${x.key}`) }))} />
      </div>
      <div className="max-w-3xl space-y-12">{children}</div>
    </div>
  );
}
