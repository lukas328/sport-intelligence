/** Links to the website and the support, usable on the server and in the browser. */

const LANG: Record<string, string> = { "de-CH": "de", fr: "fr", en: "en" };

/**
 * The website and the support as known at build time (NEXT_PUBLIC_SITE_URL,
 * NEXT_PUBLIC_SUPPORT_EMAIL), until /v1/public/config answers: a link is never relative to the app
 * (finding L9: «app…/de/agb» 404).
 */
export const DEFAULT_SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "https://handball-intelligence.com").replace(/\/$/, "");
export const DEFAULT_SUPPORT_EMAIL = process.env.NEXT_PUBLIC_SUPPORT_EMAIL ?? "support@handball-intelligence.com";

/** A page of the website, always with its language path (/de, /fr, /en): the website is a static
 * export without redirects for addresses without one (UX test N06). An empty or missing site
 * address falls back to the default, never to a path in the app. */
export function sitePage(site: string | null | undefined, locale: string, page = ""): string {
  const base = (site || DEFAULT_SITE_URL).replace(/\/$/, "");
  return `${base}/${LANG[locale] ?? "de"}/${page}`;
}

/** «This team is mine, but someone else has it»: a prepared mail to the support. */
export function ownershipMail(email: string, subject: string, body: string): string {
  return `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

/** A plain mail to the support (a forgotten password while no mail goes out, finding L2). */
export function supportMail(email: string | null | undefined, subject: string, body = ""): string {
  const to = email || DEFAULT_SUPPORT_EMAIL;
  return `mailto:${to}?subject=${encodeURIComponent(subject)}${body ? `&body=${encodeURIComponent(body)}` : ""}`;
}
