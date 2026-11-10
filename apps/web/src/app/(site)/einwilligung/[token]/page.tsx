import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { EmptyState } from "@/components/ui/card";
import { serverApi } from "@/lib/api";
import { ConsentForm } from "./consent-form";

export const metadata: Metadata = { robots: { index: false, follow: false } };

/** Consent through the team's link, without an account (SPEC section 1). */
export default async function ConsentPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const t = await getTranslations("consentLink");
  const { data } = await (await serverApi()).GET("/v1/consent/{token}", { params: { path: { token } } });
  if (!data) return <EmptyState title={t("invalid")} />;
  return (
    <div className="mx-auto max-w-xl space-y-6 py-8">
      <header>
        <p className="text-sm text-muted">{data.club}</p>
        <h1 className="text-2xl font-bold">{t("title", { team: data.team })}</h1>
      </header>
      <ConsentForm token={token} data={data} />
    </div>
  );
}
