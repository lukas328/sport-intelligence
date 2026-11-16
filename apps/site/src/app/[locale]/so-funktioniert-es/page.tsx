import type { Metadata } from "next";
import Link from "next/link";
import type { CSSProperties } from "react";
import { Browser, Phone } from "@/components/device";
import { HallPlan } from "@/components/hall-plan";
import { Reveal } from "@/components/reveal";
import { Honest } from "@/components/honest";
import { KitScope, StartLink } from "@/components/kit";
import { JsonLd } from "@/components/json-ld";
import { PageHead, SectionHead, Updated } from "@/components/wurf-head";
import { graph, howTo } from "@/lib/schema";
import { APP_LOCALE, messages, type Locale } from "@/lib/i18n";
import type { Messages } from "@/messages/de";
import { pageMeta } from "@/lib/seo";

type Props = { params: Promise<{ locale: Locale }> };

/** Pictures from the app (public/app, scripts/app-screens.mjs) under «So sieht es in der App aus». */
const SHOTS = [
  { src: "/app/video.webp", width: 1280, height: 1000, phone: false },
  { src: "/app/szenen.webp", width: 1280, height: 940, phone: false },
  { src: "/app/saison.webp", width: 1280, height: 820, phone: false },
  { src: "/app/teilen-phone.webp", width: 780, height: 812, phone: true },
];

/** K9: each step with a picture from the app (the first with the hall plan: filming happens outside it). */
function StepPicture({ i, alt, plan }: { i: number; alt: string; plan: Messages["filming"] }) {
  if (i === 0) return <HallPlan label={plan.planLabel} camera={plan.planCamera} field={plan.planField} corner={plan.planCorner} />;
  if (i === 1)
    return (
      <div className="border-2 border-ink bg-paper p-4">
        <img src="/app/hochladen-phone.webp" alt={alt} width={780} height={616} loading="lazy" decoding="async" className="block h-auto w-full" />
      </div>
    );
  if (i === 2) return <Phone src="/app/pruefen-phone.webp" alt={alt} width={780} height={1688} className="max-w-[17rem]" />;
  return <Phone src="/app/ergebnis-phone.webp" alt={alt} width={780} height={3760} scroll className="max-w-[17rem]" />;
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
            tools: [m.filming.sections[0]!.items[0]!],
            steps: t.steps.map((s) => ({ name: s.title, text: s.text })),
          }),
        )}
      />
      <Reveal />
      <PageHead kick={t.title} title={t.head} lead={t.lead}>
        <Updated locale={locale} />
      </PageHead>
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
                <StepPicture i={i} alt={s.alt} plan={m.filming} />
              </div>
            </li>
          ))}
        </ol>

        <section aria-labelledby="shots" className="mt-16">
          <SectionHead id="shots" title={t.shotsTitle} note={t.shotsNote} />
          <ul className="mt-8 grid grid-cols-1 gap-10 md:grid-cols-2">
            {t.shots.map((s, i) => {
              const pic = SHOTS[i]!;
              return (
                <li key={pic.src} data-reveal style={{ "--d": i % 2 } as CSSProperties}>
                  <figure className="m-0">
                    {pic.phone ? (
                      <div className="border-2 border-ink bg-paper">
                        <img src={pic.src} alt={s.alt} width={pic.width} height={pic.height} loading="lazy" decoding="async" className="mx-auto block h-auto w-full max-w-[26rem]" />
                      </div>
                    ) : (
                      <Browser src={pic.src} alt={s.alt} width={pic.width} height={pic.height} crop={1280 / 760} />
                    )}
                    <figcaption className="mt-3 text-[1.0625rem]">{s.caption}</figcaption>
                  </figure>
                </li>
              );
            })}
          </ul>
        </section>

        <section aria-labelledby="kann" className="mt-20">
          <SectionHead id="kann" title={m.honest.title} />
          <div className="mt-8">
            <Honest t={m.honest} />
          </div>
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
