import type { MetadataRoute } from "next";
import { appOrigin } from "@/lib/app-origin";

/**
 * The app is no website (finding L11): search engines get the entry and the sign-in only. Shared
 * pages stay open for link previews in chats; they carry `noindex` themselves. Everything else
 * (the app, onboarding, invitations, consent links, the back office) is closed.
 */
export default async function robots(): Promise<MetadataRoute.Robots> {
  const origin = await appOrigin();
  return {
    rules: [{ userAgent: "*", allow: ["/$", "/einstieg", "/login", "/register", "/s/"], disallow: ["/"] }],
    sitemap: `${origin}/sitemap.xml`,
  };
}
