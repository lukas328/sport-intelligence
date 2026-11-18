"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import type { Phase, ScorePoint } from "@/lib/week";
import { reducedMotion, useWeek } from "./events";

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
  phases: PhaseText[];
  /** labels on the line: at the start and end of the turn, the final score */
  marks: { at: number; text: string }[];
}

const LEN = 3600;
/** seconds of play for the whole match, the turn three times slower (about 20 seconds in all) */
const BASE_MS = 15000;
const SLOW = 3;

function scoreAt(score: readonly ScorePoint[], s: number): ScorePoint {
  let cur = score[0]!;
  for (const p of score) if (p.clock_s <= s) cur = p;
  return cur;
}

/**
 * Saturday in about 20 seconds (BEFUNDE-4 U32): the run of the match as the goal difference over
 * 60 minutes, drawn as the match goes, the score counting along, the turn played slower. Three
 * phases to tap: the chosen one is marked in yellow on the line (with its word) and lists what
 * happened. The markup is the end state: without JavaScript and with reduced motion the whole
 * line, the final score and the turn stand there at once; the film starts when the card is seen.
 */
export function MatchRun({ score, phases, own, opp, text }: { score: ScorePoint[]; phases: Phase[]; own: string; opp: string; text: MatchRunText }) {
  const [t, setT] = useState(LEN);
  const [playing, setPlaying] = useState(false);
  const [pick, setPick] = useState(1);
  const box = useRef<HTMLDivElement>(null);
  const run = phases[1]!;

  // seconds of match per millisecond, slower in the turn
  const play = useCallback(() => {
    if (reducedMotion()) {
      setT(LEN);
      return;
    }
    setPlaying(true);
    setT(0);
  }, []);

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

  // play once when the card comes into view
  useEffect(() => {
    const el = box.current;
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
  const clock = `${Math.floor(Math.min(t, LEN) / 60)}:${String(Math.floor(Math.min(t, LEN) % 60)).padStart(2, "0")}`;

  return (
    <div ref={box} className="border-2 border-ink bg-paper text-ink shadow-[8px_8px_0_var(--ink)]">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 bg-ink px-4 py-2.5 text-ground md:px-5">
        <p className="flex items-baseline gap-3 font-mono text-[0.9375rem] font-semibold md:text-base" aria-hidden>
          <span>{own}</span>
          <b className="font-num text-[1.75rem] leading-none tabular-nums md:text-[2rem]">
            {now.own}:{now.opp}
          </b>
          <span>{opp}</span>
        </p>
        <div className="flex items-center gap-3">
          <span className="font-mono text-lg font-semibold tabular-nums" aria-hidden>
            {clock}
          </span>
          <button type="button" onClick={play} disabled={playing} className="min-h-11 cursor-pointer border-2 border-ground px-3 text-base font-bold disabled:opacity-60">
            {t >= LEN && !playing ? text.replay : text.play}
          </button>
        </div>
      </div>
      <div className="px-2 pt-4 md:px-4">
        <div className="md:hidden">
          <Chart width={360} height={190} score={score} t={t} band={chosen} text={text} small />
        </div>
        <div className="hidden md:block">
          <Chart width={1000} height={300} score={score} t={t} band={chosen} text={text} />
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

function Chart({ width, height, score, t, band, text, small = false }: { width: number; height: number; score: readonly ScorePoint[]; t: number; band: Phase; text: MatchRunText; small?: boolean }) {
  const padL = small ? 8 : 16;
  const padR = small ? 70 : 104;
  const top = small ? 30 : 40;
  const bottom = small ? 28 : 36;
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
  const font = small ? 13 : 16;
  const label = { font: `700 ${font}px var(--font-sans)`, fill: "var(--ink)" } as const;
  const clip = `run-${width}`;
  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={text.label} className="block w-full">
      <defs>
        <clipPath id={clip}>
          <rect x={0} y={0} width={x(t) + 1} height={height} />
        </clipPath>
      </defs>
      {/* the chosen phase in yellow, with its word above */}
      <rect x={x(band.from)} y={top - (small ? 18 : 24)} width={Math.max(4, x(band.to) - x(band.from))} height={height - top - bottom + (small ? 18 : 24)} fill="var(--attn)" opacity={0.75} />
      <text x={(x(band.from) + x(band.to)) / 2} y={top - (small ? 6 : 8)} textAnchor="middle" style={{ ...label, font: `800 ${font}px var(--font-sans)` }}>
        {band.score}
      </text>
      <line x1={padL} x2={x(LEN)} y1={y(0)} y2={y(0)} stroke="var(--ink)" strokeOpacity={0.45} strokeWidth={1} />
      <line x1={x(LEN / 2)} x2={x(LEN / 2)} y1={top - 6} y2={height - bottom} stroke="var(--ink)" strokeDasharray="2 5" />
      <text x={x(LEN / 2) + 6} y={height - bottom + (small ? 18 : 24)} style={{ ...label, fill: "var(--ink-2)", font: `600 ${font}px var(--font-sans)` }}>
        {text.halfMark}
      </text>
      <text x={x(LEN) + (small ? 6 : 10)} y={y(hi) + 4} style={{ ...label, fill: "var(--ink-2)", font: `600 ${font}px var(--font-sans)` }}>
        {`+${hi} ${text.ahead}`}
      </text>
      <text x={x(LEN) + (small ? 6 : 10)} y={y(lo) + 4} style={{ ...label, fill: "var(--ink-2)", font: `600 ${font}px var(--font-sans)` }}>
        {`${lo} ${text.behind}`}
      </text>
      <g clipPath={`url(#${clip})`}>
        <path d={`${d}V${y(0)}H${x(0)}Z`} fill="var(--ink)" fillOpacity={0.08} />
        <path d={d} fill="none" stroke="var(--club-line)" strokeWidth={small ? 2.5 : 3.5} strokeLinejoin="round" />
      </g>
      {t < LEN && <line x1={x(t)} x2={x(t)} y1={top - 6} y2={height - bottom} stroke="var(--ink)" strokeWidth={2} />}
      {t >= LEN &&
        text.marks.map((m) => {
          const p = scoreAt(score, m.at);
          return (
            <g key={m.at}>
              <circle cx={x(m.at)} cy={y(p.own - p.opp)} r={small ? 4 : 5.5} fill="var(--ink)" />
              <text x={x(m.at) + (m.at >= LEN ? 8 : 0)} y={y(p.own - p.opp) + (p.own - p.opp >= -1 ? -(small ? 9 : 12) : small ? 20 : 26)} textAnchor={m.at >= LEN ? "start" : "middle"} style={label}>
                {m.text}
              </text>
            </g>
          );
        })}
      {t < LEN && <circle cx={x(t)} cy={y(head.own - head.opp)} r={small ? 4 : 5.5} fill="var(--ink)" />}
    </svg>
  );
}
