import type { CSSProperties, ReactNode } from "react";
import { BallIcon } from "@/components/ball-icon";
import { cn } from "@/lib/cn";
import { fmt } from "@/lib/i18n";
import { saturday } from "@/lib/story";
import type { Messages } from "@/messages/de";

/**
 * The drawings of the four steps of «So funktioniert es» (BEFUNDE-4 U33, U47): cut-outs on the
 * page's own ground, no box and no dark frame. The court as line art in ink, the yellow cards
 * («3m», «12 %», «ein Tipp», «11 von 29»), the paper cards with the app's words («Video
 * hochladen», «Passt das Spielfeld?», «Aussen rechts zumachen»), the camera, the bell and the
 * ball. Built as live HTML and SVG, not pictures: sharp at any size, words from the message files
 * (`how.art`), and the club's parts (our players, the collection's head) in the visitor's shirt
 * colour from the kit variables; the court stays neutral.
 *
 * Each drawing is laid out on its own grid of units (640 wide), `--u` is one unit of the drawn
 * width, so the whole drawing scales with its column like a picture; small words never go under
 * 14 px. The ball of each step carries `data-ball`: components/ball-run.tsx runs one ball path
 * through the four (the ball shown there replaces them while it runs).
 *
 * Ported from the earlier picture templates (scripts/product-shots, steps.js and hall.js).
 */

type Pt = readonly [number, number];
type Proj = (p: Pt) => Pt;
type Art = Messages["how"]["art"];

const W = 640;
/** `n` units of the drawing */
const u = (n: number) => `calc(${n} * var(--u))`;
/** a size in units, never under `min` rem (words stay readable on a phone) */
const tx = (n: number, min = 0.875) => `max(${min}rem, ${u(n)})`;
const f1 = (v: number) => v.toFixed(1);

function curve(f: (t: number) => Pt, a: number, b: number, n = 32): Pt[] {
  return Array.from({ length: n + 1 }, (_, i) => f(a + ((b - a) * i) / n));
}
function d(M: Proj, pts: readonly Pt[], close = false): string {
  return `M${pts.map((p) => M(p).map(f1).join(" ")).join("L")}${close ? "Z" : ""}`;
}
/** a flat view from above: metres to units, turned by `rot` degrees round [cx, cy] metres */
function top(x0: number, y0: number, s: number, rot: number, [cx, cy]: Pt): Proj {
  const c = Math.cos((rot * Math.PI) / 180);
  const k = Math.sin((rot * Math.PI) / 180);
  return ([x, y]) => [x0 + s * ((x - cx) * c - (y - cy) * k), y0 + s * ((x - cx) * k + (y - cy) * c)];
}

// the whole court in metres: x along it (goals at x = 0 and 40), y across (0 to 20)
function zonePts(side: -1 | 1): Pt[] {
  const gx = side < 0 ? 0 : 40;
  const s = side < 0 ? 1 : -1;
  return [
    [gx, 2.5],
    ...curve((t) => [gx + s * 6 * Math.cos(t), 8.5 - 6 * Math.sin(t)], Math.PI / 2, 0),
    ...curve((t) => [gx + s * 6 * Math.cos(t), 11.5 + 6 * Math.sin(t)], 0, Math.PI / 2),
    [gx, 17.5],
  ];
}
function ninePts(side: -1 | 1): Pt[] {
  const gx = side < 0 ? 0 : 40;
  const s = side < 0 ? 1 : -1;
  const a = Math.asin(8.5 / 9);
  return [
    ...curve((t) => [gx + s * 9 * Math.cos(t), 8.5 - 9 * Math.sin(t)], a, 0),
    ...curve((t) => [gx + s * 9 * Math.cos(t), 11.5 + 9 * Math.sin(t)], 0, a),
  ];
}

const INK = "var(--ink)";
const LINE = { fill: "none", stroke: INK, strokeWidth: 2, strokeLinejoin: "round" as const };

/** the whole court as line art: a light floor, the goal areas lightly shaded, ink lines, the goals */
function Court({ M, w = 2 }: { M: Proj; w?: number }) {
  const edge: Pt[] = [[0, 0], [40, 0], [40, 20], [0, 20]];
  return (
    <g>
      <path d={d(M, edge, true)} fill="var(--paper)" fillOpacity={0.75} />
      {([-1, 1] as const).map((s) => {
        const gx = s < 0 ? 0 : 40;
        const k = s < 0 ? 1 : -1;
        return (
          <g key={s}>
            <path d={d(M, zonePts(s), true)} {...LINE} fill={INK} fillOpacity={0.07} strokeWidth={w} />
            <path d={d(M, ninePts(s))} {...LINE} strokeWidth={w * 0.8} strokeDasharray={`${f1(w * 3.4)} ${f1(w * 2.6)}`} />
            <path d={d(M, [[gx + k * 7, 9.5], [gx + k * 7, 10.5]])} {...LINE} strokeWidth={w} />
            <path d={d(M, [[gx, 8.5], [gx - k, 8.5], [gx - k, 11.5], [gx, 11.5]])} fill={INK} stroke={INK} strokeWidth={w} strokeLinejoin="miter" />
          </g>
        );
      })}
      <path d={d(M, edge, true)} {...LINE} strokeWidth={w * 1.2} />
      <path d={d(M, [[20, 0], [20, 20]])} {...LINE} strokeWidth={w} />
    </g>
  );
}

/** players as dots: ours in the club's shirt, theirs in white, both with an ink edge */
function Dots({ M, list, ours, r = 9 }: { M: Proj; list: readonly Pt[]; ours: boolean; r?: number }) {
  return (
    <g fill={ours ? "var(--club)" : "#fff"} stroke={INK} strokeWidth={2.4}>
      {list.map((p, i) => {
        const [x, y] = M(p);
        return <circle key={i} cx={f1(x)} cy={f1(y)} r={r} />;
      })}
    </g>
  );
}

/** the drawing's frame: the units, the scaling, one label for the whole drawing */
function Frame({ h, label, className, children }: { h: number; label: string; className?: string; children: ReactNode }) {
  return (
    <div
      role="img"
      aria-label={label}
      className={cn("step-art relative w-full select-none", className)}
      style={{ aspectRatio: `${W} / ${h}`, containerType: "inline-size", "--u": `calc(100cqi / ${W})` } as CSSProperties}
    >
      {children}
    </div>
  );
}

/** an absolutely placed piece at [x, y] units of a drawing `h` high */
function at(x: number, y: number, h: number, extra?: CSSProperties): CSSProperties {
  return { left: `${((x / W) * 100).toFixed(3)}%`, top: `${((y / h) * 100).toFixed(3)}%`, ...extra };
}

/** a cut-out card: square, an ink edge, the site's hard shadow, a little tilted */
function Card({ yellow, tilt, style, className, children }: { yellow?: boolean; tilt: number; style: CSSProperties; className?: string; children: ReactNode }) {
  return (
    <div
      className={cn("absolute border-2 border-ink text-ink shadow-[6px_6px_0_var(--ink)]", yellow ? "bg-attn" : "bg-paper", className)}
      style={{ ...style, rotate: `${tilt}deg` }}
    >
      {children}
    </div>
  );
}

/** the ball of a step, where the ball path passes (components/ball-run.tsx) */
function Ball({ x, y, h, size = 34 }: { x: number; y: number; h: number; size?: number }) {
  return (
    <span data-ball aria-hidden className="step-ball pointer-events-none absolute z-[2] block -translate-x-1/2 -translate-y-1/2" style={at(x, y, h, { width: u(size), height: u(size) })}>
      <BallIcon />
    </span>
  );
}

/** a yellow disc with an ink edge and an icon in it, centred on [x, y] */
function Disc({ x, y, h, size, children }: { x: number; y: number; h: number; size: number; children: ReactNode }) {
  return (
    <span
      aria-hidden
      style={at(x, y, h, { width: u(size), height: u(size), borderRadius: "50%", padding: u(size * 0.2) })}
      className="absolute z-[1] grid -translate-x-1/2 -translate-y-1/2 place-items-center border-2 border-ink bg-attn text-ink shadow-[4px_4px_0_var(--ink)]"
    >
      {children}
    </span>
  );
}

const ICON_CAMERA = (
  <svg viewBox="0 0 24 24" className="h-full w-full" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinejoin="round">
    <path d="M3.5 8.5h3.6l1.6-2.4h6.6l1.6 2.4h3.6v10H3.5z" />
    <circle cx="12" cy="13.2" r="3.2" />
  </svg>
);
const ICON_BELL = (
  <svg viewBox="0 0 24 24" className="h-full w-full" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 16V11a6 6 0 0 1 12 0v5l1.6 2H4.4z" />
    <path d="M10 21h4" />
  </svg>
);
const ICON_CHECK = (
  <svg viewBox="0 0 24 24" className="h-full w-full" fill="none" stroke="currentColor" strokeWidth={3.4} strokeLinecap="square">
    <path d="M4 12.5l5 5L20.5 6" />
  </svg>
);

/**
 * Step 1, «Filmen»: the whole court from above, a little turned, a defence 6-0 (ours) against
 * the attack (theirs, white), the ball with the attack. The camera (the yellow disc) at the
 * middle of the near sideline, what it sees over the whole court with both goals (the light
 * yellow fan, dotted edges), «3m» on the yellow card beside it, the sentence on a paper card.
 */
function Film({ t, label }: { t: Art["film"]; label: string }) {
  const H = 500;
  const M = top(320, 186, 13.6, -4, [20, 10]);
  const OURS: Pt[] = [[0.9, 10], [6.6, 3.6], [7.4, 7.2], [7.7, 10.1], [7.4, 12.9], [6.6, 16.4]];
  const THEIRS: Pt[] = [[10.6, 2.6], [11.4, 7.1], [7.9, 8.8], [10.4, 11.8], [11.2, 15.6], [9.6, 18.3], [39.1, 10]];
  const ball = M([12.3, 6.4]);
  const cam = M([20, 24]);
  const fan: Pt[] = [cam, M([-1.4, 20.6]), M([-1.4, -0.6]), M([41.4, -0.6]), M([41.4, 20.6])];
  const fanD = `M${fan.map((p) => p.map(f1).join(" ")).join("L")}Z`;
  const edges = `M${[fan[1]!, cam, fan[4]!].map((p) => p.map(f1).join(" ")).join("L")}M${[fan[1]!, fan[2]!, fan[3]!, fan[4]!].map((p) => p.map(f1).join(" ")).join("L")}`;
  return (
    <Frame h={H} label={label}>
      <svg aria-hidden viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 block h-full w-full overflow-visible">
        <Court M={M} />
        <path d={fanD} fill="var(--attn)" fillOpacity={0.3} />
        <path d={edges} fill="none" stroke={INK} strokeWidth={2.4} strokeDasharray="0.5 7" strokeLinecap="round" strokeLinejoin="round" />
        <Dots M={M} list={OURS} ours />
        <Dots M={M} list={THEIRS} ours={false} />
      </svg>
      <Ball x={ball[0]} y={ball[1]} h={H} size={26} />
      <Disc x={cam[0]} y={cam[1]} h={H} size={80}>
        {ICON_CAMERA}
      </Disc>
      <Card yellow tilt={-5} style={at(392, 372, H, { padding: `${u(6)} ${u(20)} ${u(12)}` })}>
        <span className="font-num block leading-[.85] whitespace-nowrap" style={{ fontSize: u(96) }}>
          3m
        </span>
      </Card>
      <Card tilt={2} style={at(18, 384, H, { width: u(300), padding: `${u(12)} ${u(16)} ${u(14)}` })}>
        <p className="leading-[1.2] font-bold" style={{ fontSize: tx(23) }}>
          {t.say}
        </p>
      </Card>
    </Frame>
  );
}

/**
 * Step 2, «Hochladen»: the app's sheet «Video hochladen» as a paper card (TSV Nachtwind, the
 * website's match, chosen in ink; SG Blitzfang below), overlapped by the yellow card of the upload
 * running («12 %», the bar, the size, the app's words), the ball on its way up, and the bell: the
 * coach can put the phone away.
 */
function Upload({ t, label }: { t: Art["upload"]; label: string }) {
  const H = 590;
  return (
    <Frame h={H} label={label}>
      <svg aria-hidden viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 block h-full w-full overflow-visible">
        {/* the video goes up: a dotted way from the upload to the ball */}
        <path d="M520 262C540 210 560 160 586 96" fill="none" stroke={INK} strokeWidth={2.4} strokeDasharray="0.5 8" strokeLinecap="round" />
      </svg>
      <Card tilt={-3} style={at(20, 34, H, { width: u(450), padding: `${u(22)} 0 ${u(12)}` })}>
        <p className="font-slant leading-[1.02]" style={{ fontSize: tx(40, 1.25), margin: `0 ${u(22)}` }}>
          {t.title}
        </p>
        <p className="font-semibold leading-tight" style={{ fontSize: tx(21), margin: `${u(10)} ${u(22)} ${u(16)}` }}>
          {t.ask}
        </p>
        {[t.a, t.b].map(([name, date], i) => (
          <p
            key={name}
            className={cn("flex items-baseline justify-between font-bold", i === 0 ? "bg-ink text-paper" : "text-ink")}
            style={{ fontSize: tx(22), margin: `0 ${u(12)}`, padding: `${u(13)} ${u(12)}`, gap: u(12) }}
          >
            <span>{name}</span>
            <span className={cn("font-medium", i === 0 ? "" : "text-ink-2")} style={{ fontSize: tx(20) }}>
              {date}
            </span>
          </p>
        ))}
      </Card>
      <Card yellow tilt={2} style={at(262, 262, H, { width: u(350), padding: `${u(18)} ${u(24)}` })}>
        <span className="font-num block leading-[.85] whitespace-nowrap" style={{ fontSize: u(118) }}>
          {t.pct}
        </span>
        <span aria-hidden className="block border-2 border-ink" style={{ marginTop: u(18), height: u(22), background: "linear-gradient(90deg, var(--ink) 12%, transparent 12%)" }} />
        <span className="block font-mono font-medium tracking-[.04em] uppercase" style={{ marginTop: u(12), fontSize: tx(19) }}>
          {t.size}
        </span>
      </Card>
      <Ball x={592} y={84} h={H} />
      <Disc x={50} y={540} h={H} size={64}>
        {ICON_BELL}
      </Disc>
      <p className="absolute font-bold leading-[1.2] text-balance" style={at(98, 518, H, { width: u(300), fontSize: tx(23) })}>
        {t.say}
      </p>
    </Frame>
  );
}

// a camera's view (the hall from the stand, the floor at z = 0), then fitted into a box of units
function persp(eye: readonly [number, number, number], look: readonly [number, number, number]) {
  const sub = (a: readonly number[], b: readonly number[]) => a.map((v, i) => v - b[i]!);
  const norm = (a: number[]) => a.map((v) => v / Math.hypot(...a));
  const cross = (a: number[], b: number[]) => [a[1]! * b[2]! - a[2]! * b[1]!, a[2]! * b[0]! - a[0]! * b[2]!, a[0]! * b[1]! - a[1]! * b[0]!];
  const dot = (a: number[], b: number[]) => a.reduce((s, v, i) => s + v * b[i]!, 0);
  const fwd = norm(sub(look, eye));
  const right = norm(cross(fwd, [0, 0, 1]));
  const up = cross(right, fwd);
  // the court seen from the other side of the near sideline: x runs right to left, so mirror it
  return ([x, y]: Pt, z = 0): Pt => {
    const v = sub([40 - x, y, z], eye);
    const zc = Math.max(0.05, dot(v, fwd));
    return [dot(v, right) / zc, -dot(v, up) / zc];
  };
}
function fit(raw: (p: Pt, z?: number) => Pt, [bx, by, bw]: readonly [number, number, number]) {
  const c = [raw([0, 0]), raw([40, 0]), raw([0, 20]), raw([40, 20])];
  const x0 = Math.min(...c.map((p) => p[0]));
  const x1 = Math.max(...c.map((p) => p[0]));
  const y0 = Math.min(...c.map((p) => p[1]));
  const s = bw / (x1 - x0);
  return (p: Pt, z = 0): Pt => {
    const [x, y] = raw(p, z);
    return [bx + (x - x0) * s, by + (y - y0) * s];
  };
}

/**
 * Step 3, «Prüfen»: the court as the camera sees it from the stand, in line art, and the field the
 * analysis proposes in yellow with its four corner points. Over it the paper card of the question
 * with the app's words («Frage 1 von 1», «Passt das Spielfeld?», «Passt» in ink, «Weiss nicht»), the
 * ball on «Passt», the yellow tag «ein Tipp» with a check, and the line under it.
 */
function Check({ t, label }: { t: Art["check"]; label: string }) {
  const H = 590;
  const P3 = fit(persp([20, 34, 28], [20, 9, 0]), [24, 26, 592]);
  const M: Proj = (p) => P3(p);
  const corners: Pt[] = [M([0, 0]), M([40, 0]), M([40, 20]), M([0, 20])];
  const field = `M${corners.map((p) => p.map(f1).join(" ")).join("L")}Z${d(M, [[20, 0], [20, 20]])}`;
  const goal = (gx: number) => {
    const k = gx === 0 ? -1 : 1;
    const g = (y: number, z: number, back = 0): Pt => P3([gx + k * back, y], z);
    const pts = (list: Pt[]) => list.map((p) => p.map(f1).join(" ")).join("L");
    return (
      <g key={gx}>
        <path d={`M${pts([g(8.5, 0, 1), g(8.5, 1.4, 1), g(11.5, 1.4, 1), g(11.5, 0, 1)])}M${pts([g(8.5, 2), g(8.5, 1.4, 1)])}M${pts([g(11.5, 2), g(11.5, 1.4, 1)])}`} fill="none" stroke={INK} strokeOpacity={0.45} strokeWidth={1.4} />
        <path d={`M${pts([g(8.5, 0), g(8.5, 2), g(11.5, 2), g(11.5, 0)])}`} fill="none" stroke={INK} strokeWidth={3.4} strokeLinejoin="miter" />
      </g>
    );
  };
  const ours: Pt[] = [[2.2, 9.6], [6.5, 4], [7.2, 7.5], [7.5, 10.2], [7, 13]];
  const theirs: Pt[] = [[10.2, 3], [10.8, 7.4], [10.2, 11.6], [11.6, 14.8]];
  const lift = (p: Pt): Pt => {
    const [x, y] = M(p);
    return [x, y - 4];
  };
  return (
    <Frame h={H} label={label}>
      <svg aria-hidden viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 block h-full w-full overflow-visible">
        <Court M={M} w={1.8} />
        {goal(0)}
        {goal(40)}
        <Dots M={lift} list={ours} ours r={6.5} />
        <Dots M={lift} list={theirs} ours={false} r={6.5} />
        {/* the proposed field: yellow with an ink edge, so it reads on the light court */}
        <path d={field} fill="var(--attn)" fillOpacity={0.22} stroke={INK} strokeWidth={5.5} strokeLinejoin="round" />
        <path d={field} fill="none" stroke="var(--attn)" strokeWidth={3} strokeLinejoin="round" />
        {corners.map(([x, y], i) => (
          <circle key={i} cx={f1(x)} cy={f1(y)} r={11} fill="var(--attn)" stroke={INK} strokeWidth={3} />
        ))}
      </svg>
      <Card tilt={-2} style={at(22, 240, H, { width: u(440), padding: `${u(18)} ${u(22)} ${u(22)}` })}>
        <p className="font-medium text-ink-2" style={{ fontSize: tx(19) }}>
          {t.count}
        </p>
        <p className="font-slant leading-[1.02]" style={{ fontSize: tx(46, 1.375), margin: `${u(6)} 0 ${u(18)}` }}>
          {t.q}
        </p>
        <p className="flex font-bold" style={{ gap: u(12), fontSize: tx(21) }}>
          <span className="relative flex-1 border-2 border-ink bg-ink whitespace-nowrap text-paper" style={{ padding: `${u(14)} ${u(14)}` }}>
            {t.yes}
          </span>
          <span className="flex-1 border-2 border-ink whitespace-nowrap" style={{ padding: `${u(14)} ${u(14)}` }}>
            {t.no}
          </span>
        </p>
      </Card>
      <Ball x={196} y={434} h={H} />
      <Card yellow tilt={-6} className="flex items-center" style={at(436, 330, H, { gap: u(12), padding: `${u(12)} ${u(20)} ${u(14)} ${u(16)}` })}>
        <span aria-hidden className="block shrink-0" style={{ width: u(46), height: u(46) }}>
          {ICON_CHECK}
        </span>
        <span className="font-slant block leading-[.95]" style={{ fontSize: tx(34, 1.125), width: "min-content" }}>
          {t.tip}
        </span>
      </Card>
      <p className="absolute font-bold leading-[1.2]" style={at(30, 542, H, { width: u(560), fontSize: tx(23) })}>
        {t.say}
      </p>
    </Frame>
  );
}

/**
 * Step 4, «Anschauen und teilen»: the first of the three things of the website's match, «11 von
 * 29» on the yellow card, the half court with the goal at the top and the 11 shot spots of the demo
 * match over the right wing (lib/story.ts saturday()), each with its way into the goal, the ball in
 * the goal. Over it the collection the coach sends to the team chat, as the app shows it: «Aussen
 * rechts zumachen» on the club's colour, «4 Szenen», the team and «Link teilen».
 */
function Result({ t, label }: { t: Art["result"]; label: string }) {
  const H = 600;
  const story = saturday();
  const spots = story.dots.filter((x) => x.ra).map((x) => x.at);
  const others = story.dots.filter((x) => !x.ra).map((x) => x.at);
  // the half court in metres: u across (0 to 20), v away from the goal line; the goal at the top
  const M = top(436, 262, 20, -4, [10, 8.5]);
  const zone: Pt[] = [[2.5, 0], ...curve((t) => [8.5 - 6 * Math.sin(t), 6 * Math.cos(t)], Math.PI / 2, 0), ...curve((t) => [11.5 + 6 * Math.sin(t), 6 * Math.cos(t)], 0, Math.PI / 2), [17.5, 0]];
  const a = Math.asin(8.5 / 9);
  const nine: Pt[] = [...curve((t) => [8.5 - 9 * Math.sin(t), 9 * Math.cos(t)], a, 0), ...curve((t) => [11.5 + 9 * Math.sin(t), 9 * Math.cos(t)], 0, a)];
  const edge: Pt[] = [[0, 0], [20, 0], [20, 17], [0, 17]];
  const goal = M([10, -0.5]);
  return (
    <Frame h={H} label={label}>
      <svg aria-hidden viewBox={`0 0 ${W} ${H}`} className="absolute inset-0 block h-full w-full overflow-visible">
        <path d={d(M, edge, true)} fill="var(--paper)" fillOpacity={0.75} />
        <path d={d(M, zone, true)} {...LINE} fill={INK} fillOpacity={0.07} />
        <path d={d(M, nine)} {...LINE} strokeWidth={1.6} strokeDasharray="7 5" />
        <path d={d(M, [[9.5, 7], [10.5, 7]])} {...LINE} />
        <path d={`${d(M, [[0, 17], [0, 0], [20, 0], [20, 17]])}`} {...LINE} strokeWidth={2.4} />
        <path d={d(M, [[8.5, 0], [8.5, -1], [11.5, -1], [11.5, 0]])} fill={INK} stroke={INK} strokeWidth={2} />
        {/* the other goals conceded, small and white: 11 of all of them */}
        <g fill="#fff" stroke={INK} strokeWidth={2}>
          {others.map((p, i) => {
            const [x, y] = M(p);
            return <circle key={i} cx={f1(x)} cy={f1(y)} r={6} />;
          })}
        </g>
        <g stroke={INK} strokeOpacity={0.55} strokeWidth={1.8}>
          {spots.map((p, i) => (
            <path key={i} d={d(M, [p, [8.8 + (2.4 * i) / Math.max(1, spots.length - 1), 0]])} />
          ))}
        </g>
        {spots.map((p, i) => {
          const [x, y] = M(p);
          return <circle key={i} cx={f1(x)} cy={f1(y)} r={10} fill="var(--attn)" stroke={INK} strokeWidth={2.6} />;
        })}
      </svg>
      <Ball x={goal[0]} y={goal[1]} h={H} size={30} />
      <Card yellow tilt={-3} style={at(12, 30, H, { width: u(300), padding: `${u(16)} ${u(20)} ${u(18)}` })}>
        <p className="flex items-end" style={{ gap: u(14) }}>
          <span className="font-num block leading-[.8]" style={{ fontSize: u(148) }}>
            {story.n}
          </span>
          <span className="font-slant block leading-none whitespace-nowrap" style={{ fontSize: tx(44, 1.25), marginBottom: u(6) }}>
            {fmt(t.of, { n: story.of })}
          </span>
        </p>
        <p className="leading-[1.15] font-bold" style={{ fontSize: tx(25), marginTop: u(14) }}>
          {t.what}
        </p>
      </Card>
      <Card tilt={-2} style={at(22, 384, H, { width: u(404) })}>
        <p className="font-slant border-b-2 border-ink bg-club leading-[1.02] text-club-ink" style={{ fontSize: tx(31, 1.125), padding: `${u(14)} ${u(18)} ${u(16)}` }}>
          {t.title}
        </p>
        <div className="flex items-end justify-between" style={{ gap: u(12), padding: `${u(14)} ${u(16)} ${u(16)} ${u(18)}` }}>
          <p>
            <span className="block font-bold" style={{ fontSize: tx(21) }}>
              {t.scenes}
            </span>
            <span className="block leading-tight font-medium text-ink-2" style={{ fontSize: tx(18), marginTop: u(3) }}>
              {t.team}
            </span>
          </p>
          <span className="shrink-0 bg-ink font-bold text-paper" style={{ fontSize: tx(19), padding: `${u(11)} ${u(14)}` }}>
            {t.share}
          </span>
        </div>
      </Card>
    </Frame>
  );
}

/** The drawing of step `step` (0 to 3) in the visitor's language; `label` is its description. */
export function StepArt({ step, art, label }: { step: number; art: Art; label: string }) {
  if (step === 0) return <Film t={art.film} label={label} />;
  if (step === 1) return <Upload t={art.upload} label={label} />;
  if (step === 2) return <Check t={art.check} label={label} />;
  if (step === 3) return <Result t={art.result} label={label} />;
  return null;
}
