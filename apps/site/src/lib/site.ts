/** Build-time settings of the static site; all optional with safe defaults. */
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "https://handball-intelligence.com").replace(/\/$/, "");
export const APP_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "https://app.handball-intelligence.com").replace(/\/$/, "");
export const SUPPORT_EMAIL = process.env.NEXT_PUBLIC_SUPPORT_EMAIL ?? "support@handball-intelligence.com";
export const STATUS_URL = process.env.NEXT_PUBLIC_STATUS_URL ?? "";

/** The product's name, as it stands in titles, structured data and llms.txt. */
export const SITE_NAME = "Handball Intelligence";

/**
 * Date of the last content review of the core pages («Stand» on the page, lastmod in the sitemap,
 * dateModified in structured data). Change it when the texts are reviewed again.
 */
export const SITE_UPDATED = "2026-11-13";

/**
 * The plan table in packages/plans is a placeholder (OPEN_QUESTIONS Q-PROD-4, Q-SITE-1). While this
 * is false, the pages say «noch nicht endgültig» and no price goes into structured data or llms.txt
 * as a fixed offer.
 */
export const PRICES_FINAL = false;

/**
 * Whether the analysis uses every file of a match (OPEN_QUESTIONS Q-VIDEO-PARTS). True since the
 * app analyses all parts of a match: the filming page, the questions, the facts, llms.txt, the
 * guide and the help articles follow this switch.
 */
export const MULTI_FILE = true;

/**
 * Public launch. While false, Fakten, Über uns, llms.txt and the question «Kann ich es heute schon
 * nutzen?» say that the site is before the launch and that operator details, terms and privacy
 * policy follow (m.facts.launchPre, dated with SITE_UPDATED). Set to true on launch day.
 */
export const LAUNCHED = false;

/** Operating company for the imprint; left empty until it is known (OPEN_QUESTIONS Q-ADD-3). */
export const COMPANY = {
  name: process.env.NEXT_PUBLIC_COMPANY_NAME ?? "",
  address: process.env.NEXT_PUBLIC_COMPANY_ADDRESS ?? "",
  uid: process.env.NEXT_PUBLIC_COMPANY_UID ?? "",
};

/** The app reads ?lang= once and keeps it as its language cookie (apps/web/src/middleware.ts). */
/**
 * The first step into the app starts here, without an account: «Wie heisst dein Team?» sends the
 * name to the app's team preview (`/einstieg?q=`, built in apps/web). Without a name it opens the
 * empty search; «Kostenlos starten» leads there too. `lang` keeps the visitor's language, `farbe`
 * the shirt colour picked on the site (blau, rot, …), so the app does not ask again.
 */
export function startUrl(appLocale: string, team?: string, farbe?: string): string {
  const q = team ? `q=${encodeURIComponent(team)}&` : "";
  const f = farbe ? `farbe=${encodeURIComponent(farbe)}&` : "";
  return `${APP_URL}/einstieg?${q}${f}lang=${encodeURIComponent(appLocale)}`;
}

/** Form target of the team field (GET; the query is added by the browser). */
export const START_ACTION = `${APP_URL}/einstieg`;

export function loginUrl(appLocale: string): string {
  return `${APP_URL}/login?lang=${encodeURIComponent(appLocale)}`;
}

export function pageUrl(locale: string, path = ""): string {
  return `${SITE_URL}/${locale}/${path ? `${path.replace(/^\/|\/$/g, "")}/` : ""}`;
}
