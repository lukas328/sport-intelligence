import type { Metadata } from "next";
import type { CSSProperties } from "react";
import { clubStyle } from "@/lib/color";
import { getTranslations } from "next-intl/server";
import { EmptyState } from "@/components/ui/card";
import { serverApi } from "@/lib/api";
import { SharedView, type Shared } from "./shared-view";

/** Open Graph data for the chat preview (title, club, length); fetching it does not count. */
export async function generateMetadata({ params }: { params: Promise<{ token: string }> }): Promise<Metadata> {
  const { token } = await params;
  const robots = { index: false, follow: false };
  const { data } = await (await serverApi()).GET("/v1/share/{token}/preview", { params: { path: { token } } });
  if (!data) return { robots };
  const t = await getTranslations("share");
  const minutes = data.duration_s ? Math.max(1, Math.round(data.duration_s / 60)) : null;
  const description = [data.club && data.club !== data.team ? `${data.club}, ${data.team}` : data.team, data.scenes ? t("previewScenes", { n: data.scenes }) : null, minutes ? t("previewMinutes", { n: minutes }) : null]
    .filter(Boolean)
    .join(" · ");
  return { title: data.title, description, robots, openGraph: { title: data.title, description, siteName: data.club, type: "video.other" } };
}

export default async function SharePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const t = await getTranslations("share");
  const client = await serverApi();
  const [res, preview] = await Promise.all([client.GET("/v1/share/{token}", { params: { path: { token } } }), client.GET("/v1/share/{token}/preview", { params: { path: { token } } })]);
  if (!res.data) return <EmptyState title={t("invalid")} />;
  // the club's colours carry the Keil of the shared page, as in the link preview
  const kit = preview.data?.kit;
  return (
    <div style={clubStyle(kit?.a ?? null, kit?.b ?? null) as CSSProperties}>
      <SharedView token={token} data={res.data as unknown as Shared} club={preview.data?.club ?? null} />
    </div>
  );
}
