import type { Metadata } from "next";
import type { CSSProperties } from "react";
import Link from "next/link";
import plans from "@handball/plans";
import { DemoCamera } from "@/components/demo-camera";
import { HallPlan } from "@/components/hall-plan";
import { ProductShot } from "@/components/product-shot";
import { JsonLd } from "@/components/json-ld";
import { DemoLink, KitScope, StartLink } from "@/components/kit";
import { Reveal } from "@/components/reveal";
import { BeforeAfter, Evening, TeamChat, When } from "@/components/story";
import { TeamField } from "@/components/team-field";
import { Things } from "@/components/things";
import { APP_LOCALE, fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { graph, organization, softwareApplication, webPage, website } from "@/lib/schema";
import { SITE_UPDATED } from "@/lib/site";
import { saturday, threeMatchesLater } from "@/lib/story";
import { demoView } from "@/lib/things";

/** shown width of a picture in a step card (three columns from md) */
const STEP_SIZES = "(min-width: 1216px) 362px, (min-width: 768px) 30vw, calc(100vw - 2rem)";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMeta(locale, "", undefined, messages(locale).meta.description);
}

/**
 * The start page as one week of an invented team (docs/ux-test/livegang/BEFUNDE-2.md, W5, W22):
 * the promise with the answer cut out of the app; Saturday 7 pm, lost with only a feeling;
 * Saturday 10 pm, the three things; one of the goals from above; how you get there; Tuesday, four
 * scenes in the team chat; three matches later the right wing is closed. Then the video in the
 * club, the price and the team field. The match is the demo match, so its numbers are the demo's.
 */
export default async function Home({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.home;
  const v = demoView(m);
  const sat = saturday();
  const later = threeMatchesLater();
  const team = plans.plans.find((p) => p.plan === "team")!;
  const app = APP_LOCALE[locale];
  const wing = fmt(m.things.concededText, { zone: m.things.zones[sat.zone as keyof typeof m.things.zones] });
  return (
    <KitScope>
      <JsonLd
        data={graph(
          organization(),
          website(locale),
          softwareApplication(locale, m.meta.description, m.pricing.plans),
          webPage(locale, "", m.meta.title, m.meta.description, SITE_UPDATED),
        )}
      />
      <Reveal />

      {/* 1 · the promise, the way in, and the answer from the app */}
      <section
        aria-labelledby="hero"
        className="on-club relative overflow-hidden bg-club text-club-ink shadow-[inset_0_0_0_2px_var(--club-edge)] [clip-path:polygon(0_0,100%_0,100%_97%,0_100%)] md:[clip-path:polygon(0_0,100%_0,100%_calc(100%-4rem),0_100%)]"
      >
        <div className="wrap grid grid-cols-1 items-center gap-10 pt-8 pb-16 md:pt-14 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] lg:gap-14 lg:pb-28">
          <div className="min-w-0">
            <p className="text-base font-semibold md:text-[1.0625rem]">{t.kick}</p>
            <h1 id="hero" className="mt-3 text-[2.75rem] leading-[.95] md:text-[4.5rem]">
              {t.title}
            </h1>
            <p className="mt-5 max-w-[34rem] text-[1.1875rem] leading-normal font-medium md:mt-6 md:text-[1.375rem]">{t.lead}</p>
            <div className="mt-8">
              <TeamField id="team" label={t.teamLabel} button={t.teamButton} example={t.teamExample} appLocale={app} onClub />
            </div>
            <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-3">
              <DemoLink href={`/${locale}/demo/`} className="btn border-club-ink text-club-ink hover:bg-[color-mix(in_srgb,var(--club-ink)_12%,transparent)]">
                {m.cta.demo}
              </DemoLink>
              <p className="text-[1.0625rem] font-medium">{fmt(t.price, { price: team.price_chf_month, days: team.trial_days })}</p>
            </div>
          </div>
          <div className="rise min-w-0" style={{ "--d": 1 } as CSSProperties}>
            <ProductShot
              name="hero-thing"
              alt={t.heroAlt}
              labels={m.product["hero-thing"]}
              framed={false}
              priority
              sizes="(min-width: 1216px) 520px, (min-width: 1024px) 44vw, (min-width: 520px) 480px, calc(100vw - 2rem)"
              className="mx-auto max-w-[32.5rem] lg:mr-0"
            />
            <p className="mt-2 text-base font-medium lg:text-right">{t.shotNote}</p>
          </div>
        </div>
      </section>

      {/* 2 · Saturday, 7 pm: the problem (W6, W23, W25), the evening after the defeat */}
      <section aria-labelledby="problem" className="-mt-10 bg-ink pt-10 text-ground md:-mt-16 md:pt-16">
        <div className="wrap grid grid-cols-1 items-center gap-10 py-14 md:py-20 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:gap-16">
          <div data-reveal className="min-w-0">
            <When dark>{t.problemWhen}</When>
            <h2 id="problem" className="mt-4 text-[2.5rem] md:text-[4rem]">
              {t.problemTitle}
            </h2>
            <p className="mt-6 max-w-[36rem] text-[1.1875rem] text-[#dcdfe2] md:text-[1.3125rem]">{t.problemText}</p>
            <p className="mt-3 max-w-[36rem] text-[1.1875rem] text-[#dcdfe2] md:text-[1.3125rem]">{t.problemRest}</p>
            <p className="mt-6 text-[1.25rem] font-bold md:text-[1.4375rem]">{t.problemBuild}</p>
          </div>
          <div data-reveal style={{ "--d": 1 } as CSSProperties} className="min-w-0">
            <Evening t={t.problemCard} score={sat.score} />
          </div>
        </div>
      </section>

      <div className="wrap">
        {/* 3 · Saturday, 10 pm: what you get, the three things (W7) */}
        <section aria-labelledby="get" className="mt-20 md:mt-28">
          <div data-reveal className="max-w-[44rem]">
            <When>{t.getWhen}</When>
            <h2 id="get" className="mt-4 text-[2.25rem] md:text-[3.5rem]">
              {t.getTitle}
            </h2>
            <p className="mt-4 text-[1.1875rem] md:text-[1.3125rem]">{fmt(t.getText, { n: sat.n, of: sat.of })}</p>
          </div>
          <div data-reveal style={{ "--d": 1 } as CSSProperties} className="mt-6">
            <Things things={v.things} scenesHref={`/${locale}/demo/`} />
          </div>
          <p className="mt-4 text-[1.0625rem] text-ink-2">{t.getMore}</p>
        </section>

        {/* 4 · one of the nine from above: the demo to touch (W12) */}
        <section aria-labelledby="demo" className="mt-20 md:mt-28">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)] lg:gap-12">
            <div data-reveal className="min-w-0">
              <p className="text-[1.0625rem] font-semibold text-ink-2">{t.demoKick}</p>
              <h2 id="demo" className="mt-2 text-[2.25rem] md:text-[3rem]">
                {fmt(t.demoTitle, { n: sat.n })}
              </h2>
              <p className="mt-4">{t.demoText}</p>
              <DemoLink href={`/${locale}/demo/`} className="btn btn-ink mt-6">
                {t.demoLink}
              </DemoLink>
            </div>
            <div data-reveal style={{ "--d": 1 } as CSSProperties} className="min-w-0">
              <DemoCamera
                view="halfB"
                desktopWidth={720}
                shotLabel={false}
                scene={v.scene}
                text={{ label: m.camera.label, pause: m.camera.pause, play: m.camera.play, notFound: m.camera.notFound, noBall: m.camera.noBall, caption: v.scene.label }}
                legend={{ own: v.own, opp: v.opp, ref: m.camera.legendRef, number: m.camera.legendNumber, ball: m.camera.legendBall }}
              />
            </div>
          </div>
        </section>

        {/* 5 · how you get there: film, upload, check (W9, W20) */}
        <section aria-labelledby="steps" className="mt-20 md:mt-28">
          <div data-reveal className="max-w-[40rem]">
            <p className="text-[1.0625rem] font-semibold text-ink-2">{t.stepsKick}</p>
            <h2 id="steps" className="mt-2 text-[2.25rem] md:text-[3.5rem]">
              {t.stepsTitle}
            </h2>
            <p className="mt-3 text-[1.1875rem] md:text-[1.3125rem]">{t.stepsLead}</p>
          </div>
          {/* picture, title and text in rows shared by the three steps, so the titles line up */}
          <ol className="mt-10 grid grid-cols-1 gap-12 md:grid-cols-3 md:grid-rows-[auto_auto_1fr] md:gap-x-8 md:gap-y-0">
            {t.steps.map((s, i) => (
              <li key={s.title} data-reveal style={{ "--d": i } as CSSProperties} className="flex flex-col md:row-span-3 md:grid md:grid-rows-subgrid">
                {i === 0 ? (
                  <div className="flex aspect-[640/620] items-center border-2 border-ink bg-paper md:self-start [&_figure]:my-0 [&_figure]:w-full">
                    <HallPlan label={m.filming.planLabel} camera={m.filming.planCamera} field={m.filming.planField} corner={m.filming.planCorner} framed={false} />
                  </div>
                ) : (
                  <ProductShot
                    name={i === 1 ? "step-upload" : "step-check"}
                    alt={("alt" in s && s.alt) || ""}
                    labels={i === 1 ? m.product["step-upload"] : m.product["step-check"]}
                    sizes={STEP_SIZES}
                    className="md:self-start"
                  />
                )}
                <div className="mt-5 flex items-baseline gap-4">
                  <span aria-hidden className="font-num text-[3.5rem] leading-[.8] text-club-text">
                    {i + 1}
                  </span>
                  <h3 className="text-[1.5rem] leading-tight">{s.title}</h3>
                </div>
                <p className="mt-3">{s.text}</p>
              </li>
            ))}
          </ol>
          <div className="mt-6 flex flex-wrap gap-x-8">
            <Link href={`/${locale}/so-funktioniert-es/`} className="link">
              {m.cta.how}
            </Link>
            <Link href={`/${locale}/aufnahme/`} className="link">
              {m.cta.filming}
            </Link>
          </div>
        </section>

        {/* 6 · Tuesday: four scenes in the team chat (W26, W28) */}
        <section aria-labelledby="share" className="mt-20 md:mt-28">
          <div className="grid grid-cols-1 items-center gap-10 md:grid-cols-2 md:gap-16">
            <div data-reveal className="min-w-0">
              <When>{t.shareWhen}</When>
              <h2 id="share" className="mt-4 text-[2.25rem] md:text-[3rem]">
                {t.shareTitle}
              </h2>
              <p className="mt-4 text-[1.1875rem]">{t.shareText}</p>
              <ul className="mt-6 border-t-2 border-ink">
                {t.sharePoints.map((x) => (
                  <li key={x} className="flex gap-3 border-b border-rule py-3 font-semibold">
                    <Tick />
                    {x}
                  </li>
                ))}
              </ul>
            </div>
            <div data-reveal style={{ "--d": 1 } as CSSProperties} className="min-w-0">
              <TeamChat t={t.chat} team={v.own} />
            </div>
          </div>
        </section>

        {/* 7 · three matches later: the right wing is closed (W27) */}
        <section aria-labelledby="after" className="mt-20 md:mt-28">
          <div className="grid grid-cols-1 items-end gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] lg:gap-16">
            <div data-reveal className="min-w-0">
              <When>{t.afterWhen}</When>
              <h2 id="after" className="mt-4 text-[2.5rem] md:text-[4rem]">
                {t.afterTitle}
              </h2>
              <p className="mt-4 text-[1.1875rem] md:text-[1.3125rem]">{fmt(t.afterText, { before: sat.n, beforeOf: sat.of, after: later.n, afterOf: later.of })}</p>
              <p className="mt-4 text-base text-ink-2">{t.afterNote}</p>
            </div>
            <div data-reveal style={{ "--d": 1 } as CSSProperties} className="min-w-0">
              <BeforeAfter t={t} before={sat} after={later} zone={wing} />
            </div>
          </div>
        </section>

        {/* 8 · the video stays in the club */}
        <section aria-labelledby="trust" className="mt-20 border-t-2 border-ink pt-12 md:mt-28">
          <h2 id="trust" data-reveal className="text-[2.25rem] md:text-[3rem]">
            {t.trustTitle}
          </h2>
          <ul className="mt-8 grid grid-cols-1 gap-8 md:grid-cols-3">
            {t.trust.map((x, i) => (
              <li key={x.title} data-reveal style={{ "--d": i } as CSSProperties} className="border-t-2 border-ink pt-5">
                <h3 className="text-[1.375rem] leading-tight">{x.title}</h3>
                <p className="mt-2">{x.text}</p>
              </li>
            ))}
          </ul>
          <p data-reveal className="mt-8 flex flex-wrap items-center gap-x-4 gap-y-2 text-[1.0625rem]">
            <SwissFlag />
            <span className="max-w-[40rem]">{t.trustSwiss}</span>
          </p>
          <div className="mt-2 flex flex-wrap gap-x-8">
            <Link href={`/${locale}/daten/`} className="link">
              {m.cta.data}
            </Link>
            <Link href={`/${locale}/ueber-uns/`} className="link">
              {t.trustLink}
            </Link>
          </div>
        </section>

        {/* 9 · price (W4, W11) */}
        <section aria-labelledby="price" className="mt-20 md:mt-28">
          <div data-reveal className="grid grid-cols-1 items-end gap-6 border-2 border-ink bg-paper p-6 md:grid-cols-[auto_minmax(0,1fr)_auto] md:gap-10 md:p-10">
            <p className="flex items-baseline gap-3">
              <b className="font-num text-[5rem] leading-[.8] text-club-text md:text-[7rem]">{team.price_chf_month}</b>
              <span className="text-[1.0625rem] font-semibold text-ink-2">{t.priceUnit}</span>
            </p>
            <div>
              <h2 id="price" className="text-[2rem] md:text-[2.5rem]">
                {fmt(t.priceTitle, { price: team.price_chf_month })}
              </h2>
              <p className="mt-2">{fmt(t.priceText, { days: team.trial_days })}</p>
            </div>
            <div className="flex flex-col gap-2">
              <StartLink appLocale={app} className="btn btn-ink">
                {m.cta.start}
              </StartLink>
              <Link href={`/${locale}/preise/`} className="link justify-center">
                {m.cta.pricing}
              </Link>
            </div>
          </div>
        </section>

        {/* 10 · start */}
        <section aria-labelledby="final" className="mt-20 border-t-2 border-ink pt-10 md:mt-28">
          <h2 id="final" className="text-[2.5rem] md:text-[3.75rem]">
            {t.finalTitle}
          </h2>
          <div className="mt-8 grid grid-cols-1 items-end gap-8 md:grid-cols-[minmax(0,34rem)_auto]">
            <TeamField id="team-end" label={t.teamLabel} button={t.teamButton} example={t.teamExample} appLocale={app} />
            <DemoLink href={`/${locale}/demo/`} className="btn btn-line md:mb-9 md:justify-self-start">
              {m.cta.demo}
            </DemoLink>
          </div>
          <p className="mt-3 text-[1.0625rem] text-ink-2">{t.teamAfter}</p>
        </section>
      </div>
    </KitScope>
  );
}

function Tick() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden className="mt-1 size-5 shrink-0 text-club-text">
      <path d="M3 10.5 8 15 17 5" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="square" />
    </svg>
  );
}

function SwissFlag() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden className="size-8 shrink-0">
      <rect width="32" height="32" fill="#d52b1e" />
      <path d="M13 6h6v7h7v6h-7v7h-6v-7H6v-6h7z" fill="#fff" />
    </svg>
  );
}
