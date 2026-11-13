import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

export const dynamic = "force-static";

/**
 * Decision (docs/site/SEO.md, «KI-Crawler», for Lukas to confirm): the site wants to be found and
 * quoted, so search engines and AI crawlers may read everything. The crawlers are named one by one,
 * so the alternative (block only the training crawlers: GPTBot, ClaudeBot, Google-Extended,
 * Applebot-Extended, CCBot, meta-externalagent) is a change of one list.
 */
export const AI_CRAWLERS = [
  "GPTBot",
  "OAI-SearchBot",
  "ChatGPT-User",
  "ClaudeBot",
  "Claude-SearchBot",
  "Claude-User",
  "PerplexityBot",
  "Perplexity-User",
  "Google-Extended",
  "Applebot-Extended",
  "CCBot",
  "meta-externalagent",
  "meta-webindexer",
];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: "*", allow: "/" },
      { userAgent: AI_CRAWLERS, allow: "/" },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
