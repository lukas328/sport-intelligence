/** Only allow same-site relative redirect targets (prevents open redirects via ?next=). */
export function safeNext(next: string | null | undefined, fallback = "/app"): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) return fallback;
  return next;
}

/**
 * Navigate after the session changed (sign-in, sign-up, password reset, invitation): a full
 * document load instead of `router.push()` + `router.refresh()`. The client router and its cache
 * still belong to the anonymous visitor, and push plus refresh fired two RSC requests at a route
 * that only redirects on the server (/app picks the first club). One document request lets the
 * server answer /app with a plain HTTP redirect and render the signed-in tree once, with the
 * session cookie in place, so the app shell is server-rendered inside NextIntlClientProvider.
 * `replace` keeps one-time token URLs (magic link, reset) out of the history.
 */
export function enterApp(target: string, { replace = false }: { replace?: boolean } = {}): void {
  if (replace) window.location.replace(target);
  else window.location.assign(target);
}
