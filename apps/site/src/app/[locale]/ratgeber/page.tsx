import type { Metadata } from "next";
import Link from "next/link";
import { JsonLd } from "@/components/json-ld";
import { GuideThumb } from "@/components/guide-thumb";
import { KitScope } from "@/components/kit";
import { TopicTiles } from "@/components/head-art";
import { PageHead, SectionHead, Updated } from "@/components/wurf-head";
import { fmt, messages, type Locale } from "@/lib/i18n";
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
  const item = (key: string, href: string, title: string, text: string, de: boolean) => (
    <li key={key} className="flex gap-5 border-b border-rule py-5">
      <GuideThumb slug={key} />
      <div className="min-w-0">
        <Link href={href} hrefLang={de ? "de-CH" : undefined} lang={de ? "de-CH" : undefined} className="font-bold text-[1.5rem] leading-tight hover:underline md:text-[1.625rem]">
          {title}
        </Link>
        <p className="measure mt-1 text-ink-2" lang={de ? "de-CH" : undefined}>
          {text}
        </p>
      </div>
    </li>
  );
  const row = (g: Guide, l: Locale) => item(g.slug, `/${l}/ratgeber/${g.slug}/`, g.title[l]!, g.answer[l]!, l !== locale);
  const latest = GUIDES.map((g) => g.updated).sort().at(-1) ?? "";
  // the tiles in the head: each topic with its number of pages (the filming page and the tools count)
  const counted = (n: number) => (n === 1 ? t.countOne : fmt(t.count, { count: n }));
  const tiles = [
    ...ORDER.map((group) => ({ id: `g-${group}`, name: t.groups[group], count: own.filter((g) => g.group === group).length + (group === "filmen" ? 1 : 0) })),
    { id: "g-tools", name: m.tools.groupTitle, count: 3 },
  ]
    .filter((x) => x.count > 0)
    .map((x) => ({ ...x, countText: counted(x.count) }));
  return (
    <KitScope>
      <JsonLd
        data={graph({
          ...webPage(locale, "ratgeber", t.metaTitle, t.description, latest, "CollectionPage"),
          hasPart: own.map((g) => ({ "@id": `${pageUrl(locale, `ratgeber/${g.slug}`)}#artikel` })),
        })}
      />
      <PageHead kick={t.title} title={t.head} lead={t.lead} aside={<TopicTiles tiles={tiles} label={t.topicsLabel} />} />
      <div className="wrap">
        {ORDER.map((group) => {
          const items = own.filter((g) => g.group === group);
          if (!items.length) return null;
          return (
            <section key={group} aria-labelledby={`g-${group}`} className="mt-14">
              <SectionHead id={`g-${group}`} title={t.groups[group]} />
              <ul className="max-w-[52rem]">
                {items.map((g) => row(g, locale))}
                {group === "filmen" && item("aufnahme", `/${locale}/aufnahme/`, m.seo.filming.title, m.filming.lead, false)}
              </ul>
            </section>
          );
        })}
        <section aria-labelledby="g-tools" className="mt-14">
          <SectionHead id="g-tools" title={m.tools.groupTitle} />
          <ul className="max-w-[52rem]">
            {item("vorlagen", `/${locale}/vorlagen/`, m.tools.templates.title, m.tools.templates.lead, false)}
            {item("rechner-quote", `/${locale}/rechner/wurfquote/`, m.tools.rate.title, m.tools.rate.lead, false)}
            {item("rechner-speicher", `/${locale}/rechner/speicher/`, m.tools.storage.title, m.tools.storage.lead, false)}
          </ul>
        </section>
        {german.length > 0 && (
          <section aria-labelledby="g-de" className="mt-14">
            <SectionHead id="g-de" title={t.germanTitle} note={t.germanNote} />
            <ul className="max-w-[52rem]">{german.map((g) => row(g, "de"))}</ul>
          </section>
        )}
        {latest && <Updated locale={locale} date={latest} />}
      </div>
    </KitScope>
  );
}
