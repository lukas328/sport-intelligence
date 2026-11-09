import type { Metadata } from "next";
import Link from "next/link";
import { HTML_LANG, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { BLOG } from "../../../../content/blog";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).blog;
  return pageMeta(locale, "blog", t.title, t.lead);
}

export default async function Blog({ params }: Props) {
  const { locale } = await params;
  const t = messages(locale).blog;
  const date = new Intl.DateTimeFormat(HTML_LANG[locale], { dateStyle: "long", timeZone: "Europe/Zurich" });
  const posts = [...BLOG].sort((a, b) => b.date.localeCompare(a.date));
  return (
    <>
      <h1 className="text-3xl font-bold">{t.title}</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted">{t.lead}</p>
      <ul className="mt-8 max-w-3xl space-y-6">
        {posts.map((p) => (
          <li key={p.slug} className="rounded-2xl bg-raised ring-1 ring-border/70 p-5">
            <time dateTime={p.date} className="text-sm text-muted">{date.format(new Date(p.date))}</time>
            <h2 className="mt-1 text-xl font-semibold">
              <Link href={`/${locale}/blog/${p.slug}/`} className="hover:underline">{p.title[locale]}</Link>
            </h2>
            <p className="mt-2 text-muted">{p.summary[locale]}</p>
          </li>
        ))}
      </ul>
    </>
  );
}
