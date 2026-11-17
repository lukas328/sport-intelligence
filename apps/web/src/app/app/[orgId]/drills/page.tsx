import type { Metadata } from "next";
import { FOCI, type Focus } from "@handball/tactics";
import { getTranslations } from "next-intl/server";
import { AreaOrPageHeader } from "@/components/shell/section-nav";
import { DrillLibrary } from "./drill-library";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("drills"))("title") };
}

export default async function DrillsPage({ params, searchParams }: { params: Promise<{ orgId: string }>; searchParams: Promise<{ focus?: string }> }) {
  const { orgId } = await params;
  const { focus } = await searchParams;
  const t = await getTranslations("drills");
  const wanted = (focus ?? "").split(",").filter((f): f is Focus => FOCI.includes(f as Focus));
  return (
    <div className="space-y-6">
      <AreaOrPageHeader title={t("title")} />
      <p className="max-w-2xl text-[15px] text-muted">{t("hint")}</p>
      <DrillLibrary orgId={orgId} initialFocus={wanted} />
    </div>
  );
}
