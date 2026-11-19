import type { Metadata } from "next";
import Link from "next/link";
import type { CSSProperties } from "react";
import { AppTour } from "@/components/app-tour";
import { BallRun } from "@/components/ball-run";
import { StepArt } from "@/components/step-art";
import { cn } from "@/lib/cn";
import { Reveal } from "@/components/reveal";
import { Honest } from "@/components/honest";
import { KitScope, StartLink } from "@/components/kit";
import { JsonLd } from "@/components/json-ld";
import { StepsArt } from "@/components/head-art";
import { PageHead, SectionHead } from "@/components/wurf-head";
import { graph, howTo } from "@/lib/schema";
import { APP_LOCALE, fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { appShot } from "@/lib/product-shots";
import { COLLECTION, SEARCH, SEASON_BARS, tourTimeline } from "@/lib/tour-cuts";
import { HELP } from "../../../../content/help";
import { AnswerCut, BarsCut, ButtonCut, ChatCut, SceneCut, TimelineCut, type TourCut } from "@/components/tour-cuts";

type Props = { params: Promise<{ locale: Locale }> };

/**
 * The four steps are drawn live on the page (components/step-art.tsx, no pictures); under «So
 * sieht es in der App aus» the product pictures (public/product, scripts/product-shots): the same
 * as on the start page plus sharing.
 */
const SHOTS = ["get-video", "get-search", "get-season", "share"] as const;

/**
 * The places each tour picture pulls out as live cut-outs (U34, components/tour-cuts.tsx): the
 * app's words in the page's language, the captures' figures (lib/tour-cuts.ts).
 */
function tourCuts(shot: (typeof SHOTS)[number], m: ReturnType<typeof messages>): TourCut[] {
  const a = m.product.app;
  const p = m.product;
  if (shot === "get-video") {
    const t = tourTimeline();
    return [
      { id: "tap", label: p["get-video"].tap, content: <SceneCut clock={t.scene.clock} what={fmt(a.goal, { team: "TSV Nachtwind", clock: t.scene.clock })} playing={a.playing} /> },
      { id: "timeline", label: p["get-video"].timeline, content: <TimelineCut t={t} words={a} /> },
    ];
  }
  if (shot === "get-search")
    return [
      {
        id: "answer",
        label: p["get-search"].answer,
        content: <AnswerCut n={SEARCH.n} of={fmt(a.answerOf, { of: SEARCH.of })} base={fmt(a.answerBase, { percent: SEARCH.percent, n: SEARCH.last.n, of: SEARCH.last.of })} />,
      },
      { id: "play", label: fmt(p["get-search"].play, { n: SEARCH.n }), content: <ButtonCut>{fmt(a.playAll, { n: SEARCH.n })}</ButtonCut> },
    ];
  if (shot === "get-season")
    return [
      {
        id: "bars",
        label: p["get-season"].bars,
        content: <BarsCut title={a.wingTheme} text={fmt(a.everyMatch, { n: SEARCH.n, of: SEARCH.of })} scenes={fmt(a.scenes, { n: SEARCH.n })} bars={SEASON_BARS} />,
      },
    ];
  return [
    { id: "chat", label: p.share.chat, content: <ChatCut title={a.collection} team={a.team} meta={fmt(a.collectionMeta, { n: COLLECTION.scenes, length: COLLECTION.length })} /> },
    { id: "nologin", label: p.share.nologin, content: <ButtonCut>{a.shareLink}</ButtonCut> },
  ];
}

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
        {/* step 0 (BEFUNDE-5 point 8): once a season, the team says yes or no by link */}
        <section id="schritt-0" aria-labelledby="zero" data-reveal className="mt-14 grid grid-cols-[auto_minmax(0,1fr)] items-start gap-x-6 border-2 border-ink bg-paper p-6 md:mt-20 md:gap-x-10 md:p-10">
          <p aria-hidden className="font-num text-[4.5rem] leading-[.8] text-club-text md:text-[6rem]">
            0
          </p>
          <div className="min-w-0">
            <h2 id="zero" className="text-[2rem] md:text-[2.5rem]">
              {t.zero.title}
            </h2>
            <p className="measure mt-3 text-[1.1875rem]">{t.zero.text}</p>
            <div className="mt-2 flex flex-wrap gap-x-8">
              <Link href={`/${locale}/daten/`} className="link">
                {m.cta.consent}
              </Link>
              <Link href={`/${locale}/hilfe/einwilligungen/`} className="link">
                {`${m.help.title}: ${HELP.find((h) => h.slug === "einwilligungen")!.title[locale]}`}
              </Link>
            </div>
          </div>
        </section>
        {/* the four steps (U47): text and drawing share the row, left and right in turn; the
            drawings are cut-outs on the page's ground, and one ball path runs through them */}
        <div data-steps className="relative mt-14 md:mt-20">
          <BallRun />
          <ol className="relative grid gap-20 md:gap-24 lg:gap-10">
            {t.steps.map((s, i) => {
              const flip = i % 2 === 1;
              return (
                <li key={s.title} id={`schritt-${i + 1}`} className="grid grid-cols-1 items-center gap-y-8 lg:grid-cols-12 lg:gap-x-10">
                  <div data-reveal className={cn("relative z-[2] lg:col-span-5 lg:row-start-1", flip ? "lg:col-start-8" : "lg:col-start-1")}>
                    <p aria-hidden className="font-num text-[6rem] leading-[.8] text-club-text md:text-[8rem] lg:text-[10rem]">
                      {i + 1}
                    </p>
                    <h2 className="mt-3 text-[2.5rem] md:text-[3.25rem] lg:mt-4 lg:text-[3.5rem]">{s.title}</h2>
                    <p className="measure mt-4 text-[1.1875rem] lg:text-[1.25rem]">{s.text}</p>
                    {i === 0 && (
                      <Link href={`/${locale}/aufnahme/`} className="link mt-2">
                        {m.cta.filming}
                      </Link>
                    )}
                  </div>
                  <div
                    data-reveal
                    style={{ "--d": 1 } as CSSProperties}
                    className={cn("relative z-[1] -mx-2 sm:mx-0 lg:col-span-7 lg:row-start-1", flip ? "lg:col-start-1" : "lg:col-start-6")}
                  >
                    <StepArt step={i} art={t.art} label={s.alt} />
                  </div>
                </li>
              );
            })}
          </ol>
        </div>

        <section aria-labelledby="shots" className="mt-16">
          <SectionHead id="shots" title={t.shotsTitle} note={t.shotsNote} />
          {/* one story with the four pictures (L13, U31): a stage with a play on the half court */}
          <AppTour
            label={t.tourLabel}
            hint={t.tourHint}
            items={t.shots.map((s, i) => ({
              player: t.tourPlayers[i]!,
              name: appShot(SHOTS[i]!, locale),
              base: SHOTS[i]!,
              alt: s.alt,
              caption: s.caption,
              text: s.text,
              cuts: tourCuts(SHOTS[i]!, m),
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
          <StartLink appLocale={APP_LOCALE[locale]} src="how" className="btn btn-ink">
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
