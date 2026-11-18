"use client";

import type { CSSProperties } from "react";
import { useEffect, useRef, useState } from "react";
import { Bundle } from "@/components/anlauf/bundle";
import { HalfCourtLines } from "@/components/anlauf/court";
import { cn } from "@/lib/cn";
import type { StoryCourt } from "@/lib/story";
import type { ThingView } from "@/lib/things";

/** the part of the half court the stage shows: goal to about 12 m (16:10, like the video) */
const BOX: [number, number, number, number] = [-0.6, -1.2, 21.2, 13.25];

export interface HeroFilmText {
  /** what the moving picture shows, for screen readers */
  label: string;
  /** the lettering over the blurred video */
  video: string;
  /** the three stages: video, analysis, three things */
  status: readonly string[];
  /** the score line in the bar */
  score: string;
  replay: string;
  /** the first loading row while the film runs: «Video wird angeschaut», «Analyse läuft» */
  wait: readonly string[];
  /** the count over the court once the goals are down: «11 von 29 über aussen rechts» */
  count: string;
  note: string;
}

/**
 * The hero (BEFUNDE-2 L4, BEFUNDE-3 U22): in about seven seconds what the product does. It opens
 * on the half court, sharp from the first frame; the match video comes in as a window over it (a
 * real hall recording, blurred until nothing but «a hall, a match» is left), and while it plays
 * the analysis lays the goals conceded on the court one after the other. The video goes, the
 * eleven over the right wing stay, and the three things come in below. Then it rests on that picture; the three things can be picked
 * (the court draws that thing's runs), and «Nochmals abspielen» starts it again.
 *
 * Everything is CSS on server-rendered markup, so the headline and this card are there with the
 * first paint, nothing moves the layout (the stage keeps its 16:10 and the rows their place), and
 * the resting state is the markup itself: with reduced motion or without CSS animations the card
 * simply shows the end. Script only picks a thing, restarts the film, and holds it while the card
 * is still below the screen (on the phone it comes after the team field), so it plays when seen.
 */
export function HeroFilm({
  things,
  court,
  text,
}: {
  things: ThingView[];
  court: StoryCourt;
  text: HeroFilmText;
}) {
  const [round, setRound] = useState(0);
  const [picked, setPicked] = useState<number | null>(null);
  const dots = court.dots;
  const k = 440 / BOX[2];
  const box = useRef<HTMLElement>(null);
  useEffect(() => {
    const node = box.current;
    if (!node || typeof IntersectionObserver === "undefined") return;
    if (node.getBoundingClientRect().top < window.innerHeight * 0.8) return;
    // below the first screen: start over and wait until the card is in view
    node.classList.add("film-hold");
    setRound((r) => r + 1);
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e?.isIntersecting) return;
        node.classList.remove("film-hold");
        io.disconnect();
      },
      { threshold: 0.45 },
    );
    io.observe(node);
    return () => io.disconnect();
  }, []);
  const replay = () => {
    setPicked(null);
    setRound((r) => r + 1);
  };
  return (
    <figure ref={box} className="m-0">
      <div className="border-2 border-ink bg-paper text-ink shadow-[8px_8px_0_var(--ink)]">
        {/* the bar: the match and what is happening (video, analysis, three things) */}
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 bg-ink px-4 py-2.5 text-ground md:px-5">
          <span className="font-mono text-[0.9375rem] font-semibold xl:text-base xl:tracking-wide">
            {text.score}
          </span>
          <span
            key={`s${round}`}
            aria-hidden
            className="ml-auto grid shrink-0 font-mono text-[0.9375rem] font-semibold uppercase md:text-base"
          >
            {text.status.map((s, i) => (
              <span
                key={s}
                className={cn(
                  "film-status flex items-center gap-2 justify-self-end [grid-area:1/1]",
                  `film-status-${i}`,
                )}
              >
                <i
                  className={cn(
                    "inline-block size-2.5",
                    i === 0 ? "film-rec bg-[#ff5a4e]" : i === 1 ? "bg-attn" : "bg-[#4fd1a1]",
                  )}
                  style={{ borderRadius: "50%" }}
                />
                {s}
              </span>
            ))}
          </span>
        </div>

        {/* the stage: 16:10, the court from the first frame, the video comes in over it (U22) */}
        <div
          key={`f${round}`}
          role="img"
          aria-label={text.label}
          className="film relative aspect-[16/10] overflow-hidden bg-paper"
        >
          <div aria-hidden className="absolute inset-0">
            {/* the court with the goals conceded, the right wing marked */}
            <div className="film-court absolute inset-0">
              {picked === null || picked === 0 ? (
                <svg viewBox={BOX.join(" ")} className="block h-full w-full">
                  <g className="film-lines">
                    <HalfCourtLines opacity={0.34} />
                  </g>
                  <path
                    className="film-zone"
                    d="M15.4 0H20V5.2H17.8Z"
                    fill="var(--attn)"
                    opacity={0.6}
                  />
                  {dots.map((d, i) => (
                    <g key={i} className="film-dot" style={{ "--i": i } as CSSProperties}>
                      <circle
                        className={d.ra ? undefined : "film-rest"}
                        cx={d.at[0]}
                        cy={d.at[1]}
                        r={(d.ra ? 5.2 : 4.4) / k}
                        fill={d.ra ? "var(--ink)" : "var(--paper)"}
                        stroke="var(--ink)"
                        strokeWidth={d.ra ? 0 : 1.4}
                        vectorEffect="non-scaling-stroke"
                      />
                    </g>
                  ))}
                </svg>
              ) : (
                <Bundle
                  key={picked}
                  goals={things[picked]!.goals}
                  width={440}
                  play
                  clean
                  box={BOX.join(" ")}
                  label={things[picked]!.label}
                  className="h-full"
                />
              )}
              <p className="film-count absolute top-3 left-3 border-2 border-ink bg-paper px-2.5 py-1 font-slant text-[1.0625rem] leading-tight md:top-4 md:left-4 md:text-[1.25rem]">
                {picked === null || picked === 0 ? text.count : things[picked]!.text}
              </p>
            </div>

            {/* the video, as a window over the court: a real recording, blurred past recognition (no
                person, number, text or logo); it plays while the goals land on the court, then goes */}
            <div className="film-video absolute bottom-[5%] left-[3%] w-[46%] aspect-[16/10] overflow-hidden border-2 border-ink bg-[#7d7f80] shadow-[4px_4px_0_var(--ink)]">
              <img
                src="/media/halle.webp"
                alt=""
                width={800}
                height={450}
                fetchPriority="high"
                decoding="async"
                className="film-pan absolute inset-0 h-full w-full object-cover"
              />
              <div className="absolute inset-0 bg-[linear-gradient(180deg,rgb(22_23_26/.05)_40%,rgb(22_23_26/.55))]" />
              <p className="film-word absolute inset-x-0 top-[30%] text-center font-slant text-[1.375rem] leading-none text-white [text-shadow:0_2px_12px_rgb(0_0_0/.5)] sm:text-[1.75rem] md:text-[2.25rem]">
                {text.video}
              </p>
              <div className="film-scan absolute inset-y-0 w-1/3 bg-[linear-gradient(90deg,transparent,rgb(255_210_60/.55),transparent)]" />
              <div className="absolute inset-x-2 bottom-2 flex items-center gap-2 font-mono text-[0.75rem] font-semibold text-white md:inset-x-3 md:bottom-2.5 md:text-[0.8125rem]">
                <svg viewBox="0 0 20 20" className="size-3 shrink-0 md:size-3.5">
                  <path d="M5 3l12 7-12 7z" fill="currentColor" />
                </svg>
                <span className="relative h-1 flex-1 bg-white/35">
                  <i className="film-progress absolute inset-y-0 left-0 w-full origin-left bg-white" />
                </span>
                <span className="max-sm:hidden">60:00</span>
              </div>
            </div>
          </div>
        </div>

        {/* the three things, one row each; a row shows its goals on the court */}
        <ol key={`r${round}`} className="border-t-2 border-ink">
          {things.map((t, i) => {
            const on = (picked ?? 0) === i;
            return (
              <li
                key={i}
                className="relative border-b border-rule last:border-b-0"
                style={{ "--i": i } as CSSProperties}
              >
                {/* while the analysis runs: the row as the app shows it loading */}
                <span
                  aria-hidden
                  className="film-ghost absolute inset-0 grid grid-cols-[4.5rem_minmax(0,1fr)] items-center gap-x-3 px-4 md:grid-cols-[5.25rem_minmax(0,1fr)] md:px-5"
                >
                  <i className="film-shimmer block h-8 w-11 bg-ink/15" />
                  {i === 0 ? (
                    // the first row says, calmly, what is going on: the video is watched, then analysed
                    <span className="grid gap-2">
                      <span className="grid text-base leading-tight font-semibold text-ink-2">
                        {text.wait.map((w, k) => (
                          <span key={w} className={cn("film-wait flex items-center gap-2 [grid-area:1/1]", `film-wait-${k}`)}>
                            <i className="film-shimmer inline-block size-2 shrink-0 bg-club" style={{ borderRadius: "50%" }} />
                            {w}
                          </span>
                        ))}
                      </span>
                      <i className="film-shimmer block h-3 w-[45%] bg-ink/10" />
                    </span>
                  ) : (
                    <span className="grid gap-2">
                      <i className="film-shimmer block h-3.5 w-[70%] bg-ink/15" />
                      <i className="film-shimmer block h-3 w-[45%] bg-ink/10" />
                    </span>
                  )}
                </span>
                <div className="film-row">
                  <button
                    type="button"
                    aria-pressed={on}
                    onClick={() => setPicked(i)}
                    className={cn(
                      "grid min-h-14 w-full cursor-pointer grid-cols-[4.5rem_minmax(0,1fr)] items-center gap-x-3 px-4 py-1.5 text-left md:grid-cols-[5.25rem_minmax(0,1fr)] md:px-5",
                      on
                        ? "bg-[color-mix(in_srgb,var(--attn)_38%,var(--paper))]"
                        : "hover:bg-ink/5",
                    )}
                  >
                    <span className="flex flex-col">
                      <b className="font-num text-[2rem] leading-[.9] text-club-text md:text-[2.25rem]">
                        {t.numeral}
                      </b>
                      <span className="text-base font-semibold whitespace-nowrap text-ink-2">
                        {t.unit}
                      </span>
                    </span>
                    <span className="min-w-0 leading-tight">
                      <span className="block text-[1.0625rem] font-bold md:text-[1.125rem]">
                        {t.text}
                      </span>
                      <span className="block text-[0.9375rem] text-ink-2 md:text-base">
                        {t.sub}
                      </span>
                    </span>
                  </button>
                </div>
              </li>
            );
          })}
        </ol>
      </div>
      <figcaption className="mt-4 flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-base font-medium">
        <span>{text.note}</span>
        <button
          type="button"
          onClick={replay}
          className="film-replay link cursor-pointer text-club-ink"
        >
          {text.replay}
        </button>
      </figcaption>
    </figure>
  );
}
