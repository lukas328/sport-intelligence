/**
 * Prices in EUR and CHF (docs/plans/europa.md, EU3: EUR 39 and CHF 39, a round number per
 * currency, so the amounts of packages/plans hold for both). Templates in the messages carry
 * `{cur}`; the page fills it with the visitor's currency: `?cur=` from a link or the switch on
 * «Preise», else CHF for a browser language of Switzerland and EUR for all others. Nothing is
 * stored in the browser.
 */
export const CURRENCIES = ["CHF", "EUR"] as const;
export type Currency = (typeof CURRENCIES)[number];

/** what the server renders, before the browser says more */
export const DEFAULT_CURRENCY: Currency = "CHF";

export function isCurrency(v: string | null | undefined): v is Currency {
  return v != null && (CURRENCIES as readonly string[]).includes(v.toUpperCase());
}

/** CHF when one of the browser's languages is a Swiss one (de-CH, fr-CH, it-CH, rm), else EUR. */
export function currencyOf(languages: readonly string[], query?: string | null): Currency {
  if (isCurrency(query)) return query.toUpperCase() as Currency;
  return languages.some((l) => /-ch$/i.test(l) || /^rm\b/i.test(l)) ? "CHF" : "EUR";
}

/** both currencies at once, for the places that render without a browser (titles, facts, llms.txt) */
export const BOTH = "CHF/EUR";

/** the price of one team in a plan for several (CHF 199 for 10 teams: 19.90), two decimals */
export function perTeam(p: { price_chf_month: number; teams: number }): string {
  return (p.price_chf_month / p.teams).toFixed(2);
}
