import type { Metadata } from "next";
import { HTML_LANG, LOCALES, type Locale } from "@/lib/i18n";
import { SITE_NAME, pageUrl } from "@/lib/site";

/** hreflang value of a locale: the Swiss variants for German and French, plain English. */
export const HREFLANG: Record<Locale, string> = { de: "de-CH", fr: "fr-CH", en: "en" };

/**
 * The language alternates of one path: every language the page exists in, plus x-default (the
 * German page, the main market). Pages that exist only in German list only de-CH and x-default.
 */
export function alternates(path: string, available: readonly Locale[] = LOCALES): Record<string, string> {
  const out: Record<string, string> = Object.fromEntries(available.map((l) => [HREFLANG[l], pageUrl(l, path)]));
  out["x-default"] = pageUrl(available.includes("de") ? "de" : (available[0] ?? "de"), path);
  return out;
}

export interface PageMetaOptions {
  /** languages the page exists in (default: all three) */
  available?: readonly Locale[];
  /** an article: og:type article with its dates */
  article?: { published: string; modified?: string };
  noindex?: boolean;
}

/**
 * Title, description, canonical URL, language alternates and Open Graph of one page. Next replaces
 * the layout's openGraph as a whole, so every field is set here again.
 */
export function pageMeta(locale: Locale, path: string, title: string | undefined, description: string, opts: PageMetaOptions = {}): Metadata {
  const available = opts.available ?? LOCALES;
  const url = pageUrl(locale, path);
  const others = available.filter((l) => l !== locale).map((l) => HTML_LANG[l].replace("-", "_"));
  const image = { url: "/og.png", width: 1200, height: 630, alt: SITE_NAME };
  return {
    // the layout adds « | Handball Intelligence»; a title that would pass 60 characters stands alone
    ...(title ? { title: `${title} | ${SITE_NAME}`.length > 60 ? { absolute: title } : title } : {}),
    description,
    alternates: { canonical: url, languages: alternates(path, available) },
    openGraph: {
      title: title ?? SITE_NAME,
      description,
      url,
      siteName: SITE_NAME,
      locale: HTML_LANG[locale].replace("-", "_"),
      alternateLocale: others,
      images: [image],
      ...(opts.article
        ? { type: "article", publishedTime: opts.article.published, modifiedTime: opts.article.modified ?? opts.article.published }
        : { type: "website" }),
    },
    twitter: { card: "summary_large_image" },
    ...(opts.noindex ? { robots: { index: false, follow: true } } : {}),
  };
}
