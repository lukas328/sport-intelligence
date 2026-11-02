export const locales = ["de-CH", "en", "fr"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "de-CH";
export const LOCALE_COOKIE = "NEXT_LOCALE";

export function resolveLocale(value: string | undefined | null): Locale {
  if (!value) return defaultLocale;
  const exact = locales.find((l) => l.toLowerCase() === value.toLowerCase());
  if (exact) return exact;
  const base = value.split("-")[0]?.toLowerCase();
  if (base === "de") return "de-CH";
  return locales.find((l) => l === base) ?? defaultLocale;
}
