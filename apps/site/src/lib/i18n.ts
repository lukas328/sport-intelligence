import de, { type Messages } from "@/messages/de";
import en from "@/messages/en";
import fr from "@/messages/fr";

export const LOCALES = ["de", "fr", "en"] as const;
export type Locale = (typeof LOCALES)[number];
export const HTML_LANG: Record<Locale, string> = { de: "de-CH", fr: "fr-CH", en: "en" };
export const LOCALE_NAMES: Record<Locale, string> = { de: "Deutsch", fr: "Français", en: "English" };
/** The app's locale codes (apps/web/src/i18n/config.ts). */
export const APP_LOCALE: Record<Locale, string> = { de: "de-CH", fr: "fr", en: "en" };

const ALL: Record<Locale, Messages> = { de, fr, en };

export function isLocale(value: string): value is Locale {
  return (LOCALES as readonly string[]).includes(value);
}

export function messages(locale: string): Messages {
  return ALL[isLocale(locale) ? locale : "de"];
}

/** Replaces {name} placeholders. */
export function fmt(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (m, k: string) => (k in vars ? String(vars[k]) : m));
}

export function localeParams(): { locale: Locale }[] {
  return LOCALES.map((locale) => ({ locale }));
}
