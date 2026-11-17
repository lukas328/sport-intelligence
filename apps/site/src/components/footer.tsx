import Link from "next/link";
import { LangLinks } from "@/components/nav-links";
import { LOCALE_NAMES, LOCALES, messages, type Locale } from "@/lib/i18n";
import { STATUS_URL, SUPPORT_EMAIL } from "@/lib/site";
import { GUIDES } from "../../content/ratgeber";

export function Footer({ locale }: { locale: Locale }) {
  const m = messages(locale);
  const missing = Object.fromEntries(GUIDES.map((g) => [g.slug, LOCALES.filter((l) => !g.locales.includes(l))]));
  const col = (title: string, items: [string, string][]) => (
    <div>
      <h2 className="font-slant text-[1.375rem]">{title}</h2>
      <ul className="mt-2">
        {items.map(([href, label]) => (
          <li key={href}>
            {href.startsWith("http") || href.startsWith("mailto:") ? (
              <a href={href} className="inline-flex min-h-12 min-w-12 items-center underline-offset-4 hover:underline">
                {label}
              </a>
            ) : (
              <Link href={`/${locale}/${href}/`} className="inline-flex min-h-12 min-w-12 items-center underline-offset-4 hover:underline">
                {label}
              </Link>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
  const support: [string, string][] = [
    ["hilfe", m.nav.faq],
    ["daten", m.nav.data],
    ["ueber-uns", m.nav.us],
    ["kontakt", m.nav.about],
    [`mailto:${SUPPORT_EMAIL}`, SUPPORT_EMAIL],
  ];
  if (STATUS_URL) support.push([STATUS_URL, m.footer.status]);
  return (
    <footer className="mt-24 border-t-2 border-ink">
      <div className="wrap grid gap-10 py-12 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          {/* the vector word mark above its smallest size (brand: across from 220 px), so it stays sharp */}
          <img src="/brand/wortmarke-quer.svg" alt="Handball Intelligence" width={2150} height={512} className="h-14 w-auto" />
          <p className="mt-4 max-w-[18rem] text-base text-ink-2">{m.footer.note}</p>
          {/* the one quality mark, here and on «Über uns», not in the head (EU4) */}
          <p className="mt-4 flex items-center gap-2 text-base text-ink-2">
            <svg viewBox="0 0 32 32" aria-hidden className="size-5 shrink-0">
              <rect width="32" height="32" fill="#d52b1e" />
              <path d="M13 6h6v7h7v6h-7v7h-6v-7H6v-6h7z" fill="#fff" />
            </svg>
            {m.footer.made}
          </p>
        </div>
        {col(m.footer.product, [
          ["so-funktioniert-es", m.nav.how],
          ["aufnahme", m.nav.filming],
          ["demo", m.nav.demo],
          ["preise", m.nav.pricing],
          ["ratgeber", m.nav.guides],
          ["fakten", m.nav.facts],
          ["blog", m.nav.blog],
        ])}
        {col(m.footer.support, support)}
        <div>
          {col(m.footer.legal, [
            ["agb", m.footer.terms],
            ["datenschutz", m.footer.privacy],
            ["impressum", m.footer.imprint],
          ])}
          <nav aria-label={m.nav.language} className="mt-6">
            <h2 className="font-slant text-[1.375rem]">{m.nav.language}</h2>
            <LangLinks locale={locale} names={Object.fromEntries(LOCALES.map((l) => [l, LOCALE_NAMES[l]]))} missing={missing} />
          </nav>
        </div>
      </div>
    </footer>
  );
}
