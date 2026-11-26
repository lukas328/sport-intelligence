/**
 * The club's country (ISO 3166-1 alpha-2): it sets the billing currency (CHF in Switzerland and
 * Liechtenstein, EUR elsewhere, api services/plans.currency_for) and, later, the federation data.
 * A club made by hand takes a guess from the browser (time zone first: a German speaker in Zurich
 * is a Swiss club), and the club settings change it.
 */

/** The countries a club can choose, handball Europe first (europa.md EU1). */
export const COUNTRIES = ["CH", "LI", "DE", "AT", "FR", "BE", "LU", "NL", "DK", "NO", "SE", "IS", "FI", "ES", "PT", "IT", "PL", "CZ", "SK", "SI", "HR", "HU", "GB", "IE"] as const;

const ZONES: Record<string, string> = {
  "Europe/Zurich": "CH",
  "Europe/Vaduz": "LI",
  "Europe/Berlin": "DE",
  "Europe/Busingen": "DE",
  "Europe/Vienna": "AT",
  "Europe/Paris": "FR",
  "Europe/Brussels": "BE",
  "Europe/Luxembourg": "LU",
  "Europe/Amsterdam": "NL",
  "Europe/Copenhagen": "DK",
  "Europe/Oslo": "NO",
  "Europe/Stockholm": "SE",
  "Atlantic/Reykjavik": "IS",
  "Europe/Helsinki": "FI",
  "Europe/Madrid": "ES",
  "Europe/Lisbon": "PT",
  "Europe/Rome": "IT",
  "Europe/Warsaw": "PL",
  "Europe/Prague": "CZ",
  "Europe/Bratislava": "SK",
  "Europe/Ljubljana": "SI",
  "Europe/Zagreb": "HR",
  "Europe/Budapest": "HU",
  "Europe/London": "GB",
  "Europe/Dublin": "IE",
};

/** The country of a new club from the browser's time zone, else the region of its languages,
 * else Switzerland (where the federation data come from today). */
export function guessCountry(languages: readonly string[], timeZone?: string | null): string {
  const zone = timeZone ? ZONES[timeZone] : undefined;
  if (zone) return zone;
  for (const l of languages) {
    const region = l.split("-")[1]?.toUpperCase();
    if (region && (COUNTRIES as readonly string[]).includes(region)) return region;
  }
  return "CH";
}

/** The guess in this browser. */
export function browserCountry(): string {
  if (typeof navigator === "undefined") return "CH";
  let zone: string | undefined;
  try {
    zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    zone = undefined;
  }
  return guessCountry(navigator.languages?.length ? navigator.languages : [navigator.language], zone);
}

/** CHF or EUR for a country (the API's rule, shown beside the choice). */
export function currencyOf(country: string): "CHF" | "EUR" {
  return country === "CH" || country === "LI" ? "CHF" : "EUR";
}

/** A country's name in the page's language (the browser knows them all). */
export function countryName(code: string, locale: string): string {
  try {
    return new Intl.DisplayNames([locale], { type: "region" }).of(code) ?? code;
  } catch {
    return code;
  }
}
