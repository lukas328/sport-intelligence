"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/client";

/**
 * The website's and the support's addresses from the configuration (/v1/public/config), so a
 * change of domain does not break links in the app. Null until loaded: links wait for it.
 */
export function useSiteConfig() {
  return useQuery({
    queryKey: ["public-config"],
    staleTime: 3_600_000,
    queryFn: async () => (await api.GET("/v1/public/config")).data ?? null,
  }).data ?? null;
}

/** A page of the website in the reader's language (German without prefix). */
export function sitePage(site: string, locale: string, page: string): string {
  return `${site}${locale === "de-CH" ? "" : `/${locale}`}/${page}`;
}

/** «This team is mine, but someone else has it»: a prepared mail to the support. */
export function ownershipMail(email: string, subject: string, body: string): string {
  return `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}
