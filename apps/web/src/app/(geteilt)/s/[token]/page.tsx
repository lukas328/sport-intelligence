import type { Metadata } from "next";
import type { CSSProperties } from "react";
import { headers } from "next/headers";
import { getLocale, getTranslations } from "next-intl/server";
import { EmptyState } from "@/components/ui/card";
import { serverApi } from "@/lib/api";
import { clubStyle } from "@/lib/color";
import { ogDescription, ogTitle, publicOrigin, shareMetadata } from "@/lib/share/meta";
import { isPreviewBot } from "@/lib/share/policy";
import type { T } from "@/lib/share/text";
import { SharedView, type Shared } from "./shared-view";

const NOINDEX = { index: false, follow: false };

async function preview(token: string) {
  return (await (await serverApi()).GET("/v1/share/{token}/preview", { params: { path: { token } } })).data ?? null;
}

/**
 * The link preview in the chat (K20, R2): Open Graph and Twitter tags in the server HTML, with
 * absolute URLs, a picture made for the link and for a reel the MP4 itself. Fetching the preview
 * data does not count as an opening.
 */
export async function generateMetadata({ params }: { params: Promise<{ token: string }> }): Promise<Metadata> {
  const { token } = await params;
  const t = (await getTranslations()) as unknown as T;
  const data = await preview(token);
  if (!data) return { title: { absolute: t("share.invalid") }, robots: NOINDEX };
  return shareMetadata(t, data, { origin: publicOrigin(await headers(), process.env.HB_WEB_BASE_URL), token, locale: await getLocale() });
}

export default async function SharePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const t = await getTranslations("share");
  const data = await preview(token);
  if (!data) return <EmptyState title={t("invalid")} />;
  // a chat building its preview is no viewer: tags and a line of text, no opening counted
  if (isPreviewBot((await headers()).get("user-agent"))) {
    const tt = (await getTranslations()) as unknown as T;
    return (
      <div className="py-10">
        <h1 className="font-slant text-3xl">{ogTitle(tt, data)}</h1>
        <p className="mt-2 text-ink-2">{ogDescription(tt, data, await getLocale())}</p>
      </div>
    );
  }
  const res = await (await serverApi()).GET("/v1/share/{token}", { params: { path: { token } } });
  if (!res.data) return <EmptyState title={t("invalid")} />;
  // the club's colours carry the Keil of the shared page, as in the link preview
  return (
    <div style={clubStyle(data.kit.a ?? null, data.kit.b ?? null) as CSSProperties}>
      <SharedView token={token} data={res.data as unknown as Shared} club={data.club || null} clubColour={data.kit.a ?? null} />
    </div>
  );
}
