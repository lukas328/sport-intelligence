import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { EmptyState } from "@/components/ui/card";
import { serverApi } from "@/lib/api";
import { SharedView, type Shared } from "./shared-view";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default async function SharePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const t = await getTranslations("share");
  const res = await (await serverApi()).GET("/v1/share/{token}", { params: { path: { token } } });
  if (!res.data) return <EmptyState title={t("invalid")} />;
  return <SharedView token={token} data={res.data as unknown as Shared} />;
}
