/**
 * Errors of the app as a browser sees them, sent to our own API (POST /v1/client-errors) so that
 * faults nobody reports can be found: hydration mismatches (React's recoverable errors reach the
 * window as error events) and uncaught errors. Nothing personal leaves the browser: the error's
 * code, message and stack with ids, e-mail addresses and URL queries masked, the kind of page
 * (route with ids masked), the build and the kind of device. No cookies (credentials omit), at
 * most five reports per browser session. Technically necessary, no consent needed (privacy text).
 */

export interface ClientErrorReport {
  kind: "react" | "error" | "rejection";
  code: number | null;
  message: string;
  stack: string | null;
  route: string;
  build: string | null;
  device: "phone" | "tablet" | "desktop";
}

const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi;
const EMAIL = /[\w.+-]+@[\w-]+(\.[\w-]+)+/g;
const QUERY = /(https?:\/\/[^\s?#"')]+)[?#][^\s"')]*/g;
export const MAX_PER_SESSION = 5;
const KEY = "hb.client-errors";

/** Ids, e-mail addresses and the query of URLs out of a text. */
export function maskText(text: string): string {
  return text.replace(UUID, ":id").replace(EMAIL, "[email]").replace(QUERY, "$1");
}

/** The kind of page: /app/:id/matches/:id/check, never a query or a number. */
export function maskRoute(path: string): string {
  return path.split(/[?#]/)[0]!.replace(UUID, ":id").replace(/(?<=\/)\d+(?=\/|$)/g, ":n").slice(0, 200);
}

/** React's error number in a minified production message (#418: hydration mismatch). */
export function reactCode(message: string): number | null {
  const m = /Minified React error #(\d+)/.exec(message);
  return m ? Number(m[1]) : null;
}

export function deviceOf(width: number, coarse: boolean): ClientErrorReport["device"] {
  return width < 640 ? "phone" : coarse && width < 1100 ? "tablet" : "desktop";
}

/** The report for an error, or null for what is not worth one (no message, a browser extension). */
export function reportOf(error: unknown, kind: "error" | "rejection", path: string, device: ClientErrorReport["device"], build: string | null): ClientErrorReport | null {
  const e = error instanceof Error ? error : null;
  const message = e?.message ?? (typeof error === "string" ? error : "");
  if (!message) return null;
  const stack = e?.stack ?? null;
  // errors thrown by browser extensions are not ours
  if (stack && /chrome-extension:|moz-extension:|safari-web-extension:/.test(stack)) return null;
  const code = reactCode(message);
  return {
    kind: code != null ? "react" : kind,
    code,
    message: maskText(message).slice(0, 300),
    stack: stack ? maskText(stack).slice(0, 3000) : null,
    route: maskRoute(path),
    build,
    device,
  };
}

/** How many reports this browser session sent; counts on in memory without storage. */
let sentInMemory = 0;
export function takeSlot(storage: Pick<Storage, "getItem" | "setItem"> | null): boolean {
  try {
    if (storage) {
      const n = Number(storage.getItem(KEY) ?? 0);
      if (n >= MAX_PER_SESSION) return false;
      storage.setItem(KEY, String(n + 1));
      return true;
    }
  } catch {
    // private mode: the count in memory
  }
  if (sentInMemory >= MAX_PER_SESSION) return false;
  sentInMemory++;
  return true;
}
