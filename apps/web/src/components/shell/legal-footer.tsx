"use client";

import { useLocale, useTranslations } from "next-intl";
import { sitePage, useSiteConfig } from "@/lib/site-config";

const PAGES = ["impressum", "datenschutz", "agb", "kontakt"] as const;

/**
 * A slim line at the foot of the app with the website's legal pages (app review LEGAL-01): links
 * only, in the user's language; the texts live on the website.
 */
export function LegalFooter({ className }: { className?: string }) {
  const t = useTranslations("legalFooter");
  const locale = useLocale();
  const site = useSiteConfig()?.site_url;
  return (
    <footer className={className} data-testid="legal-footer">
      <nav aria-label={t("label")}>
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
          {PAGES.map((page) => (
            <li key={page}>
              <a
                href={sitePage(site, locale, page)}
                target="_blank"
                rel="noreferrer"
                className="inline-flex min-h-8 items-center underline decoration-1 underline-offset-4 hover:text-ink"
              >
                {t(page)}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </footer>
  );
}
