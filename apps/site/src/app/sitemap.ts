import type { MetadataRoute } from "next";
import { LOCALES } from "@/lib/i18n";
import { pageUrl } from "@/lib/site";
import { BLOG } from "../../content/blog";
import { HELP } from "../../content/help";

export const dynamic = "force-static";

export const PAGES = ["", "funktionen", "preise", "demo", "aufnahme", "hilfe", "blog", "kontakt", "agb", "datenschutz", "impressum"];

export default function sitemap(): MetadataRoute.Sitemap {
  const paths = [...PAGES, ...HELP.map((h) => `hilfe/${h.slug}`), ...BLOG.map((p) => `blog/${p.slug}`)];
  return paths.map((path) => ({
    url: pageUrl("de", path),
    alternates: { languages: Object.fromEntries(LOCALES.map((l) => [l === "de" ? "de-CH" : l, pageUrl(l, path)])) },
  }));
}
