import type { Metadata } from "next";
import { LOCALES } from "@/lib/i18n";
import { pageUrl } from "@/lib/site";

/** Title, description, canonical URL and language alternates of one page. */
export function pageMeta(locale: string, path: string, title: string | undefined, description: string): Metadata {
  const languages = Object.fromEntries(LOCALES.map((l) => [l === "de" ? "de-CH" : l, pageUrl(l, path)]));
  return {
    ...(title ? { title } : {}),
    description,
    alternates: { canonical: pageUrl(locale, path), languages: { ...languages, "x-default": pageUrl("de", path) } },
    openGraph: { title: title ?? "Handball AI", description, url: pageUrl(locale, path) },
  };
}
