import Link from "next/link";
import { APP_LOCALE, LOCALE_NAMES, LOCALES, messages, type Locale } from "@/lib/i18n";
import { loginUrl, registerUrl } from "@/lib/site";

export function Header({ locale }: { locale: Locale }) {
  const t = messages(locale).nav;
  const links: [string, string][] = [
    ["funktionen", t.features],
    ["preise", t.pricing],
    ["demo", t.demo],
    ["hilfe", t.help],
    ["blog", t.blog],
  ];
  return (
    <header>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:p-2">
        {t.skip}
      </a>
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
        <Link href={`/${locale}/`} className="inline-flex items-center gap-2.5 text-[1.0625rem] font-bold [font-stretch:112%]">
          <svg viewBox="0 0 32 32" aria-hidden className="size-7">
            <rect width="32" height="32" rx="9" fill="currentColor" />
            <path d="M7 9.5h18" stroke="var(--background)" strokeWidth="2.4" strokeLinecap="round" />
            <path d="M8 9.5c0 8 3.6 13 8 13s8-5 8-13" fill="none" stroke="var(--background)" strokeWidth="2.4" strokeLinecap="round" />
            <circle cx="16" cy="15" r="2.4" fill="var(--accent)" />
          </svg>
          Handball AI
        </Link>
        <nav aria-label="Navigation" className="order-3 flex w-full flex-wrap gap-x-4 gap-y-1 text-sm sm:order-none sm:w-auto">
          {links.map(([path, label]) => (
            <Link key={path} href={`/${locale}/${path}/`} className="whitespace-nowrap rounded-full px-1 text-muted hover:text-foreground">
              {label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3 text-sm">
          <nav aria-label={t.language} className="flex gap-2">
            {LOCALES.map((l) => (
              <Link
                key={l}
                href={`/${l}/`}
                hrefLang={l}
                lang={l}
                aria-current={l === locale ? "true" : undefined}
                title={LOCALE_NAMES[l]}
                className={l === locale ? "font-semibold underline" : "text-muted hover:underline"}
              >
                {l.toUpperCase()}
              </Link>
            ))}
          </nav>
          <a href={loginUrl(APP_LOCALE[locale])} className="hover:underline">
            {t.login}
          </a>
          <a href={registerUrl(APP_LOCALE[locale])} className="rounded-full bg-accent px-4 py-2 font-medium text-accent-contrast hover:brightness-95">
            {t.start}
          </a>
        </div>
      </div>
    </header>
  );
}
