"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

/**
 * A redirect that depends on data, from a page under a `loading.tsx`: there `redirect()` comes in
 * the middle of the stream, and Next answers with `<meta http-equiv="refresh">`, which reloads the
 * page a second later and turns every following client navigation into a full page load (e2e
 * 20.11., lib/moved.ts). This replaces the address on the client instead, without a second load.
 * Fixed old addresses are redirected by the middleware (lib/moved.ts).
 */
export function Replace({ to }: { to: string }) {
  const router = useRouter();
  useEffect(() => router.replace(to), [router, to]);
  return null;
}
