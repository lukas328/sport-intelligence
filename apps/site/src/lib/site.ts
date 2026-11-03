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
export function registerUrl(appLocale: string): string {
  return `${APP_URL}/register?lang=${encodeURIComponent(appLocale)}`;
}

export function loginUrl(appLocale: string): string {
  return `${APP_URL}/login?lang=${encodeURIComponent(appLocale)}`;
}

export function pageUrl(locale: string, path = ""): string {
  return `${SITE_URL}/${locale}/${path ? `${path.replace(/^\/|\/$/g, "")}/` : ""}`;
}
