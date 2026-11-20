/** Build-time settings of the static site; all optional with safe defaults. */
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "https://handball-intelligence.com").replace(/\/$/, "");
export const APP_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "https://app.handball-intelligence.com").replace(/\/$/, "");
export const SUPPORT_EMAIL = process.env.NEXT_PUBLIC_SUPPORT_EMAIL ?? "support@handball-intelligence.com";
export const STATUS_URL = process.env.NEXT_PUBLIC_STATUS_URL ?? "";

/** The product's name, as it stands in titles, structured data and llms.txt. */
export const SITE_NAME = "Handball Intelligence";

/**
 * Date of the last content review of the core pages (lastmod in the sitemap, dateModified in
 * structured data, the date of llms.txt and «Fakten»). Change it when the texts are reviewed again.
 */
export const SITE_UPDATED = "2026-11-17";

/**
 * The pages that show «Stand» under their content (BEFUNDE-3 U26): only where a reader needs to
 * know how current the page is, each with the day its text was last reviewed. Marketing pages
 * carry no date; a guide carries its own (content/ratgeber `updated`).
 */
export const PAGE_UPDATED = {
  /** Daten und Einwilligung: for parents and the board */
  daten: "2026-11-17",
  /** Fakten auf einen Blick: the site's statements in one table, the same as llms.txt */
  fakten: SITE_UPDATED,
} as const;

/**
 * The prices of packages/plans go into structured data as offers. The website describes the
 * product as it will be at release, without «noch nicht endgültig» (Lukas, 17.11., BEFUNDE-2 W32);
 * set to false to keep prices out of structured data again.
 */
export const PRICES_FINAL = true;

/**
 * Whether the analysis uses every file of a match (OPEN_QUESTIONS Q-VIDEO-PARTS). True since the
 * app analyses all parts of a match: the filming page, the questions, the facts, llms.txt, the
 * guide and the help articles follow this switch.
 */
export const MULTI_FILE = true;

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
export function startUrl(appLocale: string, team?: string, farbe?: string, src?: Source): string {
  const q = team ? `q=${encodeURIComponent(team)}&` : "";
  const f = farbe ? `farbe=${encodeURIComponent(farbe)}&` : "";
  const s = src ? `src=${src}&` : "";
  return `${APP_URL}/einstieg?${q}${f}${s}lang=${encodeURIComponent(appLocale)}`;
}

/**
 * Where on the site a way into the app sits: every link and form into the app carries it as
 * `?src=` (the app stores it at sign-up). The only measuring of the site: no cookie, no storage,
 * no third party (the footer's promise). The list is in apps/site/README.md, keep both in step.
 */
export const SOURCES = [
  "header",
  "menu",
  "login",
  "team-search",
  "team-search-end",
  "home-price",
  "pricing",
  "pricing-table",
  "how",
  "demo",
  "about",
  "clubs",
  "guide",
] as const;
export type Source = (typeof SOURCES)[number];

/** Form target of the team field (GET; the query is added by the browser). */
export const START_ACTION = `${APP_URL}/einstieg`;

/** The app's entry with the way by hand open at once, for teams the federation data does not cover. */
export function byHandUrl(appLocale: string, farbe?: string, src?: Source): string {
  const f = farbe ? `&farbe=${encodeURIComponent(farbe)}` : "";
  const s = src ? `&src=${src}` : "";
  return `${APP_URL}/einstieg?step=name${f}${s}&lang=${encodeURIComponent(appLocale)}`;
}

export function loginUrl(appLocale: string, src: Source = "login"): string {
  return `${APP_URL}/login?src=${src}&lang=${encodeURIComponent(appLocale)}`;
}

export function pageUrl(locale: string, path = ""): string {
  return `${SITE_URL}/${locale}/${path ? `${path.replace(/^\/|\/$/g, "")}/` : ""}`;
}
