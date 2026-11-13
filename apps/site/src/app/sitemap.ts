import type { MetadataRoute } from "next";
import { LOCALES } from "@/lib/i18n";
import { alternates } from "@/lib/seo";
import { SITE_UPDATED, pageUrl } from "@/lib/site";
import { BLOG } from "../../content/blog";
import { GUIDES } from "../../content/ratgeber";
import { HELP } from "../../content/help";

export const dynamic = "force-static";

/** Pages that exist in all three languages, without the legal drafts' own dates. */
export const PAGES = ["", "so-funktioniert-es", "aufnahme", "demo", "preise", "hilfe", "ratgeber", "fakten", "ueber-uns", "daten", "kontakt", "blog", "agb", "datenschutz", "impressum"];

type Entry = { path: string; available: readonly (typeof LOCALES)[number][]; modified: string };

export function sitemapEntries(): Entry[] {
  return [
    ...PAGES.map((path) => ({ path, available: LOCALES, modified: SITE_UPDATED })),
    ...HELP.filter((h) => h.listed !== false).map((h) => ({ path: `hilfe/${h.slug}`, available: LOCALES, modified: SITE_UPDATED })),
    ...BLOG.map((p) => ({ path: `blog/${p.slug}`, available: LOCALES, modified: p.updated ?? p.date })),
    ...GUIDES.map((g) => ({ path: `ratgeber/${g.slug}`, available: g.locales, modified: g.updated })),
  ];
}

/** Every page in every language it exists in, each with all its alternates (hreflang) and x-default. */
export default function sitemap(): MetadataRoute.Sitemap {
  return sitemapEntries().flatMap(({ path, available, modified }) =>
    available.map((locale) => ({
      url: pageUrl(locale, path),
      lastModified: modified,
      alternates: { languages: alternates(path, available) },
    })),
  );
}
