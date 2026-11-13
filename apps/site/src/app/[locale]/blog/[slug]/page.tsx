import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { KitScope } from "@/components/kit";
import { PageHead } from "@/components/wurf-head";
import { JsonLd } from "@/components/json-ld";
import { blogBody, mdxComponents } from "@/lib/content";
import { HTML_LANG, LOCALES, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { pageUrl } from "@/lib/site";
import { BLOG } from "../../../../../content/blog";

type Props = { params: Promise<{ locale: Locale; slug: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return LOCALES.flatMap((locale) => BLOG.map((p) => ({ locale, slug: p.slug })));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const post = BLOG.find((p) => p.slug === slug);
  return post ? pageMeta(locale, `blog/${slug}`, post.title[locale], post.summary[locale]) : {};
}

export default async function BlogPost({ params }: Props) {
  const { locale, slug } = await params;
  const post = BLOG.find((p) => p.slug === slug);
  if (!post) notFound();
  const t = messages(locale).blog;
  const Body = await blogBody(locale, slug);
  const date = new Intl.DateTimeFormat(HTML_LANG[locale], { dateStyle: "long", timeZone: "Europe/Zurich" });
  return (
    <KitScope>
    <article>
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "BlogPosting",
          headline: post.title[locale],
          description: post.summary[locale],
          datePublished: post.date,
          inLanguage: HTML_LANG[locale],
          url: pageUrl(locale, `blog/${slug}`),
          publisher: { "@type": "Organization", name: "Handball Intelligence" },
        }}
      />
      <PageHead
        kick={<Link href={`/${locale}/blog/`} className="link text-ink">{t.back}</Link>}
        title={post.title[locale]}
        lead={<time dateTime={post.date}>{date.format(new Date(post.date))}</time>}
      />
      <div className="wrap">
        <div className="prose mt-10">
          <Body components={mdxComponents(locale, "blog")} />
        </div>
      </div>
    </article>
    </KitScope>
  );
}
