import type { Metadata } from "next";
import Link from "next/link";
import { JsonLd } from "@/components/json-ld";
import { APP_LOCALE, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { SITE_URL, SUPPORT_EMAIL, registerUrl } from "@/lib/site";
import plans from "@handball/plans";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMeta(locale, "", undefined, messages(locale).meta.description);
}

export default async function Home({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.home;
  return (
    <>
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@graph": [
            { "@type": "Organization", name: "Handball Intelligence", url: SITE_URL, email: SUPPORT_EMAIL },
            {
              "@type": "SoftwareApplication",
              name: "Handball Intelligence",
              applicationCategory: "SportsApplication",
              operatingSystem: "Web",
              description: m.meta.description,
              offers: plans.plans.map((p) => ({
                "@type": "Offer",
                name: m.pricing.plans[p.plan as keyof typeof m.pricing.plans].name,
                price: p.price_chf_month,
                priceCurrency: plans.currency,
              })),
            },
          ],
        }}
      />
      <section className="py-10 sm:py-16">
        <h1 className="max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">{t.title}</h1>
        <p className="mt-5 max-w-2xl text-lg text-muted">{t.lead}</p>
        <div className="mt-8 flex flex-wrap gap-3">
          <a href={registerUrl(APP_LOCALE[locale])} className="rounded-full bg-accent px-5 py-2.5 font-semibold text-accent-contrast">
            {t.cta}
          </a>
          <Link href={`/${locale}/demo/`} className="rounded-xl ring-1 ring-inset ring-border px-5 py-3 font-semibold">
            {t.ctaDemo}
          </Link>
        </div>
        <p className="mt-3 text-sm text-muted">{t.noCard}</p>
      </section>
      <section className="grid gap-6 sm:grid-cols-3">
        {t.points.map((p) => (
          <div key={p.title} className="rounded-2xl bg-raised ring-1 ring-border/70 bg-surface p-5">
            <h2 className="font-semibold">{p.title}</h2>
            <p className="mt-2 text-sm text-muted">{p.text}</p>
          </div>
        ))}
      </section>
      <section className="mt-14">
        <h2 className="text-2xl font-bold">{t.howTitle}</h2>
        <ol className="mt-5 grid gap-4 sm:grid-cols-4">
          {t.steps.map((s, i) => (
            <li key={s} className="rounded-2xl bg-raised ring-1 ring-border/70 p-4">
              <span className="block text-2xl font-bold text-accent">{i + 1}</span>
              {s}
            </li>
          ))}
        </ol>
      </section>
      <section className="mt-14 rounded-2xl bg-raised ring-1 ring-border/70 bg-surface p-6">
        <h2 className="text-xl font-bold">{t.honestTitle}</h2>
        <p className="mt-2 max-w-3xl text-muted">{t.honestText}</p>
      </section>
      <section className="mt-14 text-center">
        <h2 className="text-2xl font-bold">{t.finalTitle}</h2>
        <a href={registerUrl(APP_LOCALE[locale])} className="mt-5 inline-block rounded-full bg-accent px-5 py-2.5 font-semibold text-accent-contrast">
          {t.cta}
        </a>
      </section>
    </>
  );
}
