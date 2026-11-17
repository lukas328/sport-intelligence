"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/client";

function useConfigQuery() {
  return useQuery({
    queryKey: ["public-config"],
    staleTime: 3_600_000,
    queryFn: async () => (await api.GET("/v1/public/config")).data ?? null,
  });
}

/**
 * The website's and the support's addresses from the configuration (/v1/public/config), so a
 * change of domain does not break links in the app, and whether mails go out (finding L2). Null
 * until loaded: links fall back to the defaults in `site.ts`; what depends on mail waits.
 */
export function useSiteConfig() {
  return useConfigQuery().data ?? null;
}

/** Whether mails go out: null while unknown, false when the API does not say so (L2). */
export function useMailEnabled(): boolean | null {
  const q = useConfigQuery();
  if (q.isPending) return null;
  return Boolean(q.data?.mail_enabled);
}

export { DEFAULT_SITE_URL, DEFAULT_SUPPORT_EMAIL, ownershipMail, sitePage, supportMail } from "./site";
