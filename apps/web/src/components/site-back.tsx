"use client";

import type { ReactNode } from "react";
import { useLocale, useTranslations } from "next-intl";
import { sitePage, useSiteConfig } from "@/lib/site-config";
import { cn } from "@/lib/utils";

/**
 * The way back to the website from the public pages of the app (BEFUNDE-2 L5): the start page
 * of handball-intelligence.com in the language the visitor reads now (de, fr, en). The address
 * comes from /v1/public/config and falls back to NEXT_PUBLIC_SITE_URL, then to the default.
 */
export function useSiteHome(): string {
  const locale = useLocale();
  return sitePage(useSiteConfig()?.site_url, locale);
}

/** «Zur Website» as a text link with a small arrow back. */
export function SiteBackLink({ className }: { className?: string }) {
  const t = useTranslations("nav");
  return (
    <a href={useSiteHome()} data-testid="to-website" className={cn("inline-flex min-h-11 items-center gap-1.5 text-[15px] font-bold whitespace-nowrap text-ink underline decoration-[1.5px] underline-offset-4", className)}>
      <svg viewBox="0 0 16 16" aria-hidden className="size-3.5 shrink-0">
        <path d="M10 3 5 8l5 5" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="square" />
      </svg>
      {t("toWebsite")}
    </a>
  );
}

/** The mark (or whatever is given) as a link to the website, named for screen readers. */
export function SiteHomeMark({ children, className }: { children: ReactNode; className?: string }) {
  const t = useTranslations("nav");
  return (
    <a href={useSiteHome()} aria-label={t("toWebsiteLabel")} className={className}>
      {children}
    </a>
  );
}
