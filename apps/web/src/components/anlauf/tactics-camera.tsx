"use client";

import { type CSSProperties, type ReactNode, useEffect, useRef, useState } from "react";
import { CourtLines } from "./court";
import { inView, pathOf, positionAt, presence, type Pt, trailAt, VIEWS, type ViewName } from "./geometry";

const NS = { vectorEffect: "non-scaling-stroke" } as const;
const INK_DARK = "#0a0d11";
const PLAY_MS = 6000;
const CYCLE_MS = 7600;

/** One tracked person of a scene, in court metres (40 x 20). */
export interface SceneTrack {
  team: "own" | "opp" | "ref";
  /** shirt number, only where it was read */
  number?: number | null;
  xy: readonly Pt[];
  /** when each point is (share of the scene); the track shows only while it has data (F5) */
  ts?: readonly number[] | null;
}

/** A stretch where the ball was found in the picture and the analysis knows who holds it. */
export interface BallStretch {
  /** seconds from the scene start */
  from: number;
  to: number;
  team: "own" | "opp";
  number: number;
}

export interface CameraScene {
  /** match clock at the scene start, seconds (the video time when `videoTime`) */
  clock: number;
  /** the throw-off is not set: the clock shows the place in the video (E02) */
  videoTime?: boolean;
  /** length in seconds */
  duration: number;
  tracks: readonly SceneTrack[];
  /** empty: the ball was not found in this scene; nothing is drawn for it */
  ball: readonly BallStretch[];
  scorer?: { team: "own" | "opp"; number: number } | null;
  shot?: Pt | null;
  aim?: Pt | null;
  /** the scorer's way: solid when confirmed, dashed when estimated */
  confirmed: boolean;
  /** label at the shot spot, e.g. "Tor Thalwil 39:55" */
  label?: string | null;
}

export function clockAt(scene: Pick<CameraScene, "clock" | "duration">, t: number): string {
  const s = scene.clock + Math.min(scene.duration, Math.floor(t * scene.duration));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function holderAt(scene: CameraScene, t: number): BallStretch | null {
  const sec = t * scene.duration;
  return scene.ball.find((b) => sec >= b.from && sec <= b.to) ?? null;
}

/** One frame of the tactics camera at t (0 to 1). */
export function CameraFrame({ scene, view, width, dot = 12, t, labels = false }: { scene: CameraScene; view: ViewName; width: number; dot?: number; t: number; labels?: boolean }) {
  const V = VIEWS[view];
  const kk = width / V.box[2];
  const r = dot / kk;
  const f = (p: Pt) => inView(view, p);
  const scorer = (tr: SceneTrack) => scene.scorer != null && tr.team === scene.scorer.team && tr.number === scene.scorer.number;
  const trail = (tr: SceneTrack, col: string, key: string) => {
    const whole = scorer(tr);
    const s = (whole ? trailAt(tr.xy, tr.ts, t, t) : trailAt(tr.xy, tr.ts, t, 0.33)).map(f);
    if (s.length < 2) return [];
    const n = s.length - 1;
    return s.slice(0, -1).map((p, i) => {
      const a = ((i + 1) / n) ** 1.4;
      return (
        <path
          key={`${key}-${i}`}
          d={pathOf([p, s[i + 1]!])}
          stroke={col}
          strokeOpacity={((whole ? 0.5 : 0.12) + (whole ? 0.5 : 0.7) * a).toFixed(2)}
          strokeWidth={((whole ? 2.4 : 1.2) + (whole ? 1.6 : 2) * a).toFixed(2)}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={whole && !scene.confirmed ? "5 4" : undefined}
          {...NS}
        />
      );
    });
  };
  // only the tracks that exist at t: one dot per person seen then, not one per piece of track
  const players = scene.tracks.filter((x) => x.team !== "ref" && presence(x.ts, t) > 0);
  const hold = holderAt(scene, t);
  // the ball only at the player who holds it, and only while it was found in the picture
  const holder = hold ? players.find((x) => x.team === hold.team && x.number === hold.number) : undefined;
  const ballAt: Pt | null = holder ? f(positionAt(holder.xy, holder.ts, t)) : null;
  const done = t >= 1;
  const tf = V.turn ? "matrix(0 1 1 0 0 0)" : undefined;
  return (
    <>
      <g transform={tf}>
        <CourtLines floor="var(--court)" area="rgb(255 255 255 / .06)" line="rgb(226 236 244 / .5)" width={1.3} />
      </g>
      {players.filter((x) => x.team === "opp").flatMap((x, i) => trail(x, "var(--opp-cam-trail)", `o${i}`))}
      {players.filter((x) => x.team === "own").flatMap((x, i) => trail(x, "var(--club-cam)", `u${i}`))}
      {done && scene.shot && (
        <>
          {scene.aim && <path d={pathOf([f(scene.shot), f(scene.aim)])} stroke="#fff" strokeOpacity={0.75} strokeWidth={1.4} {...NS} />}
          <circle cx={f(scene.shot)[0]} cy={f(scene.shot)[1]} r={r * 1.9} fill="none" stroke="#fff" strokeWidth={1.6} strokeDasharray={scene.confirmed ? undefined : "3 3"} {...NS} />
        </>
      )}
      {scene.tracks
        .filter((x) => x.team === "ref" && presence(x.ts, t) > 0)
        .map((x, i) => {
          const p = f(positionAt(x.xy, x.ts, t));
          return <rect key={`ref${i}`} x={p[0] - r * 0.5} y={p[1] - r * 0.5} width={r} height={r} fill="#8d97a1" opacity={presence(x.ts, t)} transform={`rotate(45 ${p[0]} ${p[1]})`} />;
        })}
      {[...players.filter((x) => x.team === "opp"), ...players.filter((x) => x.team === "own")].map((x, i) => {
        const us = x.team === "own";
        const e = f(positionAt(x.xy, x.ts, t));
        return (
          <g key={`p${i}`} opacity={presence(x.ts, t)}>
            {us ? (
              <circle cx={e[0]} cy={e[1]} r={r} fill="var(--club-cam)" stroke={INK_DARK} strokeWidth={1.4} {...NS} />
            ) : (
              <circle cx={e[0]} cy={e[1]} r={r * 0.92} fill="var(--opp-cam)" stroke="var(--opp-cam-edge)" strokeWidth={2.2} {...NS} />
            )}
            {x.number != null && (
              <text
                x={e[0]}
                y={e[1] + r * 0.38}
                textAnchor="middle"
                fill={us ? "var(--club-cam-ink)" : "var(--opp-cam-ink)"}
                style={{ font: `italic 800 ${(r * 1.04).toFixed(3)}px var(--font-display)` }}
              >
                {x.number}
              </text>
            )}
          </g>
        );
      })}
      {ballAt && <Ball at={ballAt} r={r} />}
      {done && labels && scene.shot && scene.label && (
        <g>
          <rect x={f(scene.shot)[0] + r * 2.4} y={f(scene.shot)[1] - 11 / kk} width={(scene.label.length * 7.4 + 16) / kk} height={22 / kk} fill={INK_DARK} />
          <text x={f(scene.shot)[0] + r * 2.4 + 8 / kk} y={f(scene.shot)[1] + 4.5 / kk} fill="#fff" style={{ font: `700 ${13 / kk}px var(--font-sans)` }}>
            {scene.label}
          </text>
        </g>
      )}
    </>
  );
}

/** The ball at the player who holds it: white with a seam, upper right of the dot. Never a flight. */
function Ball({ at, r }: { at: Pt; r: number }) {
  const bx = at[0] + r * 0.95;
  const by = at[1] - r * 0.95;
  const br = r * 0.6;
  return (
    <g data-ball="">
      <circle cx={bx} cy={by} r={br} fill="#fff" stroke={INK_DARK} strokeWidth={1.3} {...NS} />
      <path d={`M${bx - br * 0.86} ${by - br * 0.3}Q${bx} ${by + br * 0.5} ${bx + br * 0.86} ${by - br * 0.3}`} fill="none" stroke={INK_DARK} strokeWidth={1} {...NS} />
    </g>
  );
}

function reducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export interface CameraText {
  label: string;
  pause: string;
  play: string;
  /** shown in the ball line where the ball was not found (long gaps only) */
  notFound: string;
  /** shown when the ball was not found in the whole scene */
  noBall: string;
  caption?: string | null;
  captionSmall?: string | null;
  /** said before the clock, e.g. «Video» when it is the video time */
  clockPrefix?: string | null;
}

/**
 * The tactics camera: positions from the video on a dark court, the ways of the last two
 * seconds, the scorer's whole way. Plays the scene once (6 s), holds, plays again; Pause stops,
 * reduced motion shows the last frame. The ball line underneath says who held the ball, only
 * where it was found.
 */
export function TacticsCamera({
  scene,
  view = "camL",
  width = 900,
  dot = 12,
  text,
  still = false,
  showLabels = true,
  ballLine = true,
  barExtra,
}: {
  scene: CameraScene;
  view?: ViewName;
  width?: number;
  dot?: number;
  text: CameraText;
  still?: boolean;
  showLabels?: boolean;
  ballLine?: boolean;
  /** more controls in the bar, e.g. the switch Video | Taktik */
  barExtra?: ReactNode;
}) {
  const [t, setT] = useState(1);
  const [paused, setPaused] = useState(true);
  const start = useRef<number | null>(null);

  useEffect(() => {
    setPaused(still || reducedMotion());
  }, [still]);

  useEffect(() => {
    if (paused) return;
    let raf = 0;
    start.current = null;
    const tick = (ts: number) => {
      if (start.current == null) start.current = ts;
      const e = (ts - start.current) % CYCLE_MS;
      setT(Math.min(1, e / PLAY_MS));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [paused]);

  const V = VIEWS[view];
  return (
    <figure className="m-0">
      <div className="relative bg-court">
        <svg viewBox={V.box.join(" ")} role="img" aria-label={text.label} className="block w-full">
          <CameraFrame scene={scene} view={view} width={width} dot={dot} t={t} labels={showLabels} />
        </svg>
        {text.caption && (
          <figcaption className="max-sm:static max-sm:max-w-none max-sm:border-t max-sm:border-[#2a3440] absolute top-4 right-4 max-w-[70%] bg-[rgb(10_13_17/0.9)] px-3 py-2 text-[15px] font-bold text-[#eef2f5]">
            {text.caption}
            {text.captionSmall && <small className="mt-0.5 block font-mono text-xs font-medium text-[#a5b0bb]">{text.captionSmall}</small>}
          </figcaption>
        )}
        <div className="flex flex-wrap items-center gap-2.5 bg-court-bar px-3 py-2 font-mono text-[13px] font-semibold text-court-text">
          <button
            type="button"
            className="min-h-11 min-w-11 cursor-pointer border-[1.5px] border-[#8d97a1] bg-court-bar px-2.5 font-sans text-[15px] font-bold text-white"
            aria-pressed={paused}
            onClick={() => setPaused((p) => !p)}
          >
            {paused ? text.play : text.pause}
          </button>
          {barExtra}
          <span className="ml-auto font-mono text-xl font-semibold tabular-nums text-white" aria-live="off">
            {text.clockPrefix ? `${text.clockPrefix} ` : ""}
            {clockAt(scene, t)}
          </span>
        </div>
      </div>
      {ballLine && <BallLine scene={scene} t={t} notFound={text.notFound} noBall={text.noBall} />}
    </figure>
  );
}

/** Who held the ball, only where it was found; the gaps say so. */
export function BallLine({ scene, t = 1, notFound, noBall }: { scene: Pick<CameraScene, "ball" | "duration">; t?: number; notFound: string; noBall: string }) {
  const gap = (flex: number, key: string, word: boolean) => (
    <span
      key={key}
      className="grid place-items-center text-[15px] font-semibold text-ink-2"
      style={{ flex, background: "repeating-linear-gradient(-60deg, transparent 0 5px, color-mix(in srgb, var(--ink) 14%, transparent) 5px 6px)" }}
    >
      {word ? notFound : ""}
    </span>
  );
  if (!scene.ball.length) {
    return (
      <div className="relative mt-2 flex h-[30px] gap-0.5 text-[15px] font-bold" data-testid="ball-line">
        {gap(1, "all", false)}
        <span className="absolute inset-0 grid place-items-center text-[15px] font-semibold text-ink-2">{noBall}</span>
      </div>
    );
  }
  const parts = [];
  let at = 0;
  for (const [i, b] of scene.ball.entries()) {
    if (b.from > at) parts.push(gap(b.from - at, `g${i}`, b.from - at >= 1.5));
    parts.push(
      <span
        key={`s${i}`}
        className="grid place-items-center"
        style={
          (b.team === "own"
            ? { flex: b.to - b.from, background: "var(--club-cam)", color: "var(--club-cam-ink)" }
            : { flex: b.to - b.from, background: "var(--opp)", color: "var(--opp-ink)", boxShadow: "inset 0 0 0 1.5px var(--opp-edge)" }) as CSSProperties
        }
      >
        {b.number}
      </span>,
    );
    at = b.to;
  }
  if (at < scene.duration) parts.push(gap(scene.duration - at, "end", scene.duration - at >= 1.5));
  return (
    <div className="relative mt-2 flex h-[30px] gap-0.5 text-[15px] font-bold" data-testid="ball-line">
      {parts}
      <i aria-hidden className="absolute -top-1 -bottom-1 w-[2.5px] bg-ink" style={{ left: `${t * 100}%` }} />
    </div>
  );
}
