import type { Metadata } from "next";
import { DemoView } from "@/components/demo-view";
import type { DemoMatch } from "@/lib/demo";
import { APP_LOCALE, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { registerUrl } from "@/lib/site";
import data from "../../../../public/demo/match.json";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).demo;
  return pageMeta(locale, "demo", t.title, t.lead);
}

export default async function Demo({ params }: Props) {
  const { locale } = await params;
  const t = messages(locale).demo;
  return (
    <>
      <h1 className="text-3xl font-bold">{t.title}</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted">{t.lead}</p>
      <p role="note" className="mt-4 max-w-3xl rounded-md border border-border bg-surface p-3 text-sm">
        {t.fictional}
      </p>
      <div className="mt-8">
        <DemoView match={data as unknown as DemoMatch} t={t} locale={locale} />
      </div>
      <a href={registerUrl(APP_LOCALE[locale])} className="mt-10 inline-block rounded-md bg-accent px-5 py-3 font-semibold text-accent-contrast">
        {t.tryIt}
      </a>
    </>
  );
}
