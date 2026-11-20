/**
 * Where a sign-up came from (website review, 19.11.2026): links from the website carry
 * `?src=<place>` (hero, pricing, shared, ...). The first one seen in this tab is kept in
 * sessionStorage, never in a cookie, and sent with the registration and the new club; the API
 * stores it for the operators. Only a short slug is kept; anything else is ignored.
 */

const KEY = "hi-signup-src";
const SLUG = /^[a-z0-9][a-z0-9_-]{0,39}$/;

/** The cleaned place from a query string, or null. */
export function sourceFrom(search: string): string | null {
  const raw = new URLSearchParams(search).get("src");
  const cleaned = raw?.trim().toLowerCase() ?? "";
  return SLUG.test(cleaned) ? cleaned : null;
}

/** Keeps the `?src=` of the current address for this tab; the first one wins. */
export function rememberSource(search: string): void {
  const src = sourceFrom(search);
  if (!src) return;
  try {
    if (!window.sessionStorage.getItem(KEY)) window.sessionStorage.setItem(KEY, src);
  } catch {
    // storage blocked: the sign-up works without it
  }
}

/** The kept place, or null (nothing kept, or storage blocked). */
export function signupSource(): string | null {
  try {
    return window.sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}
