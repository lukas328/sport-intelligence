import { getLocale, getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { sharePicture } from "@/lib/share/og-image";
import type { T } from "@/lib/share/text";

export const runtime = "nodejs";

/**
 * The preview picture of a shared link (K20): 1200 x 630 PNG, rendered from the preview data
 * (no opening counted). Its URL is in og:image and twitter:image of the page (`?v=` changes when
 * the picture's design does, chats cache per URL).
 */
export async function GET(_req: Request, { params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const { data } = await (await serverApi()).GET("/v1/share/{token}/preview", { params: { path: { token } } });
  const t = (await getTranslations()) as unknown as T;
  const res = await sharePicture(data ?? null, t, await getLocale());
  if (!data) res.headers.set("cache-control", "no-store");
  return res;
}
