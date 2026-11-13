/** Links to the website and the support, usable on the server and in the browser. */

const LANG: Record<string, string> = { "de-CH": "de", fr: "fr", en: "en" };

/** A page of the website, always with its language path (/de, /fr, /en): the website is a static
 * export without redirects for addresses without one (UX test N06). */
export function sitePage(site: string, locale: string, page = ""): string {
  return `${site.replace(/\/$/, "")}/${LANG[locale] ?? "de"}/${page}`;
}

/** «This team is mine, but someone else has it»: a prepared mail to the support. */
export function ownershipMail(email: string, subject: string, body: string): string {
  return `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}
