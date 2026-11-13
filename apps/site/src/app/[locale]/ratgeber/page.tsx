import type { Metadata } from "next";
import Link from "next/link";
import { JsonLd } from "@/components/json-ld";
import { KitScope } from "@/components/kit";
import { PageHead, SectionHead } from "@/components/wurf-head";
import { HTML_LANG, fmt, messages, type Locale } from "@/lib/i18n";
import { graph, webPage } from "@/lib/schema";
import { pageMeta } from "@/lib/seo";
import { pageUrl } from "@/lib/site";
import { GUIDES, type Guide, type GuideGroup } from "../../../../content/ratgeber";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).guides;
  return pageMeta(locale, "ratgeber", t.metaTitle, t.description);
}

const ORDER: GuideGroup[] = ["filmen", "auswerten", "training", "verein", "wissen"];

/** All guides by group; in French and English the German-only ones follow in their own list. */
export default async function Guides({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.guides;
  const own = GUIDES.filter((g) => g.locales.includes(locale));
  const german = GUIDES.filter((g) => !g.locales.includes(locale));
  const date = new Intl.DateTimeFormat(HTML_LANG[locale], { dateStyle: "long", timeZone: "Europe/Zurich" });
  const row = (g: Guide, l: Locale) => (
    <li key={g.slug} className="border-b border-rule py-5">
      <Link href={`/${l}/ratgeber/${g.slug}/`} hrefLang={l === locale ? undefined : "de-CH"} lang={l === locale ? undefined : "de-CH"} className="font-slant text-[1.5rem] leading-tight hover:underline md:text-[1.625rem]">
        {g.title[l]}
      </Link>
      <p className="measure mt-1 text-ink-2" lang={l === locale ? undefined : "de-CH"}>
        {g.answer[l]}
      </p>
    </li>
  );
  const latest = GUIDES.map((g) => g.updated).sort().at(-1) ?? "";
  return (
    <KitScope>
      <JsonLd
        data={graph({
          ...webPage(locale, "ratgeber", t.metaTitle, t.description, latest, "CollectionPage"),
          hasPart: own.map((g) => ({ "@id": `${pageUrl(locale, `ratgeber/${g.slug}`)}#artikel` })),
        })}
      />
      <PageHead kick={t.title} title={t.head} lead={t.lead}>
        {latest && <p className="mt-5 text-[1.0625rem] text-ink-2">{fmt(t.updated, { date: date.format(new Date(latest)) })}</p>}
      </PageHead>
      <div className="wrap">
        {ORDER.map((group) => {
          const items = own.filter((g) => g.group === group);
          if (!items.length) return null;
          return (
            <section key={group} aria-labelledby={`g-${group}`} className="mt-14">
              <SectionHead id={`g-${group}`} title={t.groups[group]} />
              <ul className="max-w-[52rem]">{items.map((g) => row(g, locale))}</ul>
            </section>
          );
        })}
        {german.length > 0 && (
          <section aria-labelledby="g-de" className="mt-14">
            <SectionHead id="g-de" title={t.germanTitle} note={t.germanNote} />
            <ul className="max-w-[52rem]">{german.map((g) => row(g, "de"))}</ul>
          </section>
        )}
      </div>
    </KitScope>
  );
}
