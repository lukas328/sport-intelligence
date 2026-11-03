import type { Metadata } from "next";
import { PrintButton } from "@/components/print-button";
import { helpBody, mdxComponents } from "@/lib/content";
import { messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).recording;
  return pageMeta(locale, "aufnahme", t.title, t.lead);
}

/** Recording guide: the help article plus the printable notice for the hall (addendum 01, 8). */
export default async function Recording({ params }: Props) {
  const { locale } = await params;
  const t = messages(locale).recording;
  const Body = await helpBody(locale, "aufnahme");
  return (
    <div className="max-w-3xl">
      <h1 className="text-3xl font-bold">{t.title}</h1>
      <p className="mt-3 text-lg text-muted">{t.lead}</p>
      <div className="prose mt-4">
        <Body components={mdxComponents(locale, "hilfe")} />
      </div>
      <section className="mt-10 rounded-lg border-2 border-foreground p-8 text-center" aria-labelledby="notice">
        <h2 id="notice" className="sr-only">{t.noticeTitle}</h2>
        <p className="text-2xl font-bold">{t.notice}</p>
      </section>
      <PrintButton label={t.print} />
    </div>
  );
}
