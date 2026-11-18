import type { Metadata } from "next";
import type { CSSProperties } from "react";
import Link from "next/link";
import { KitScope, ShirtMenu, ShirtPicker, StartLink } from "@/components/kit";
import { PhoneChat } from "@/components/phone-chat";
import { Reveal } from "@/components/reveal";
import { When } from "@/components/story";
import { AskTry, type Prepared } from "@/components/week/ask-try";
import { MatchRun } from "@/components/week/match-run";
import { SeasonBars } from "@/components/week/season-bars";
import { TrainingTip } from "@/components/week/training-tip";
import { PlayerPhone, Tuesday } from "@/components/week/tuesday";
import { Why } from "@/components/week/why";
import { WurfHead } from "@/components/wurf-head";
import { demoFigures, type DemoGoal } from "@/lib/demo";
import { DRILL_LANG, DRILLS } from "@/lib/drills";
import { APP_LOCALE, fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { sundayAnswer } from "@/lib/story";
import { demoView, MATCH } from "@/lib/things";
import { threeThings } from "@/lib/three-things";
import { matchPhases, preparedAnswers, seasonRightWing } from "@/lib/week";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMeta(locale, "demo", messages(locale).seo.demo.title, messages(locale).seo.demo.description);
}

/**
 * The demo match as one week of a coach (BEFUNDE-4 U32, «Von 27:29 zum Plan für Dienstag»): the
 * invented match HC Tannengrün 27:29 TSV Nachtwind, marked as invented at the top. Saturday: the
 * match in 20 seconds with its turning point to tap. Saturday night: the three things, each with
 * its why (the scenes on the tactics camera, the spot to watch in yellow). Sunday: the insight as
 * one sentence and the training card from the app's library. Tuesday: the collection in the team
 * chat and the player's view without an account. Then three prepared questions to ask, and the
 * next match: the season bar for the right wing, from 11 to 4 (invented follow-up matches, marked
 * as an example). Everything the page shows the app does today; the cause the coach names himself
 * (W32). All figures come from the demo match (lib/week.ts, lib/story.ts, lib/things.ts).
 */
export default async function Demo({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.demo;
  const v = demoView(m);
  const raw = threeThings(v.goals);
  const score = `${v.final.own}:${v.final.opp}`;

  // 1 · Saturday
  const { score: series, phases, half } = matchPhases();
  const [before, run, after] = phases as [(typeof phases)[0], (typeof phases)[0], (typeof phases)[0]];
  const wingInRun = run.goals.filter((g) => g.team === "opp" && g.zone === "ra").length;
  const zoneText = (z: string) => m.things.zones[z as keyof typeof m.things.zones];
  const runText = {
    label: fmt(t.runLabel, { own: v.own, opp: v.opp, from: run.fromClock, to: run.toClock, before: before.score, after: run.score, score }),
    play: t.play,
    replay: t.replay,
    phaseLabel: t.phaseLabel,
    phaseGoals: t.phaseGoals,
    ahead: t.ahead,
    behind: t.behind,
    halfMark: fmt(t.halfMark, { score: half }),
    video: m.home.film.video,
    goal: t.runGoal,
    marks: [
      { at: run.from, text: before.score },
      { at: run.to, text: run.score },
      { at: 3600, text: score },
    ],
    phases: [
      { when: fmt(t.phaseWhen.before, { to: before.toClock }), title: t.phaseTitle.before, text: fmt(t.phaseText.before, { score: before.score, to: before.toClock }), goals: [] },
      {
        when: fmt(t.phaseWhen.run, { from: run.fromClock, to: run.toClock }),
        title: t.phaseTitle.run,
        text: fmt(t.phaseText.run, { before: before.score, after: run.score, n: run.opp, wing: wingInRun }),
        goals: run.goals.map((g) => ({
          clock: g.clock,
          team: g.team,
          wing: g.team === "opp" && g.zone === "ra",
          text: `${fmt(g.team === "opp" ? t.goalOpp : t.goalOwn, { zone: zoneText(g.zone) })}${g.number != null ? ` · ${fmt(t.number, { number: g.number })}` : ""}`,
        })),
      },
      { when: fmt(t.phaseWhen.after, { from: after.fromClock }), title: t.phaseTitle.after, text: fmt(t.phaseText.after, { own: after.own, opp: after.opp }), goals: [] },
    ],
  };
  const figures = demoFigures(MATCH);
  const opp = v.goals.filter((g) => g.team === "opp");
  const zones = (Object.keys(t.zoneNames) as (keyof typeof t.zoneNames)[])
    .map((key) => ({ key, label: t.zoneNames[key], n: opp.filter((g) => g.zone === key).length, strong: key === raw[0]?.zone }))
    .filter((z) => z.n > 0)
    .sort((a, b) => b.n - a.n);

  // 2 · the three things with their why
  const ids = raw.map((x) => x.goals.map((g) => (g as DemoGoal).id));
  const whyThings = v.things.map((x, i) => ({
    index: x.index,
    numeral: x.numeral,
    unit: x.unit,
    text: x.text,
    sub: x.sub,
    label: x.label,
    runs: x.goals,
    rest: x.rest,
    ids: ids[i]!,
    why: t.why[i] ?? "",
    gap: t.gap[i] ?? "",
  }));

  // 3 · the training card
  const lang = DRILL_LANG[locale];
  const drills = [DRILLS.defence_6_0_shift, DRILLS.transition_3v2_back];
  const sunday = sundayAnswer();

  // 4 · Tuesday: the four scenes of the collection (scripts/seed.py: the 2nd, 5th, 8th and 11th over the right wing)
  const wing = [...(raw[0]!.goals as DemoGoal[])].sort((a, b) => a.minute - b.minute);
  const collection = [1, 4, 7, 10].map((k) => wing[k]).filter((g): g is DemoGoal => !!g).map((g) => ({ clock: g.clock, number: g.number }));

  // 5 · three prepared questions
  const a = preparedAnswers();
  const [x1, y1] = sunday.shooters;
  const [x3, y3] = a.works.shooters;
  const q1 = { n: sunday.n, of: sunday.of, first: sunday.first, second: sunday.second, a: x1?.number ?? "", an: x1?.n ?? "", b: y1?.number ?? "", bn: y1?.n ?? "", opp: v.opp };
  const q2 = { ...a.when, opp: v.opp };
  const q3 = { n: a.works.n, of: a.works.of, shots: a.works.shots, a: x3?.number ?? "", an: x3?.n ?? "", b: y3?.number ?? "", bn: y3?.n ?? "", opp: v.opp };
  const prepared: Prepared[] = [
    {
      question: m.home.ask.question,
      answer: fmt(m.home.ask.answer, q1),
      source: fmt(m.home.ask.source, q1),
      queries: m.home.ask.queries.map((q) => fmt(q, q1)),
      scenes: fmt(m.home.ask.scenes, { n: sunday.n }),
      go: { scenes: { ids: ids[0]!, title: m.home.ask.question, thing: 0 } },
      href: "#warum",
    },
    {
      question: t.ask.when.question,
      answer: fmt(t.ask.when.answer, q2),
      source: fmt(t.ask.when.source, q2),
      queries: t.ask.when.queries.map((q) => fmt(q, q2)),
      scenes: fmt(m.home.ask.scenes, { n: run.goals.length }),
      go: { scenes: { ids: run.goals.map((g) => g.id), title: t.ask.when.question } },
      href: "#warum",
    },
    {
      question: t.ask.works.question,
      answer: fmt(t.ask.works.answer, q3),
      source: fmt(t.ask.works.source, q3),
      queries: t.ask.works.queries.map((q) => fmt(q, q3)),
      scenes: fmt(m.home.ask.scenes, { n: a.works.n }),
      go: { scenes: { ids: ids[2] ?? [], title: t.ask.works.question, thing: 2 } },
      href: "#warum",
    },
  ];

  // 6 · the next match
  const season = seasonRightWing();

  return (
    <KitScope>
      <Reveal />
      {/* the yellow band: the match is invented; next to it the colour, so it is found at once (U42) */}
      <div className="relative z-20 border-b-2 border-ink bg-attn py-3 text-ink">
        <div className="wrap flex flex-wrap items-center justify-between gap-x-8 gap-y-3">
          <p role="note" className="min-w-0 flex-[1_1_28rem] text-[1.0625rem]">
            <b>{t.banner}</b> {t.bannerText}
          </p>
          <ShirtMenu label={m.kit.menu} chosenLabel={m.kit.menuChosen} names={m.kit.names} />
        </div>
      </div>
      <WurfHead
        kick={t.kick}
        title={fmt(t.head, { score })}
        lead={t.lead}
        own={v.final.own}
        opp={v.final.opp}
        ownName={v.own}
        oppName={v.opp}
        scoreLabel={fmt(m.match.resultLabel, { own: v.own, opp: v.opp, a: v.final.own, b: v.final.opp })}
        goals={v.report}
        flightLabels={{ half: m.match.flightHalf, end: m.match.flightEnd }}
      />

      <div className="wrap">
        {/* 1 · Saturday: the match in 20 seconds */}
        <section aria-labelledby="samstag" className="mt-16 scroll-mt-24 md:mt-20">
          <div data-reveal className="max-w-[44rem]">
            <When>{t.satWhen}</When>
            <h2 id="samstag" className="mt-4 scroll-mt-24 text-[2.25rem] md:text-[3.25rem]">
              {t.satTitle}
            </h2>
            <p className="mt-3 text-[1.1875rem]">{t.satText}</p>
          </div>
          <div className="mt-8">
            <MatchRun score={series} phases={phases} own={v.own} opp={v.opp} text={runText} />
          </div>
          <details className="group mt-8 border-y-2 border-ink">
            <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-3 text-[1.1875rem] font-bold">
              {t.allFigures}
              <svg viewBox="0 0 20 20" aria-hidden className="size-5 shrink-0 transition-transform group-open:rotate-180">
                <path d="M4 7l6 6 6-6" fill="none" stroke="currentColor" strokeWidth={2.4} />
              </svg>
            </summary>
            <div className="grid grid-cols-1 gap-x-16 gap-y-10 pt-2 pb-8 lg:grid-cols-2">
              <table className="sheet">
                <thead>
                  <tr>
                    <th scope="col">{t.figuresTitle}</th>
                    <th scope="col">{v.own}</th>
                    <th scope="col">{v.opp}</th>
                    <th scope="col" className="hidden text-left sm:table-cell">
                      {t.figuresSource}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {figures.map((f) => (
                    <tr key={f.key}>
                      <th scope="row" className="font-semibold">
                        {t.figures[f.key]}
                        <span className="block text-base font-normal text-ink-2 sm:hidden">{t.source[f.source]}</span>
                      </th>
                      <td className="upright text-[1.25rem]">{f.key === "shootingPct" && f.own != null ? fmt(t.pct, { v: f.own }) : f.own}</td>
                      <td className="upright text-[1.25rem]">{f.key === "shootingPct" && f.opp != null ? fmt(t.pct, { v: f.opp }) : f.opp}</td>
                      <td className="hidden !pl-4 text-left text-base text-ink-2 sm:table-cell">{t.source[f.source]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div>
                <div className="flex flex-wrap items-baseline justify-between gap-x-6 border-b-2 border-ink pb-2">
                  <h3 className="text-[1.125rem]">{t.zonesTitle}</h3>
                  <p className="text-base font-semibold text-ink-2">{fmt(t.zonesTotal, { n: opp.length })}</p>
                </div>
                <ul aria-label={fmt(t.zonesLabel, { opp: v.opp })}>
                  {zones.map((z) => (
                    <li key={z.key} className="grid min-h-12 grid-cols-[minmax(0,9.5rem)_minmax(0,1fr)_2.5rem] items-center gap-x-4 border-b border-rule">
                      <span className={z.strong ? "font-semibold" : undefined}>{z.label}</span>
                      <span aria-hidden className="block h-4">
                        <i className={z.strong ? "block h-full bg-ink" : "block h-full bg-ink/25"} style={{ width: `${(z.n / zones[0]!.n) * 100}%` }} />
                      </span>
                      <span className="upright text-right text-[1.25rem]">{z.n}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </details>
        </section>

        {/* 2 · Saturday night: three things, each with its why */}
        <section aria-labelledby="warum" className="mt-20 md:mt-28">
          <div id="things" data-reveal className="max-w-[44rem] scroll-mt-24">
            <When>{t.thingsWhen}</When>
            <h2 id="warum" className="mt-4 scroll-mt-24 text-[2.25rem] md:text-[3.25rem]">
              {t.thingsTitle}
            </h2>
            <p className="mt-3 text-[1.1875rem]">{t.thingsText}</p>
          </div>
          <Why
            goals={v.goals}
            things={whyThings}
            own={v.own}
            opp={v.opp}
            text={{
              whyTitle: t.whyTitle,
              sceneList: t.sceneList,
              sceneChip: t.sceneChip,
              sceneChipNoNumber: t.sceneChipNoNumber,
              gapLegend: t.gapLegend,
              honest: t.honest,
              askSet: t.askSet,
              goal: m.camera.goal,
              camera: {
                label: `${m.camera.label} ${m.camera.half}.`,
                pause: m.camera.pause,
                play: m.camera.play,
                notFound: m.camera.notFound,
                noBall: m.camera.noBall,
                captionSmall: m.camera.half,
                ballLine: m.camera.ballLine,
              },
              legend: { own: v.own, opp: v.opp, ref: m.camera.legendRef, number: m.camera.legendNumber, ball: m.camera.legendBall },
            }}
          />
        </section>

        {/* 3 · Sunday: the insight as one sentence, the training card from the library */}
        <section aria-labelledby="einsicht" className="mt-20 grid grid-cols-1 gap-10 md:mt-28 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:gap-14">
          <div data-reveal className="min-w-0">
            <When>{t.insightWhen}</When>
            <h2 id="einsicht" className="mt-4 scroll-mt-24 text-[2.25rem] md:text-[3.25rem]">
              {t.insightTitle}
            </h2>
            <blockquote className="mt-6 border-l-[6px] border-[var(--club-line)] pl-5">
              <p className="font-slant text-[1.75rem] leading-[1.12] md:text-[2.25rem]">{t.insight}</p>
              <footer className="mt-3 text-base font-semibold text-ink-2">{t.insightBy}</footer>
            </blockquote>
          </div>
          <div data-reveal style={{ "--d": 1 } as CSSProperties} className="min-w-0">
            <h3 className="mb-4 text-[1.375rem] md:text-[1.5rem]">{t.tipTitle}</h3>
            <TrainingTip
              drills={drills}
              lang={lang}
              text={{
                tabs: t.tipTabs,
                sources: [t.tipSource[0]!, fmt(t.tipSource[1]!, { n: sunday.fast })],
                meta: drills.map((d) => fmt(t.drillMeta, { minutes: d.minutes, players: d.players, level: t.level[d.level] })),
                focus: [t.focus.defence, t.focus.transition_defence],
                howTo: t.howTo,
                parts: t.drillParts,
                sketchLabels: drills.map((d) => fmt(t.sketchLabel, { name: d.name[lang] })),
                plan: t.plan,
              }}
            />
          </div>
        </section>

        {/* 4 · Tuesday: the collection in the team chat, the player's view without an account */}
        <section aria-labelledby="dienstag" className="mt-20 grid grid-cols-1 items-center gap-10 md:mt-28 xl:grid-cols-[minmax(0,0.75fr)_minmax(0,1.25fr)] xl:gap-10">
          <div data-reveal className="min-w-0">
            <When>{t.tueWhen}</When>
            <h2 id="dienstag" className="mt-4 scroll-mt-24 text-[2.25rem] md:text-[3.25rem]">
              {t.tueTitle}
            </h2>
            <p className="mt-4 text-[1.1875rem]">{t.tueText}</p>
          </div>
          <div className="min-w-0">
            <Tuesday labels={t.tueSwitch} chat={<PhoneChat t={m.home.chat} locale={locale} />} player={<PlayerPhone t={t.player} scenes={collection} clock={m.home.chat.clock} />} />
          </div>
        </section>

        {/* 5 · ask your matches, to try: three prepared questions */}
        <section aria-labelledby="fragen" className="mt-20 grid grid-cols-1 items-start gap-x-14 md:mt-28 lg:grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)]">
          <div data-reveal className="max-w-[44rem] lg:sticky lg:top-8">
            <When>{t.askWhen}</When>
            <h2 id="fragen" className="mt-4 scroll-mt-24 text-[2.25rem] md:text-[3.25rem]">
              {t.askTitle}
            </h2>
            <p className="mt-3 text-[1.1875rem]">{t.askText}</p>
          </div>
          <div className="mt-8 min-w-0 lg:mt-2">
            <AskTry items={prepared} bar={m.home.ask.bar} team={`${v.own} ${m.home.chat.group}`} pick={t.askPick} how={m.home.ask.how} />
          </div>
        </section>
      </div>

      {/* 6 · the next match: the season bar for the right wing, from 11 to 4 (invented, marked) */}
      <section
        aria-labelledby="naechstes"
        className="on-club mt-20 bg-club text-club-ink [clip-path:polygon(0_2rem,100%_0,100%_calc(100%-2rem),0_100%)] md:mt-28 md:[clip-path:polygon(0_4rem,100%_0,100%_calc(100%-4rem),0_100%)]"
      >
        <div className="wrap pt-20 pb-20 md:pt-28 md:pb-28">
          <div data-reveal className="max-w-[46rem]">
            <When onClub>{t.nextWhen}</When>
            <h2 id="naechstes" className="mt-4 scroll-mt-24 text-[2.5rem] md:text-[4rem]">
              {fmt(t.nextTitle, { before: season[0]!.n, after: season[1]!.n })}
            </h2>
            <p className="mt-4 text-[1.1875rem] md:text-[1.3125rem]">{t.nextText}</p>
            <p className="mt-4 inline-block border-2 border-dashed border-club-ink px-3 py-1 text-[1.0625rem] font-semibold">{t.nextExample}</p>
          </div>
          <div data-reveal style={{ "--d": 1 } as CSSProperties} className="mt-10 md:mt-14">
            <SeasonBars
              matches={season}
              text={{
                label: t.nextLabel,
                of: season.map((s) => fmt(t.nextOf, { n: s.n, of: s.of })),
                bars: season.map((s) => fmt(t.nextBar, { opp: s.opp, n: s.n, of: s.of })),
                courts: season.map((s) => fmt(t.nextCourt, { opp: s.opp, n: s.n, of: s.of })),
                demo: t.nextDemo,
                example: t.nextTag,
              }}
            />
          </div>
          <p className="mt-10 max-w-[46rem] text-[1.0625rem]">{t.nextNote}</p>
        </div>
      </section>

      <div className="wrap">
        <section aria-labelledby="end" className="mt-16 grid grid-cols-1 gap-12 border-t-2 border-ink pt-10 md:mt-24 lg:grid-cols-[minmax(0,1fr)_minmax(0,28rem)]">
          <div>
            <h2 id="end" className="text-[2.25rem] md:text-[3.25rem]">
              {t.endTitle}
            </h2>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <StartLink appLocale={APP_LOCALE[locale]} className="btn btn-ink">
                {m.cta.start}
              </StartLink>
              <Link href={`/${locale}/so-funktioniert-es/`} className="btn btn-line">
                {m.cta.how}
              </Link>
            </div>
            <p className="mt-3 text-[1.0625rem] text-ink-2">{m.cta.trial}</p>
          </div>
          <ShirtPicker question={m.kit.question} hint={m.kit.hint} names={m.kit.names} />
        </section>
      </div>
    </KitScope>
  );
}
