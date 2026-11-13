import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { JsonLd } from "@/components/json-ld";
import { KitScope } from "@/components/kit";
import { MailLine } from "@/components/mail-line";
import { PageHead } from "@/components/wurf-head";
import { helpBody, mdxComponents } from "@/lib/content";
import { HTML_LANG, LOCALES, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { pageUrl } from "@/lib/site";
import { HELP } from "../../../../../content/help";

type Props = { params: Promise<{ locale: Locale; slug: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return LOCALES.flatMap((locale) => HELP.map((h) => ({ locale, slug: h.slug })));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const entry = HELP.find((h) => h.slug === slug);
  if (!entry) return {};
  const meta = pageMeta(locale, `hilfe/${slug}`, entry.title[locale], entry.summary[locale]);
  // guides outside the core stay reachable for the app's links, but out of search engines
  return entry.listed === false ? { ...meta, robots: { index: false } } : meta;
}

export default async function HelpArticle({ params }: Props) {
  const { locale, slug } = await params;
  const entry = HELP.find((h) => h.slug === slug);
  if (!entry) notFound();
  const t = messages(locale).help;
  const Body = await helpBody(locale, slug);
  return (
    <KitScope>
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "TechArticle",
          headline: entry.title[locale],
          description: entry.summary[locale],
          inLanguage: HTML_LANG[locale],
          url: pageUrl(locale, `hilfe/${slug}`),
          publisher: { "@type": "Organization", name: "Handball Intelligence" },
        }}
      />
      <PageHead kick={<Link href={`/${locale}/hilfe/`} className="link text-ink">{t.back}</Link>} title={entry.title[locale]} lead={entry.summary[locale]} />
      <article className="wrap">
        {entry.listed === false && (
          <p role="note" className="measure mt-10 border-l-4 border-ink pl-4 text-ink-2">
            {t.aside}
          </p>
        )}
        <div className="prose mt-10">
          <Body components={mdxComponents(locale, "hilfe")} />
        </div>
        <p className="measure mt-12 border-t-2 border-ink pt-6">
          <b>{t.more}</b> <MailLine template={t.contact} />
        </p>
      </article>
    </KitScope>
  );
}
