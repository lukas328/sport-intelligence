import type { Metadata } from "next";
import type { CSSProperties } from "react";
import Link from "next/link";
import plans from "@handball/plans";
import { DemoCamera } from "@/components/demo-camera";
import { Browser, Phone } from "@/components/device";
import { HallPlan } from "@/components/hall-plan";
import { JsonLd } from "@/components/json-ld";
import { DemoLink, KitScope, ShirtPicker, StartLink } from "@/components/kit";
import { Reveal } from "@/components/reveal";
import { TeamField } from "@/components/team-field";
import { APP_LOCALE, fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { graph, organization, softwareApplication, webPage, website } from "@/lib/schema";
import { PRICES_FINAL, SITE_UPDATED } from "@/lib/site";
import { demoView } from "@/lib/things";
import { GUIDES } from "../../../content/ratgeber";

/** The three guides that exist in every language, shown on the start page. */
const FEATURED = ["handballspiel-filmen", "videoanalyse-amateurteam", "video-im-verein-einwilligung"];

/** Pictures from the app (public/app, made by scripts/app-screens.mjs), with their pixel sizes. */
const SHOT = {
  phone: { src: "/app/ergebnis-phone.webp", width: 780, height: 3760 },
  desktop: { src: "/app/ergebnis.webp", width: 1280, height: 1100 },
  upload: { src: "/app/hochladen-phone.webp", width: 780, height: 616 },
  check: { src: "/app/pruefen-phone.webp", width: 780, height: 1688 },
  video: { src: "/app/video.webp", width: 1280, height: 1000 },
  scenes: { src: "/app/szenen.webp", width: 1280, height: 940 },
  season: { src: "/app/saison.webp", width: 1280, height: 820 },
  share: { src: "/app/teilen-phone.webp", width: 780, height: 812 },
};

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMeta(locale, "", undefined, messages(locale).meta.description);
}

/**
 * The start page (K24, docs/research/R4-websites.md): one promise with the real app, three steps,
 * what a coach gets, the demo to touch, sharing, why we do it, trust, price, start. Short texts;
 * the details live on the pages behind the links.
 */
export default async function Home({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.home;
  const v = demoView(m);
  const team = plans.plans.find((p) => p.plan === "team")!;
  const app = APP_LOCALE[locale];
  const getShots = [SHOT.video, SHOT.scenes, SHOT.season];
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

      {/* 1 · the promise and the real app */}
      <section
        aria-labelledby="hero"
        className="on-club relative overflow-hidden bg-club text-club-ink shadow-[inset_0_0_0_2px_var(--club-edge)] [clip-path:polygon(0_0,100%_0,100%_96%,0_100%)] md:[clip-path:polygon(0_0,100%_0,100%_calc(100%-5rem),0_100%)]"
      >
        <div className="wrap grid grid-cols-1 items-center gap-10 pt-8 pb-20 md:pt-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:pb-32">
          <div className="min-w-0">
            <p className="text-base font-semibold md:text-[1.0625rem]">{t.kick}</p>
            <h1 id="hero" className="mt-3 text-[2.75rem] leading-[.95] md:text-[4.5rem]">
              {t.title}
            </h1>
            <p className="mt-5 max-w-[34rem] text-[1.1875rem] leading-normal font-medium md:mt-6 md:text-[1.375rem]">{t.lead}</p>
            <div className="mt-7 flex flex-col gap-3 min-[480px]:flex-row min-[480px]:flex-wrap">
              <StartLink appLocale={app} className="btn btn-ink shadow-[0_0_0_2px_var(--club-ink)]">
                {m.cta.start}
              </StartLink>
              <DemoLink href={`/${locale}/demo/`} className="btn border-club-ink text-club-ink hover:bg-[color-mix(in_srgb,var(--club-ink)_12%,transparent)]">
                {m.cta.demo}
              </DemoLink>
            </div>
            <p className="mt-4 text-[1.0625rem] font-medium">
              {fmt(t.price, { price: team.price_chf_month, days: team.trial_days })}
              {!PRICES_FINAL && <> {m.pricing.draft}</>}
            </p>
          </div>
          <div className="relative min-w-0">
            <Browser {...SHOT.desktop} alt={t.heroDesktopAlt} crop={1280 / 820} priority className="rise ml-auto hidden w-[92%] lg:block" />
            <div className="rise lg:absolute lg:-bottom-14 lg:-left-2 lg:w-[38%]" style={{ "--d": 2 } as CSSProperties}>
              <Phone {...SHOT.phone} alt={t.heroPhoneAlt} scroll priority className="max-w-[17rem] lg:max-w-none" />
            </div>
            <p className="mt-4 text-center text-base font-medium lg:mt-3 lg:ml-[42%] lg:text-left">{t.shotNote}</p>
          </div>
        </div>
      </section>

      <div className="wrap">
        {/* 2 · three steps */}
        <section aria-labelledby="steps" className="mt-14 md:mt-20">
          <div data-reveal className="max-w-[40rem]">
            <h2 id="steps" className="text-[2.25rem] md:text-[3.5rem]">
              {t.stepsTitle}
            </h2>
            <p className="mt-3 text-[1.1875rem] text-ink-2 md:text-[1.3125rem]">{t.stepsLead}</p>
          </div>
          <ol className="mt-10 grid grid-cols-1 gap-12 md:grid-cols-3 md:gap-8">
            {t.steps.map((s, i) => (
              <li key={s.title} data-reveal style={{ "--d": i } as CSSProperties} className="flex flex-col">
                <div className="relative aspect-[4/3.5] overflow-hidden border-2 border-ink bg-paper">
                  {i === 0 ? (
                    <div className="absolute inset-0 grid place-items-center p-3">
                      <div className="w-full max-w-[16.5rem]">
                        <HallPlan label={m.filming.planLabel} camera={m.filming.planCamera} field={m.filming.planField} corner={m.filming.planCorner} />
                      </div>
                    </div>
                  ) : i === 1 ? (
                    <div className="absolute inset-0 grid place-items-center p-4">
                      <img {...SHOT.upload} alt={"alt" in s ? s.alt : ""} loading="lazy" decoding="async" className="block h-auto w-full max-w-[22rem] border border-rule" />
                    </div>
                  ) : (
                    <img {...SHOT.check} alt={"alt" in s ? s.alt : ""} loading="lazy" decoding="async" className="absolute inset-0 block h-full w-full object-cover object-[center_80%]" />
                  )}
                </div>
                <div className="mt-5 flex items-baseline gap-4">
                  <span aria-hidden className="font-num text-[3.5rem] leading-[.8] text-club-text">
                    {i + 1}
                  </span>
                  <h3 className="font-slant text-[1.75rem] leading-none">{s.title}</h3>
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

        {/* 3 · what every match gives you */}
        <section aria-labelledby="get" className="mt-24 md:mt-32">
          <h2 id="get" data-reveal className="max-w-[44rem] text-[2.25rem] md:text-[3.5rem]">
            {t.getTitle}
          </h2>
          <ul className="mt-10 flex flex-col gap-16 md:gap-24">
            {t.get.map((g, i) => (
              <li key={g.title} className="grid grid-cols-1 items-center gap-6 md:grid-cols-12 md:gap-10">
                <div data-reveal className={i % 2 ? "md:order-2 md:col-span-7 md:col-start-6" : "md:col-span-7"}>
                  <Browser {...getShots[i]!} alt={g.alt} crop={1280 / 760} />
                </div>
                <div data-reveal style={{ "--d": 1 } as CSSProperties} className={i % 2 ? "md:order-1 md:col-span-4 md:col-start-1" : "md:col-span-4 md:col-start-9"}>
                  <span aria-hidden className="font-num block text-[3rem] leading-[.8] text-club-text">
                    {i + 1}
                  </span>
                  <h3 className="font-slant mt-3 text-[2rem] leading-none md:text-[2.375rem]">{g.title}</h3>
                  <p className="mt-3 text-[1.1875rem]">{g.text}</p>
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-8 text-base text-ink-2">{t.shotNote}</p>
        </section>

        {/* 4 · the demo to touch */}
        <section aria-labelledby="demo" className="mt-24 md:mt-32">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)] lg:gap-12">
            <div data-reveal className="min-w-0">
              <p className="text-[1.0625rem] font-semibold text-ink-2">{t.demoKick}</p>
              <h2 id="demo" className="mt-2 text-[2.25rem] md:text-[3rem]">
                {t.demoTitle}
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
                scene={v.scene}
                text={{ label: m.camera.label, pause: m.camera.pause, play: m.camera.play, notFound: m.camera.notFound, noBall: m.camera.noBall, caption: v.scene.label }}
                legend={{ own: v.own, opp: v.opp, ref: m.camera.legendRef, number: m.camera.legendNumber, ball: m.camera.legendBall }}
              />
            </div>
          </div>
          <div data-reveal className="mt-10 max-w-[44rem]">
            <ShirtPicker question={m.kit.question} hint={m.kit.hint} names={m.kit.names} />
          </div>
        </section>

        {/* 5 · one link for the team */}
        <section aria-labelledby="share" className="mt-24 md:mt-32">
          <div className="grid grid-cols-1 items-center gap-10 md:grid-cols-2 md:gap-16">
            <div data-reveal className="order-2 md:order-1">
              <div className="mx-auto max-w-[26rem] border-2 border-ink bg-paper shadow-[0_30px_60px_-24px_rgb(10_13_17/0.4)]">
                <img {...SHOT.share} alt={t.shareAlt} loading="lazy" decoding="async" className="block h-auto w-full" />
              </div>
            </div>
            <div data-reveal style={{ "--d": 1 } as CSSProperties} className="order-1 md:order-2">
              <p className="text-[1.0625rem] font-semibold text-ink-2">{t.shareKick}</p>
              <h2 id="share" className="mt-2 text-[2.25rem] md:text-[3rem]">
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
          </div>
        </section>
      </div>

      {/* 6 · why we do it */}
      <section aria-labelledby="story" className="mt-24 bg-ink text-ground md:mt-32">
        <div className="wrap py-16 md:py-24">
          <p data-reveal className="text-[1.0625rem] font-semibold text-[#b9bec4]">
            {t.storyKick}
          </p>
          <h2 id="story" data-reveal className="mt-3 max-w-[52rem] text-[2.5rem] md:text-[4.25rem]">
            {t.storyTitle}
          </h2>
          <p data-reveal className="mt-6 max-w-[40rem] text-[1.1875rem] text-[#dcdfe2] md:text-[1.3125rem]">
            {t.storyText}
          </p>
          <ul className="mt-12 grid grid-cols-1 gap-8 border-t-2 border-[#3a3d42] pt-8 sm:grid-cols-3">
            {t.storyFacts.map((f, i) => (
              <li key={f.text} data-reveal style={{ "--d": i } as CSSProperties}>
                <i aria-hidden className="mark-band mb-5 block h-2 w-14" />
                <span aria-hidden className="font-num block text-[4.5rem] leading-[.85] md:text-[6rem]">
                  {f.figure}
                </span>
                <span className="mt-2 block text-[1.125rem] font-semibold">
                  <span className="sr-only">{f.figure} </span>
                  {f.text}
                </span>
              </li>
            ))}
          </ul>
          <p data-reveal className="mt-12 flex flex-wrap items-center gap-x-4 gap-y-2 text-[1.0625rem] text-[#dcdfe2]">
            <SwissFlag />
            <span className="max-w-[40rem]">{t.storySwiss}</span>
            <Link href={`/${locale}/ueber-uns/`} className="link text-ground">
              {t.storyLink}
            </Link>
          </p>
        </div>
      </section>

      <div className="wrap">
        {/* 7 · trust */}
        <section aria-labelledby="trust" className="mt-20 md:mt-28">
          <h2 id="trust" data-reveal className="text-[2.25rem] md:text-[3rem]">
            {t.trustTitle}
          </h2>
          <ul className="mt-8 grid grid-cols-1 gap-8 md:grid-cols-3">
            {t.trust.map((x, i) => (
              <li key={x.title} data-reveal style={{ "--d": i } as CSSProperties} className="border-t-2 border-ink pt-5">
                <h3 className="font-slant text-[1.5rem] leading-tight">{x.title}</h3>
                <p className="mt-2">{x.text}</p>
              </li>
            ))}
          </ul>
          <div className="mt-4 flex flex-wrap gap-x-8">
            <Link href={`/${locale}/daten/`} className="link">
              {m.cta.data}
            </Link>
            <Link href={`/${locale}/fakten/`} className="link">
              {t.trustHonest}
            </Link>
          </div>
        </section>

        {/* 8 · price */}
        <section aria-labelledby="price" className="mt-20 md:mt-28">
          <div data-reveal className="grid grid-cols-1 items-end gap-6 border-2 border-ink bg-paper p-6 md:grid-cols-[auto_minmax(0,1fr)_auto] md:gap-10 md:p-10">
            <p className="flex items-baseline gap-3">
              <b className="font-num text-[5rem] leading-[.8] text-club-text md:text-[7rem]">{team.price_chf_month}</b>
              <span className="text-[1.0625rem] font-semibold text-ink-2">{t.priceUnit}</span>
            </p>
            <div>
              <h2 id="price" className="text-[2rem] md:text-[2.5rem]">
                {t.priceTitle}
              </h2>
              <p className="mt-2">
                {fmt(t.priceText, { days: team.trial_days })}
                {!PRICES_FINAL && <> {m.pricing.draft}</>}
              </p>
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

        {/* 9 · guides */}
        <section aria-labelledby="guides" className="mt-20 md:mt-28">
          <div className="section-head flex flex-wrap items-baseline justify-between gap-x-6">
            <h2 id="guides" className="text-[1.875rem] md:text-[2.375rem]">
              {m.guides.homeTitle}
            </h2>
            <Link href={`/${locale}/ratgeber/`} className="link">
              {m.guides.all}
            </Link>
          </div>
          <ul className="mt-2 grid grid-cols-1 md:grid-cols-3">
            {FEATURED.map((slug) => GUIDES.find((g) => g.slug === slug)!).map((g) => (
              <li key={g.slug} className="border-b border-rule py-5 md:border-b-0 md:px-6 md:first:pl-0 md:[&+li]:border-l md:[&+li]:border-l-rule">
                <Link href={`/${locale}/ratgeber/${g.slug}/`} className="font-slant text-[1.375rem] leading-tight hover:underline">
                  {g.title[locale] ?? g.title.de}
                </Link>
              </li>
            ))}
          </ul>
        </section>

        {/* 10 · start */}
        <section aria-labelledby="final" className="mt-20 border-t-2 border-ink pt-10 md:mt-28">
          <h2 id="final" className="text-[2.5rem] md:text-[3.75rem]">
            {t.finalTitle}
          </h2>
          <div className="mt-8 grid grid-cols-1 items-end gap-8 md:grid-cols-[minmax(0,34rem)_auto]">
            <TeamField id="team-end" label={t.teamLabel} button={t.teamButton} example={t.teamExample} appLocale={app} />
            <DemoLink href={`/${locale}/demo/`} className="btn btn-line md:mb-9">
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
