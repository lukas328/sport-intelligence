import type { Metadata } from "next";
import Link from "next/link";
import { messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).features;
  return pageMeta(locale, "funktionen", t.title, t.lead);
}

export default async function Features({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.features;
  return (
    <>
      <h1 className="text-3xl font-bold">{t.title}</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted">{t.lead}</p>
      <div className="mt-8 grid gap-5 sm:grid-cols-2">
        {t.items.map((f) => (
          <section key={f.title} className="rounded-lg border border-border p-5">
            <h2 className="font-semibold">{f.title}</h2>
            <p className="mt-2 text-sm text-muted">{f.text}</p>
          </section>
        ))}
      </div>
      <p className="mt-10">
        <Link href={`/${locale}/demo/`} className="font-semibold text-accent underline">
          {m.home.ctaDemo}
        </Link>
      </p>
    </>
  );
}
