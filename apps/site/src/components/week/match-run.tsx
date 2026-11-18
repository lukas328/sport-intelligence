"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import { goalsBy, MATCH_SECONDS as LEN, matchClock, scoreAt, scorerOf, videoPan, type ScorePoint } from "@/lib/match-run";
import type { Phase } from "@/lib/week";
import { reducedMotion, useHydrated, useWeek } from "./events";

export interface PhaseText {
  when: string;
  title: string;
  text: string;
  /** the goals of the phase as rows, only where the phase is short enough to list */
  goals: { clock: string; text: string; team: "own" | "opp"; wing: boolean }[];
}

export interface MatchRunText {
  label: string;
  play: string;
  replay: string;
  phaseLabel: string;
  phaseGoals: string;
  ahead: string;
  behind: string;
  halfMark: string;
  /** the lettering over the blurred video, as in the hero film: «Dein Spiel» */
  video: string;
  /** the word on the video when a goal falls: «Tor» */
  goal: string;
  phases: PhaseText[];
  /** labels on the line: at the start and end of the turn, the final score */
  marks: { at: number; text: string }[];
}

/** milliseconds for the whole match, the turn three times slower (about 20 seconds in all) */
const BASE_MS = 15000;
const SLOW = 3;

/**
 * Saturday in about 20 seconds (BEFUNDE-4 U32, U36): on one side the blurred hall video plays (the
 * hero film's recording, «Dein Spiel» over it, the match clock running), on the other the run of
 * the match is drawn as the goal difference over 60 minutes. One clock drives both: each goal
 * flashes on the video and makes its step in the line; the turn plays slower. Three phases to tap
 * below: the chosen one is marked in yellow on the line (with its word) and lists what happened.
 * The markup is the end state: without JavaScript and with reduced motion the whole line, the
 * final score and the turn stand there at once and the video rests on its still at 60:00. The
 * film starts when the video and the line are seen.
 */
export function MatchRun({ score, phases, own, opp, text }: { score: ScorePoint[]; phases: Phase[]; own: string; opp: string; text: MatchRunText }) {
  const [t, setT] = useState(LEN);
  const [playing, setPlaying] = useState(false);
  const [pick, setPick] = useState(1);
  const stage = useRef<HTMLDivElement>(null);
  const run = phases[1]!;
  const js = useHydrated();

  const play = useCallback(() => {
    if (reducedMotion()) {
      setT(LEN);
      return;
    }
    setPlaying(true);
    setT(0);
  }, []);

  // seconds of match per millisecond, slower in the turn
  useEffect(() => {
    if (!playing) return;
    let raf = 0;
    let last: number | null = null;
    let s = 0;
    const step = (ts: number) => {
      const dt = last == null ? 0 : Math.min(64, ts - last);
      last = ts;
      const speed = LEN / BASE_MS / (s >= run.from && s <= run.to ? SLOW : 1);
      s = Math.min(LEN, s + dt * speed);
      setT(s);
      if (s >= LEN) {
        setPlaying(false);
        return;
      }
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [playing, run.from, run.to]);

  // play once when the video and the line come into view
  useEffect(() => {
    const el = stage.current;
    if (!el || typeof IntersectionObserver === "undefined" || reducedMotion()) return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e?.isIntersecting) return;
        io.disconnect();
        play();
      },
      { threshold: 0.5 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [play]);

  useWeek(
    useCallback((d) => {
      if (d.phase == null) return;
      setPlaying(false);
      setT(LEN);
      setPick(d.phase);
    }, []),
  );

  const now = scoreAt(score, t);
  const chosen = phases[pick]!;

  return (
    <div className="border-2 border-ink bg-paper text-ink shadow-[8px_8px_0_var(--ink)]">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 bg-ink px-4 py-2.5 text-ground md:px-5">
        <p className="flex items-baseline gap-3 font-mono text-[0.9375rem] font-semibold md:text-base" aria-hidden>
          <span>{own}</span>
          <b className="font-num text-[1.75rem] leading-none tabular-nums md:text-[2rem]">
            {now.own}:{now.opp}
          </b>
          <span>{opp}</span>
        </p>
        <button type="button" onClick={play} disabled={playing} className="min-h-11 cursor-pointer border-2 border-ground px-3 text-base font-bold disabled:opacity-60">
          {t >= LEN && !playing ? text.replay : text.play}
        </button>
      </div>

      {/* the video and the line: side by side on wide screens, the video first on the phone */}
      <div ref={stage} className="grid grid-cols-1 lg:grid-cols-2">
        <div className="p-3 sm:p-4 lg:border-r-2 lg:border-ink lg:p-5">
          <RunVideo t={t} playing={playing} score={score} turn={run} own={own} opp={opp} text={text} />
        </div>
        <div className="px-2 pt-2 pb-1 md:px-4 lg:flex lg:items-center lg:py-5">
          <div className="w-full md:hidden">
            <Chart size="small" score={score} t={t} band={chosen} text={text} />
          </div>
          <div className="hidden w-full md:block lg:hidden">
            <Chart size="mid" score={score} t={t} band={chosen} text={text} />
          </div>
          <div className="hidden w-full lg:block">
            <Chart size="half" score={score} t={t} band={chosen} text={text} />
          </div>
        </div>
      </div>

      <div className="border-t-2 border-ink p-4 md:p-5">
        <p id="phases" className="text-base font-semibold text-ink-2">
          {text.phaseLabel}
        </p>
        <div role="group" aria-labelledby="phases" className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
          {phases.map((p, i) => {
            const on = i === pick;
            return (
              <button
                key={p.key}
                type="button"
                aria-pressed={on}
                onClick={() => {
                  setPlaying(false);
                  setT(LEN);
                  setPick(i);
                }}
                className={cn(
                  "grid min-h-14 cursor-pointer grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 border-2 px-3 py-2 text-left",
                  on ? "border-ink bg-[color-mix(in_srgb,var(--attn)_45%,var(--paper))] shadow-[4px_4px_0_var(--ink)]" : "border-ink/25 hover:border-ink",
                )}
              >
                <span className="min-w-0 leading-tight">
                  <span className="block text-base text-ink-2">{text.phases[i]!.when}</span>
                  <b className="block text-[1.125rem]">{text.phases[i]!.title}</b>
                </span>
                <b className="font-num text-[2rem] leading-none">
                  {p.own}:{p.opp}
                </b>
              </button>
            );
          })}
        </div>
        <div aria-live="polite" className="mt-4">
          {!js &&
            text.phases.map((x, i) =>
              i === pick ? null : (
                <p key={x.title} className="measure mb-2 text-[1.0625rem]">
                  <b>{x.when}, {x.title}:</b> {x.text}
                </p>
              ),
            )}
          <p className="measure text-[1.125rem] font-semibold">{text.phases[pick]!.text}</p>
          {text.phases[pick]!.goals.length > 0 && (
            <>
              <p className="mt-3 text-base text-ink-2">{text.phaseGoals}</p>
              <ol className="mt-1 grid grid-cols-1 border-t border-rule sm:grid-cols-2">
                {text.phases[pick]!.goals.map((g) => (
                  <li key={g.clock} className="flex min-h-12 items-center gap-3 border-b border-rule py-1.5 text-[1.0625rem]">
                    <span className="upright w-14 text-[1.125rem]">{g.clock}</span>
                    <span className={cn("min-w-0", g.wing && "font-bold")}>{g.text}</span>
                  </li>
                ))}
              </ol>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * The blurred hall video, in the hero film's style (U36): the same recording (blurred past
 * recognition: no person, number, text or logo), «Dein Spiel» over it, the player bar with the
 * match clock below. The match clock moves the camera (lib/match-run.ts videoPan) and the score in
 * the corner counts along, a small bump for each goal as the line makes its step. In the turn,
 * played slower, each goal also flashes the picture softly and shows «Tor» with the new score for a
 * moment (four flashes in about three seconds: well under three per second; the rest of the match,
 * a goal every quarter second, only counts). Decorative for screen readers: the line next to it
 * carries the match.
 */
function RunVideo({ t, playing, score, turn, own, opp, text }: { t: number; playing: boolean; score: readonly ScorePoint[]; turn: Phase; own: string; opp: string; text: MatchRunText }) {
  const pan = videoPan(t);
  const n = goalsBy(score, t);
  const by = scorerOf(score, n);
  const now = scoreAt(score, t);
  const inTurn = now.clock_s > turn.from && now.clock_s <= turn.to;
  return (
    <div aria-hidden className="relative aspect-[16/10] overflow-hidden border-2 border-ink bg-[#7d7f80] shadow-[4px_4px_0_var(--ink)] md:aspect-[2/1] lg:aspect-[16/10]">
      <img
        src="/media/halle.webp"
        alt=""
        width={800}
        height={450}
        loading="lazy"
        decoding="async"
        className="absolute inset-0 h-full w-full object-cover will-change-transform"
        style={{ transform: `scale(${pan.scale}) translate(${pan.x}%, ${pan.y}%)` }}
      />
      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgb(22_23_26/.05)_40%,rgb(22_23_26/.55))]" />
      <p className="absolute inset-x-0 top-[12%] text-center font-slant text-[1.75rem] leading-none text-white [text-shadow:0_2px_12px_rgb(0_0_0/.5)] md:text-[2.25rem]">
        {text.video}
      </p>
      {/* the score in the corner, as on a match broadcast */}
      <p className="absolute top-2 left-2 bg-ink px-2 py-1 md:top-3 md:left-3">
        <b key={playing ? n : "end"} className={cn("block font-num text-[1.25rem] leading-none text-ground tabular-nums md:text-[1.5rem]", playing && "run-bump")}>
          {now.own}:{now.opp}
        </b>
      </p>
      {/* a goal in the turn: the picture flashes, «Tor» and the new score come up for a moment */}
      {playing && inTurn && n > 0 && by && (
        <div key={n} className="pointer-events-none absolute inset-0">
          <div className="run-flash absolute inset-0 bg-white" />
          <p
            className={cn(
              "run-goal absolute top-1/2 left-1/2 flex flex-col items-center border-2 border-ink px-3 py-1.5 leading-tight shadow-[4px_4px_0_var(--ink)]",
              by === "own" ? "bg-club text-club-ink" : "bg-paper text-ink",
            )}
          >
            <span className="font-mono text-[0.875rem] font-semibold whitespace-nowrap uppercase md:text-[0.9375rem]">
              {text.goal} {by === "own" ? own : opp}
            </span>
            <b className="font-num text-[2rem] leading-none tabular-nums md:text-[2.5rem]">
              {now.own}:{now.opp}
            </b>
          </p>
        </div>
      )}
      <div className="absolute inset-x-2 bottom-2 flex items-center gap-2 font-mono text-[0.8125rem] font-semibold text-white md:inset-x-3 md:bottom-2.5 md:text-[0.9375rem]">
        <svg viewBox="0 0 20 20" className="size-3 shrink-0 md:size-3.5">
          {playing ? <path d="M5 3h3.5v14H5zM11.5 3H15v14h-3.5z" fill="currentColor" /> : <path d="M5 3l12 7-12 7z" fill="currentColor" />}
        </svg>
        <span className="relative h-1 flex-1 bg-white/35">
          <i className="absolute inset-y-0 left-0 bg-white" style={{ width: `${(Math.min(t, LEN) / LEN) * 100}%` }} />
        </span>
        <span className="tabular-nums">{matchClock(t)}</span>
      </div>
    </div>
  );
}

/** the line in three sizes: phone, tablet under the video, the half next to the video */
const SIZES = {
  small: { width: 360, height: 190, padL: 8, padR: 70, top: 30, bottom: 28, font: 13, band: 18, mark: 4, stroke: 2.5 },
  mid: { width: 760, height: 280, padL: 12, padR: 104, top: 40, bottom: 34, font: 16, band: 24, mark: 5.5, stroke: 3.5 },
  half: { width: 500, height: 320, padL: 8, padR: 96, top: 40, bottom: 34, font: 16, band: 24, mark: 5.5, stroke: 3.5 },
} as const;

function Chart({ size, score, t, band, text }: { size: keyof typeof SIZES; score: readonly ScorePoint[]; t: number; band: Phase; text: MatchRunText }) {
  const z = SIZES[size];
  const { width, height, padL, padR, top, bottom, font } = z;
  const diffs = score.map((p) => p.own - p.opp);
  const hi = Math.max(2, ...diffs);
  const lo = Math.min(-2, ...diffs);
  const x = (s: number) => padL + (s / LEN) * (width - padL - padR);
  const y = (d: number) => top + ((hi - d) / (hi - lo)) * (height - top - bottom);
  // a step line: the difference holds until the next goal
  let d = `M${x(0)} ${y(0)}`;
  for (const p of score.slice(1)) d += `H${x(p.clock_s).toFixed(1)}V${y(p.own - p.opp).toFixed(1)}`;
  d += `H${x(LEN)}`;
  const head = scoreAt(score, t);
  const label = { font: `700 ${font}px var(--font-sans)`, fill: "var(--ink)" } as const;
  const soft = { ...label, fill: "var(--ink-2)", font: `600 ${font}px var(--font-sans)` } as const;
  const clip = `run-${size}`;
  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={text.label} className="block w-full">
      <defs>
        <clipPath id={clip}>
          <rect x={0} y={0} width={x(t) + 1} height={height} />
        </clipPath>
      </defs>
      {/* the chosen phase in yellow, with its word above */}
      <rect x={x(band.from)} y={top - z.band} width={Math.max(4, x(band.to) - x(band.from))} height={height - top - bottom + z.band} fill="var(--attn)" opacity={0.75} />
      <text x={(x(band.from) + x(band.to)) / 2} y={top - z.band / 3} textAnchor="middle" style={{ ...label, font: `800 ${font}px var(--font-sans)` }}>
        {band.score}
      </text>
      <line x1={padL} x2={x(LEN)} y1={y(0)} y2={y(0)} stroke="var(--ink)" strokeOpacity={0.45} strokeWidth={1} />
      <line x1={x(LEN / 2)} x2={x(LEN / 2)} y1={top - 6} y2={height - bottom} stroke="var(--ink)" strokeDasharray="2 5" />
      <text x={x(LEN / 2) + 6} y={height - bottom + z.band} style={soft}>
        {text.halfMark}
      </text>
      <text x={x(LEN) + z.band / 2.4} y={y(hi) + 4} style={soft}>
        {`+${hi} ${text.ahead}`}
      </text>
      <text x={x(LEN) + z.band / 2.4} y={y(lo) + 4} style={soft}>
        {`${lo} ${text.behind}`}
      </text>
      <g clipPath={`url(#${clip})`}>
        <path d={`${d}V${y(0)}H${x(0)}Z`} fill="var(--ink)" fillOpacity={0.08} />
        <path d={d} fill="none" stroke="var(--club-line)" strokeWidth={z.stroke} strokeLinejoin="round" />
      </g>
      {t < LEN && <line x1={x(t)} x2={x(t)} y1={top - 6} y2={height - bottom} stroke="var(--ink)" strokeWidth={2} />}
      {t >= LEN &&
        text.marks.map((m) => {
          const p = scoreAt(score, m.at);
          const up = p.own - p.opp >= -1;
          return (
            <g key={m.at}>
              <circle cx={x(m.at)} cy={y(p.own - p.opp)} r={z.mark} fill="var(--ink)" />
              <text x={x(m.at) + (m.at >= LEN ? 8 : 0)} y={y(p.own - p.opp) + (up ? -(z.mark * 2.2) : z.mark * 4.8)} textAnchor={m.at >= LEN ? "start" : "middle"} style={label}>
                {m.text}
              </text>
            </g>
          );
        })}
      {t < LEN && <circle cx={x(t)} cy={y(head.own - head.opp)} r={z.mark} fill="var(--ink)" />}
    </svg>
  );
}
