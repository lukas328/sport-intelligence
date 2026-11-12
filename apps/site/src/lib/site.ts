/** Build-time settings of the static site; all optional with safe defaults. */
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "https://handball-ai.ch").replace(/\/$/, "");
export const APP_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "https://app.handball-ai.ch").replace(/\/$/, "");
export const SUPPORT_EMAIL = process.env.NEXT_PUBLIC_SUPPORT_EMAIL ?? "support@handball-ai.ch";
export const STATUS_URL = process.env.NEXT_PUBLIC_STATUS_URL ?? "";

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
 * empty search; «Kostenlos starten» leads there too. `lang` keeps the visitor's language.
 */
export function startUrl(appLocale: string, team?: string): string {
  const q = team ? `q=${encodeURIComponent(team)}&` : "";
  return `${APP_URL}/einstieg?${q}lang=${encodeURIComponent(appLocale)}`;
}

/** Form target of the team field (GET; the query is added by the browser). */
export const START_ACTION = `${APP_URL}/einstieg`;

export function loginUrl(appLocale: string): string {
  return `${APP_URL}/login?lang=${encodeURIComponent(appLocale)}`;
}

export function pageUrl(locale: string, path = ""): string {
  return `${SITE_URL}/${locale}/${path ? `${path.replace(/^\/|\/$/g, "")}/` : ""}`;
}
