import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { ImageResponse } from "next/og";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { kit } from "@/lib/color";

export const runtime = "nodejs";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "";

/**
 * The link preview of a shared scene or collection (SPEC 7.8, «Share preview»): the club colour
 * with the slanted lower edge, the title slanted, club and length underneath. No names of
 * people, nothing behind a login. Kanit 900 italic (SIL OFL, src/fonts; woff, which the image
 * renderer reads).
 */
export default async function Image({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const { data } = await (await serverApi()).GET("/v1/share/{token}/preview", { params: { path: { token } } });
  const k = kit([data?.kit.a ?? null, data?.kit.b ?? null]);
  const font = await readFile(join(process.cwd(), "src/fonts/kanit-latin-900-italic.woff"));
  const minutes = data?.duration_s ? Math.max(1, Math.round(data.duration_s / 60)) : null;
  const t = await getTranslations("share");
  const line = [data?.club, data?.scenes ? t("previewScenes", { n: data.scenes }) : null, minutes ? t("previewMinutes", { n: minutes }) : null].filter(Boolean).join(" · ");
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", background: k.ground, position: "relative" }}>
        <svg width="1200" height="630" style={{ position: "absolute", top: 0, left: 0 }}>
          <polygon points="0,0 1200,0 1200,500 0,630" fill={k.club} stroke={k.clubEdge} strokeWidth="4" />
        </svg>
        <div style={{ display: "flex", flexDirection: "column", padding: "64px 72px", color: k.clubInk }}>
          <div style={{ fontSize: 30, fontFamily: "Kanit", marginBottom: 20 }}>{line}</div>
          <div style={{ fontSize: 92, lineHeight: 0.95, fontFamily: "Kanit", maxWidth: 1000 }}>{data?.title ?? ""}</div>
        </div>
      </div>
    ),
    { ...size, fonts: [{ name: "Kanit", data: font, style: "italic", weight: 900 }] },
  );
}
