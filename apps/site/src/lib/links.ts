import type { Locale } from "@/lib/i18n";

/**
 * Resolves the relative links in content files against their folder (help, blog, legal pages sit
 * directly under /{locale}/) and adds the trailing slash of the exported site.
 */
export function resolveHref(href: string, locale: Locale, folder: string): string {
  if (/^[a-z]+:/i.test(href) || href.startsWith("#") || href.startsWith("/")) return href;
  const base = `https://site.invalid/${locale}/${folder ? `${folder}/` : ""}`;
  const url = new URL(href, base);
  const path = url.pathname.endsWith("/") ? url.pathname : `${url.pathname}/`;
  return `${path}${url.hash}`;
}

/** `kit=` added to a link (the visitor's shirt), before its #part and next to a query it may have. */
export function withKit(href: string, shirt: string): string {
  const [path, hash] = href.split("#", 2);
  return `${path}${path!.includes("?") ? "&" : "?"}kit=${shirt}${hash !== undefined ? `#${hash}` : ""}`;
}
