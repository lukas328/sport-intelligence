import type { CSSProperties, ReactNode } from "react";
import { ProductShot } from "@/components/product-shot";
import { cn } from "@/lib/cn";
import { productShot, type ShotName } from "@/lib/product-shots";
import type { TourTimeline } from "@/lib/tour-cuts";

/**
 * The app tour's pictures as «Ausriss» (BEFUNDE-4 U34, Lukas' variant 3): the capture of the
 * whole app steps back, dimmed and a little smaller, and the one or two places that carry the
 * message are pulled out of it, about twice as large, as cards that break over the picture's
 * edge, each with a short yellow label; a thin ink line ties a card to its place in the picture.
 *
 * The cards are live components, not crops of the capture (README of scripts/product-shots,
 * «Capture or component»): they mirror the app's look at that place in the site's fonts and
 * tokens, speak the page's language, stay sharp at any size and wear the visitor's shirt
 * (the kit's CSS variables). Their figures are the captures' (lib/tour-cuts.ts). Only the
 * dimmed picture behind them is a capture, the proof that it is the real app.
 */

export interface TourCut {
  /** the place's id in the picture's manifest (`marks`, set by its template) */
  id: string;
  /** the yellow label on the card */
  label: string;
  /** the card itself: one of the components below */
  content: ReactNode;
}

/** where each card sits on the stage, in per cent of the figure (the picture fills 10 to 100) */
const PLACES: Record<string, Record<string, { left: number; top: number; width: number }>> = {
  "get-video": { tap: { left: 50, top: 4, width: 54 }, timeline: { left: -6, top: 58, width: 72 } },
  "get-search": { answer: { left: -6, top: 8, width: 76 }, play: { left: 30, top: 80, width: 40 } },
  "get-season": { bars: { left: -6, top: 48, width: 80 } },
  share: { chat: { left: -6, top: 10, width: 50 }, nologin: { left: 2, top: 74, width: 36 } },
};

/** the picture's share of the figure on the stage: smaller and pushed right, so it steps back */
const PIC = { left: 10, width: 90 };

/**
 * One tour picture with its cards. `stage`: the wide tour (cards over the picture's edge, lines
 * to their places); `flow`: the calm version and the phone (the cards stacked under the picture,
 * large enough to read).
 */
export function TourShot({
  name,
  base,
  alt,
  lettering,
  sizes,
  cuts,
  mode,
}: {
  name: ShotName;
  /** the picture without its language (get-search …), for the places of its cards */
  base: string;
  alt: string;
  lettering?: string;
  sizes: string;
  cuts: TourCut[];
  mode: "stage" | "flow";
}) {
  const marks = productShot(name).marks;
  const places = PLACES[base] ?? {};
  const picture = (
    <div className="tour-dim relative">
      <ProductShot name={name} alt={alt} labels={{}} lettering={lettering} sizes={sizes} />
      {/* the places the cards come from: a thin ink frame on the dimmed picture */}
      <svg aria-hidden viewBox="0 0 100 100" preserveAspectRatio="none" className="pointer-events-none absolute inset-0 h-full w-full overflow-visible">
        {cuts.map((c) => {
          const m = marks[c.id];
          return m ? <rect key={c.id} x={m[0]} y={m[1]} width={m[2]} height={m[3]} fill="none" stroke="var(--ink)" strokeWidth={2} vectorEffect="non-scaling-stroke" /> : null;
        })}
      </svg>
    </div>
  );

  if (mode === "flow")
    return (
      <figure className="m-0">
        {picture}
        <div className="relative z-[1] -mt-8 grid gap-7 pr-1 pl-3 sm:pl-6">
          {cuts.map((c, i) => (
            <Card key={c.id} label={c.label} className={cn("w-full max-w-[34rem]", i % 2 === 1 && "justify-self-end")}>
              {c.content}
            </Card>
          ))}
        </div>
      </figure>
    );

  return (
    <figure className="relative m-0">
      <div className="relative" style={{ marginLeft: `${PIC.left}%`, width: `${PIC.width}%` }}>
        {picture}
      </div>
      {/* thin ink lines from each place to its card, under the cards */}
      <svg aria-hidden viewBox="0 0 100 100" preserveAspectRatio="none" className="pointer-events-none absolute inset-0 h-full w-full overflow-visible">
        {cuts.map((c) => {
          const m = marks[c.id];
          const p = places[c.id];
          if (!m || !p) return null;
          const x1 = PIC.left + (PIC.width * (m[0] + m[2] / 2)) / 100;
          const y1 = m[1] + m[3] / 2;
          return <line key={c.id} x1={x1} y1={y1} x2={p.left + p.width / 2} y2={p.top + 6} stroke="var(--ink)" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />;
        })}
      </svg>
      {cuts.map((c) => {
        const p = places[c.id];
        if (!p) return null;
        return (
          <Card key={c.id} label={c.label} className="absolute" style={{ left: `${p.left}%`, top: `${p.top}%`, width: `${p.width}%` }}>
            {c.content}
          </Card>
        );
      })}
    </figure>
  );
}

/** a cut-out: the app's paper with an ink edge and a hard shadow, its label hanging on top */
function Card({ label, className, style, children }: { label: string; className?: string; style?: CSSProperties; children: ReactNode }) {
  return (
    <div className={cn("[container-type:inline-size]", className)} style={style}>
      <span className="relative z-[1] ml-3 inline-block -translate-y-1 border-2 border-ink bg-attn px-2.5 py-1 text-[clamp(1rem,3.4cqi,1.5rem)] leading-tight font-bold text-ink shadow-[3px_3px_0_var(--ink)]">
        {label}
      </span>
      <div className="-mt-3 border-2 border-ink bg-paper text-ink shadow-[6px_6px_0_rgb(22_23_26/0.28)]" style={{ fontSize: "clamp(1rem, 4.8cqi, 1.75rem)" }}>
        {children}
      </div>
    </div>
  );
}

/** «Szenen»: the answer with its base (26 von 77 …), as the app shows it under the search */
export function AnswerCut({ n, of, base }: { n: number; of: string; base: string }) {
  return (
    <div className="flex items-end gap-[.55em] px-[.8em] pt-[1em] pb-[.8em]">
      <span className="font-num text-[3.4em] leading-[.78]">{n}</span>
      <span className="grid min-w-0 gap-[.2em]">
        <b className="text-[1.1em] leading-tight">{of}</b>
        <span className="text-[.9em] leading-snug text-ink-2">{base}</span>
      </span>
    </div>
  );
}

/** a button of the app: ink, white words («Alle 26 abspielen», «Link teilen») */
export function ButtonCut({ children }: { children: ReactNode }) {
  return (
    <div className="px-[.7em] pt-[1em] pb-[.7em]">
      <span className="inline-block bg-ink px-[1.1em] py-[.65em] text-[1.05em] leading-none font-bold text-paper">{children}</span>
    </div>
  );
}

/** the scene that plays in the list of the phase, in yellow, with its place below as in the app (no «läuft gerade» any more) */
export function SceneCut({ clock, what, place }: { clock: string; what: string; place: string }) {
  return (
    <div className="pt-[.6em]">
      <div className="grid grid-cols-[3.6em_minmax(0,1fr)] items-center gap-[.5em] bg-attn px-[.8em] py-[.6em]">
        <span className="font-num text-[1.35em] leading-none">{clock}</span>
        <span className="grid leading-snug">
          <span>{what}</span>
          <span className="text-[.9em]">{place}</span>
        </span>
      </div>
    </div>
  );
}

/**
 * The match on one line, as under the app's video: our goals above in the club's colour, theirs
 * below in ink, the phase of the scene in yellow with the playhead at the scene.
 */
export function TimelineCut({ t, words }: { t: TourTimeline; words: { throwOff: string; halfTime: string; fullTime: string } }) {
  const W = 600;
  const x = (minute: number) => 6 + (minute / t.minutes) * (W - 12);
  return (
    <div className="px-[.8em] pt-[1em] pb-[.6em]">
      <svg viewBox={`0 0 ${W} 64`} className="block h-auto w-full" aria-hidden>
        <rect x={x(t.phase[0])} y={4} width={x(t.phase[1]) - x(t.phase[0])} height={56} fill="var(--attn)" />
        <line x1={x(30)} x2={x(30)} y1={6} y2={58} stroke="var(--ink-2)" strokeWidth={1.5} strokeDasharray="2 4" />
        <line x1={4} x2={W - 4} y1={32} y2={32} stroke="var(--ink)" strokeWidth={2} />
        {t.goals.map((g, i) => (
          <rect key={i} x={x(g.minute) - 2} y={g.own ? 12 : 34} width={4} height={18} fill={g.own ? "var(--club-text)" : "var(--ink)"} />
        ))}
        <path d={`M${x(t.scene.minute) - 6} 0h12l-6 8z`} fill="var(--ink)" />
        <line x1={x(t.scene.minute)} x2={x(t.scene.minute)} y1={6} y2={62} stroke="var(--ink)" strokeWidth={2} />
      </svg>
      <p className="mt-[.3em] flex justify-between text-[.8em] text-ink-2">
        <span>{words.throwOff}</span>
        <span>{words.halfTime}</span>
        <span>{words.fullTime}</span>
      </p>
    </div>
  );
}

/** «Saison»: a theme that repeats, its sentence, and one bar per match (the last the newest) */
export function BarsCut({ title, text, scenes, bars }: { title: string; text: string; scenes: string; bars: readonly { name: string; n: number }[] }) {
  const max = Math.max(...bars.map((b) => b.n));
  return (
    <div className="flex items-end gap-[1em] px-[.8em] pt-[1em] pb-[.7em]">
      <div className="grid min-w-0 flex-1 gap-[.3em]">
        <b className="font-slant text-[1.25em] leading-tight">{title}</b>
        <span className="text-[.85em] leading-snug text-ink-2">{text}</span>
        <span className="text-[.8em] font-bold underline decoration-2 underline-offset-4">{scenes}</span>
      </div>
      <div className="flex shrink-0 items-end gap-[.35em]">
        {bars.map((b, i) => (
          <span key={b.name} className="grid w-[4.1em] justify-items-center gap-[.15em]">
            <span className="font-num text-[1.2em] leading-none">{b.n}</span>
            <span className="block w-full" style={{ height: `${(b.n / max) * 3.2}em`, background: i === bars.length - 1 ? "var(--ink-2)" : "#c9c5bd" }} />
            <span className="w-full truncate border-t-2 border-ink pt-[.15em] text-center text-[.6em]">{b.name}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

/** the collection as it arrives in the team chat: a card in the club's colour, title and team */
export function ChatCut({ title, team, meta }: { title: string; team: string; meta: string }) {
  return (
    <div className="bg-[#e4ddd1] px-[1.1em] pt-[1.2em] pb-[1em]">
      <div className="border border-[#d6cfc2] bg-white p-[.35em]">
        <div className="bg-club px-[.7em] pt-[.6em] pb-[1.6em] shadow-[inset_0_0_0_2px_var(--club-edge)] [clip-path:polygon(0_0,100%_0,100%_78%,0_100%)]">
          <span className="font-slant block text-[1.45em] leading-[1.05] text-club-ink">{title}</span>
        </div>
        <p className="px-[.4em] pt-[.6em] pb-[.3em] leading-snug">
          <b className="block">{title}</b>
          <span className="text-[.9em]">
            {team} · {meta}
          </span>
        </p>
      </div>
    </div>
  );
}
