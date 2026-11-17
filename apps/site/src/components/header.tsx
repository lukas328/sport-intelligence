import Link from "next/link";
import { StartLink } from "@/components/kit";
import { NavLinks } from "@/components/nav-links";
import { APP_LOCALE, messages, type Locale } from "@/lib/i18n";
import { loginUrl } from "@/lib/site";

/**
 * The top bar: the two-coloured word mark (outside the app, never on a club colour), five
 * destinations, «Anmelden» and «Kostenlos starten», all in the bar from a laptop (1024 px) on. On
 * the phone and the tablet the destinations sit behind «Menü» (a word, not a symbol alone); a
 * <details> element needs no script.
 */
export function Header({ locale }: { locale: Locale }) {
  const t = messages(locale).nav;
  // four steps of a visitor's question, then the guides (W17); «Filmen» lives in the footer and
  // under «So funktioniert es»
  const links: [string, string][] = [
    ["so-funktioniert-es", t.how],
    ["demo", t.demo],
    ["preise", t.pricing],
    ["hilfe", t.faq],
    ["ratgeber", t.guides],
  ];
  const app = APP_LOCALE[locale];
  return (
    <header className="relative z-10 border-b-2 border-ink">
      <a href="#main" className="sr-only bg-ink px-4 py-3 font-bold text-ground focus:not-sr-only focus:absolute focus:top-2 focus:left-2">
        {t.skip}
      </a>
      <div className="wrap flex min-h-[5rem] flex-wrap items-center gap-x-4 gap-y-2 py-2 lg:flex-nowrap lg:gap-x-2 xl:gap-x-5">
        <Link href={`/${locale}/`} className="inline-flex shrink-0 items-center py-1" aria-label={t.home}>
          {/* docs/design/brand2/taktik/final/wortmarke-zweizeilig.svg, a vector at its own size: at
              least 140 px wide (brand rule), here 160 to 205 px */}
          <img src="/brand/wortmarke-zweizeilig.svg" alt="" width={1456} height={512} className="h-16 w-auto lg:h-14 xl:h-[4.5rem]" />
        </Link>
        {/* from a laptop on, the five destinations and «Anmelden» stand in the bar (S1) */}
        <nav aria-label={t.main} className="hidden min-w-0 flex-1 lg:block">
          <NavLinks locale={locale} links={links} />
        </nav>
        <div className="ml-auto hidden shrink-0 items-center gap-3 lg:flex xl:gap-5">
          <a href={loginUrl(app)} className="link whitespace-nowrap px-1">
            {t.login}
          </a>
          <StartLink appLocale={app} className="btn btn-ink whitespace-nowrap max-xl:px-4">
            {t.start}
          </StartLink>
        </div>
        <StartLink appLocale={app} className="btn btn-ink ml-auto hidden md:max-lg:inline-flex">
          {t.start}
        </StartLink>
        <details className="group ml-auto md:ml-0 lg:hidden">
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
