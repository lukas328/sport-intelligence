import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { JsonLd } from "@/components/json-ld";
import { helpBody, mdxComponents } from "@/lib/content";
import { fmt, HTML_LANG, LOCALES, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { pageUrl, SUPPORT_EMAIL } from "@/lib/site";
import { HELP } from "../../../../../content/help";

type Props = { params: Promise<{ locale: Locale; slug: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return LOCALES.flatMap((locale) => HELP.map((h) => ({ locale, slug: h.slug })));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const entry = HELP.find((h) => h.slug === slug);
  return entry ? pageMeta(locale, `hilfe/${slug}`, entry.title[locale], entry.summary[locale]) : {};
}

export default async function HelpArticle({ params }: Props) {
  const { locale, slug } = await params;
  const entry = HELP.find((h) => h.slug === slug);
  if (!entry) notFound();
  const t = messages(locale).help;
  const Body = await helpBody(locale, slug);
  return (
    <article className="max-w-3xl">
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
      <p className="text-sm">
        <Link href={`/${locale}/hilfe/`} className="text-accent underline">
          {t.back}
        </Link>
      </p>
      <h1 className="mt-4 text-3xl font-bold">{entry.title[locale]}</h1>
      <div className="prose mt-4">
        <Body components={mdxComponents(locale, "hilfe")} />
      </div>
      <p className="mt-10 border-t border-border pt-4 text-sm text-muted">
        {t.more} {fmt(t.contact, { email: SUPPORT_EMAIL })}
      </p>
    </article>
  );
}
