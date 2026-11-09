import type { Metadata } from "next";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { TodayView } from "./today-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("shell"))("today") };
}

export default async function TodayPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  const { data: org } = await (await serverApi()).GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } });
  // a club taken over from the official data and not confirmed yet: one quiet line for its admins
  const unverified = org?.my_role === "org_admin" && org.verification === "unverified";
  const t = await getTranslations("verification");
  return (
    <TodayView
      orgId={orgId}
      notice={
        unverified ? (
          <p className="text-sm text-muted" data-testid="unverified-line">
            {t("line")}{" "}
            <Link href={`/app/${orgId}/settings#official-section`} className="font-medium text-foreground underline underline-offset-4">
              {t("lineLink")}
            </Link>
          </p>
        ) : undefined
      }
    />
  );
}
