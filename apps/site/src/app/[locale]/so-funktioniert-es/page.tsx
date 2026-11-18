import type { Metadata } from "next";
import Link from "next/link";
import type { CSSProperties } from "react";
import { AppTour } from "@/components/app-tour";
import { StepPicture } from "@/components/step-picture";
import { Reveal } from "@/components/reveal";
import { Honest } from "@/components/honest";
import { KitScope, StartLink } from "@/components/kit";
import { JsonLd } from "@/components/json-ld";
import { StepsArt } from "@/components/head-art";
import { PageHead, SectionHead } from "@/components/wurf-head";
import { graph, howTo } from "@/lib/schema";
import { APP_LOCALE, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";

type Props = { params: Promise<{ locale: Locale }> };

/**
 * Product pictures (public/product, scripts/product-shots): one per step (components/step-picture,
 * the same set as on the start page), and under «So sieht es in der App aus» the same pictures as
 * on the start page plus sharing.
 */
const SHOTS = ["get-video", "get-search", "get-season", "share"] as const;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).seo.how;
  return pageMeta(locale, "so-funktioniert-es", t.title, t.description);
}

export default async function How({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.how;
  return (
    <KitScope>
      <JsonLd
        data={graph(
          howTo(locale, "so-funktioniert-es", {
            name: t.head,
            description: t.lead,
            tools: [...m.filming.tools],
            steps: t.steps.map((s) => ({ name: s.title, text: s.text })),
          }),
        )}
      />
      <Reveal />
      <PageHead kick={t.title} title={t.head} lead={t.lead} aside={<StepsArt steps={t.steps} label={t.stepsLabel} />} />
      <div className="wrap">
        <ol className="mt-12">
          {t.steps.map((s, i) => (
            <li
              key={s.title}
              id={`schritt-${i + 1}`}
              className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-5 border-t-2 border-ink py-10 md:grid-cols-[6rem_minmax(0,1fr)_minmax(0,26rem)] md:gap-x-10"
            >
              <span aria-hidden className="font-num text-[4.5rem] leading-[.85] text-club-text md:text-[6.5rem]">
                {i + 1}
              </span>
              <div data-reveal>
                <h2 className="text-[2rem] md:text-[2.5rem]">{s.title}</h2>
                <p className="measure mt-3">{s.text}</p>
                {i === 0 && (
                  <Link href={`/${locale}/aufnahme/`} className="link mt-2">
                    {m.cta.filming}
                  </Link>
                )}
              </div>
              <div data-reveal style={{ "--d": 1 } as CSSProperties} className="col-span-2 mt-6 md:col-span-1 md:mt-0">
                <StepPicture step={i} locale={locale} alt={s.alt} />
              </div>
            </li>
          ))}
        </ol>

        <section aria-labelledby="shots" className="mt-16">
          <SectionHead id="shots" title={t.shotsTitle} note={t.shotsNote} />
          {/* one story with the four pictures (L13, U31): a stage with a play on the half court */}
          <AppTour
            label={t.tourLabel}
            hint={t.tourHint}
            items={t.shots.map((s, i) => ({
              player: t.tourPlayers[i]!,
              name: SHOTS[i]!,
              alt: s.alt,
              caption: s.caption,
              text: s.text,
              labels: m.product[SHOTS[i]!],
              lettering: SHOTS[i] === "get-video" ? m.home.film.video : undefined,
            }))}
          />
        </section>

        <section aria-labelledby="kann" className="mt-20">
          <SectionHead id="kann" title={m.honest.title} />
          <div className="mt-8">
            <Honest t={m.honest} short />
          </div>
          <Link href={`/${locale}/fakten/#kann`} className="link mt-2">
            {t.honestAll}
          </Link>
        </section>

        <div className="mt-16 flex flex-col gap-3 border-t-2 border-ink pt-10 sm:flex-row sm:flex-wrap">
          <StartLink appLocale={APP_LOCALE[locale]} className="btn btn-ink">
            {m.cta.start}
          </StartLink>
          <Link href={`/${locale}/demo/`} className="btn btn-line">
            {m.cta.demo}
          </Link>
        </div>
        <p className="mt-3 text-[1.0625rem] text-ink-2">{m.cta.trial}</p>
      </div>
    </KitScope>
  );
}
