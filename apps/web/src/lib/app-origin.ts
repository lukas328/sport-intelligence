import { headers } from "next/headers";

/** The app's own address for robots.txt and the sitemap: NEXT_PUBLIC_APP_URL when set, else the
 * address the request came in on (behind the proxy: its forwarded host and scheme). */
export async function appOrigin(): Promise<string> {
  const fixed = process.env.NEXT_PUBLIC_APP_URL;
  if (fixed) return fixed.replace(/\/$/, "");
  const h = await headers();
  const host = h.get("x-forwarded-host") ?? h.get("host") ?? "app.handball-intelligence.com";
  const proto = h.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  return `${proto}://${host}`;
}
