import Link from "next/link";
import { StartLink } from "@/components/kit";
import { NavLinks } from "@/components/nav-links";
import { APP_LOCALE, messages, type Locale } from "@/lib/i18n";
import { loginUrl } from "@/lib/site";

/**
 * The top bar: the two-coloured word mark (outside the app, never on a club colour), six
 * destinations, «Anmelden» and «Kostenlos starten». On the phone the destinations sit behind
 * «Menü» (a word, not a symbol alone); a <details> element needs no script.
 */
export function Header({ locale }: { locale: Locale }) {
  const t = messages(locale).nav;
  const links: [string, string][] = [
    ["so-funktioniert-es", t.how],
    ["aufnahme", t.filming],
    ["demo", t.demo],
    ["preise", t.pricing],
    ["ratgeber", t.guides],
    ["hilfe", t.faq],
  ];
  const app = APP_LOCALE[locale];
  return (
    <header className="relative z-10 border-b-2 border-ink">
      <a href="#main" className="sr-only bg-ink px-4 py-3 font-bold text-ground focus:not-sr-only focus:absolute focus:top-2 focus:left-2">
        {t.skip}
      </a>
      <div className="wrap flex min-h-[4.5rem] flex-wrap items-center gap-x-4 gap-y-2 py-2">
        <Link href={`/${locale}/`} className="inline-flex shrink-0 items-center py-1" aria-label={t.home}>
          {/* docs/design/brand2/taktik/final/wortmarke-zweizeilig.svg: the sign about 45 px high, the words readable */}
          <img src="/brand/wortmarke-zweizeilig.svg" alt="" width={1456} height={512} className="h-14 w-auto md:h-16" />
        </Link>
        <nav aria-label={t.main} className="hidden flex-1 min-[1280px]:block">
          <NavLinks locale={locale} links={links} />
        </nav>
        <div className="ml-auto hidden items-center gap-5 min-[1280px]:flex">
          <a href={loginUrl(app)} className="link">
            {t.login}
          </a>
          <StartLink appLocale={app} className="btn btn-ink">
            {t.start}
          </StartLink>
        </div>
        <StartLink appLocale={app} className="btn btn-ink ml-auto hidden md:max-[1279px]:inline-flex">
          {t.start}
        </StartLink>
        <details className="group ml-auto md:ml-0 min-[1280px]:hidden">
          <summary className="btn btn-line list-none px-5">{t.menu}</summary>
          <div className="absolute inset-x-0 top-full border-b-2 border-ink bg-ground">
            <nav aria-label={t.main} className="wrap py-4">
              <NavLinks locale={locale} links={links} stacked />
              <div className="mt-4 flex flex-col gap-3 border-t-2 border-ink pt-4 sm:flex-row">
                <StartLink appLocale={app} className="btn btn-ink">
                  {t.start}
                </StartLink>
                <a href={loginUrl(app)} className="btn btn-line">
                  {t.login}
                </a>
              </div>
            </nav>
          </div>
        </details>
      </div>
    </header>
  );
}
