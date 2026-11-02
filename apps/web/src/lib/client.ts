"use client";

import { createApiClient } from "@handball/api-client";

function readCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const match = document.cookie.split("; ").find((c) => c.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : undefined;
}

/** Browser client: same origin (proxied to the API), sends the CSRF header on unsafe requests. */
export const api = createApiClient(typeof window === "undefined" ? "http://localhost" : window.location.origin, {
  csrfToken: () => readCookie("hb_csrf"),
});
