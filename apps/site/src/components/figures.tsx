/**
 * Drawings for the guides (Ratgeber), in the site's look: ink on cloth, the visitor's club colour
 * for «schau hier», dashed for «weniger gut» or «geschätzt». They explain; they are no product output.
 * Every label comes from the MDX file, so each language passes its own words.
 */
import type { ReactNode } from "react";
import { CourtLines, HalfCourtLines } from "@/components/anlauf/court";
import { HALF_BOX } from "@/components/anlauf/geometry";

const LABEL = { font: "700 1.9px var(--font-sans)" } as const;
const SMALL = { font: "600 1.6px var(--font-sans)" } as const;

function Figure({ caption, children }: { caption?: ReactNode; children: ReactNode }) {
  return (
    <figure className="not-prose mx-0 my-8">
      {children}
      {caption && <figcaption className="mt-3 text-[1.0625rem] text-ink-2">{caption}</figcaption>}
    </figure>
  );
}

/** The hall from above: camera raised at the middle line; optionally the places that work less well. */
export function HallCamera({ label, camera, field, avoid, caption }: { label: string; camera: string; field: string; avoid?: string; caption?: ReactNode }) {
  return (
    <Figure caption={caption}>
      <svg viewBox="-6 -6 52 40" role="img" aria-label={label} className="block w-full border-2 border-ink">
        <rect x={-6} y={-6} width={52} height={40} fill="var(--paper)" />
        <path d="M20 27.5 L-2.5 -1.5 L42.5 -1.5 Z" fill="var(--club)" fillOpacity={0.14} stroke="var(--club-line)" strokeWidth={0.18} strokeDasharray="0.8 0.6" />
        <CourtLines line="var(--ink)" width={1.6} />
        {avoid && (
          <g>
            <path d="M-4.6 8.6l2.2 2.8M-2.4 8.6l-2.2 2.8" stroke="var(--loss)" strokeWidth={0.45} />
            <path d="M44.6 8.6l-2.2 2.8M42.4 8.6l2.2 2.8" stroke="var(--loss)" strokeWidth={0.45} />
            <path d="M-4.8 -4.6l1.4 1.8M-3.4 -4.6l-1.4 1.8" stroke="var(--loss)" strokeWidth={0.4} />
            <text x={-2.6} y={-3.1} fill="var(--ink)" style={SMALL}>
              {avoid}
            </text>
          </g>
        )}
        <rect x={18} y={26.4} width={4} height={2.2} fill="var(--ink)" />
        <circle cx={20} cy={26.4} r={0.7} fill="var(--paper)" />
        <text x={20} y={31.8} textAnchor="middle" fill="var(--ink)" style={LABEL}>
          {camera}
        </text>
        <text x={20} y={15.2} textAnchor="middle" fill="var(--ink)" paintOrder="stroke" stroke="var(--paper)" strokeWidth={0.8} style={LABEL}>
          {field}
        </text>
      </svg>
    </Figure>
  );
}

/**
 * The hall from the side, across the court: a camera high up sees over the players to the far
 * side; a low one sees mostly the backs of the nearest players.
 */
export function CameraSide({ label, high, low, width, caption }: { label: string; high: string; low: string; width: string; caption?: ReactNode }) {
  // x: metres across the court (near sideline 0, far 20), y: metres up (drawn upwards)
  const Y = (m: number) => 8 - m;
  const players = [3, 6.5, 11, 15.5];
  const T = { font: "600 1.35px var(--font-sans)" } as const;
  return (
    <Figure caption={caption}>
      <svg viewBox="-8 1 31 10.2" role="img" aria-label={label} className="block w-full border-2 border-ink">
        <rect x={-8} y={1} width={31} height={10.2} fill="var(--paper)" />
        <path d={`M-8 ${Y(0)}H23`} stroke="var(--ink)" strokeWidth={0.08} />
        <path d={`M0 ${Y(0)}H20`} stroke="var(--ink)" strokeWidth={0.25} />
        {/* stand */}
        <path d={`M-7 ${Y(0)}V${Y(3.2)}H-3.6V${Y(1.6)}H-1.8V${Y(0)}Z`} fill="var(--rule)" />
        {players.map((x) => (
          <rect key={x} x={x - 0.3} y={Y(1.9)} width={0.6} height={1.9} fill="var(--ink)" />
        ))}
        {/* high camera */}
        <path d={`M-4.5 ${Y(3.9)}L0 ${Y(0)}M-4.5 ${Y(3.9)}L20 ${Y(0)}`} stroke="var(--club-line)" strokeWidth={0.1} />
        <rect x={-5.1} y={Y(4.2)} width={1.2} height={0.7} fill="var(--club)" stroke="var(--ink)" strokeWidth={0.06} />
        <text x={-7.8} y={Y(4.6)} fill="var(--ink)" style={T}>
          {high}
        </text>
        {/* low camera */}
        <path d={`M-1.2 ${Y(1.2)}L20 ${Y(1.5)}`} stroke="var(--ink-2)" strokeWidth={0.08} strokeDasharray="0.4 0.3" />
        <rect x={-1.8} y={Y(1.5)} width={1.2} height={0.6} fill="var(--paper)" stroke="var(--ink-2)" strokeWidth={0.08} strokeDasharray="0.25 0.2" />
        <text x={-7.8} y={Y(-1.7)} fill="var(--ink-2)" style={T}>
          {low}
        </text>
        <text x={22.6} y={Y(5.2)} textAnchor="end" fill="var(--ink)" style={T}>
          {width}
        </text>
      </svg>
    </Figure>
  );
}

type Pos = "la" | "rl" | "rm" | "rr" | "ra" | "kr" | "tw";
const ATTACK: Record<Exclude<Pos, "tw">, [number, number]> = {
  la: [1.4, 2.6],
  rl: [4.6, 10.2],
  rm: [10, 11.6],
  rr: [15.4, 10.2],
  ra: [18.6, 2.6],
  kr: [10, 6.9],
};
const DEFENCE: Record<string, [number, number][]> = {
  "6:0": [
    [2.6, 2.4],
    [5.2, 5.4],
    [8.4, 6.6],
    [11.6, 6.6],
    [14.8, 5.4],
    [17.4, 2.4],
  ],
  "5:1": [
    [2.6, 2.4],
    [5.4, 5.6],
    [10, 6.7],
    [14.6, 5.6],
    [17.4, 2.4],
    [10, 9.6],
  ],
  "3:2:1": [
    [2.6, 2.4],
    [10, 6.4],
    [17.4, 2.4],
    [5.8, 8.4],
    [14.2, 8.4],
    [10, 10.4],
  ],
};

/** Half court, goal at the top: attack positions with their short names, optionally a defence. */
export function CourtPositions({ label, names, defence, defenceLabel, caption }: { label: string; names: Record<Pos, string>; defence?: "6:0" | "5:1" | "3:2:1"; defenceLabel?: string; caption?: ReactNode }) {
  const [x0, y0, w, h] = HALF_BOX;
  return (
    <Figure caption={caption}>
      <svg viewBox={`${x0 - 0.6} ${y0} ${w + 1.2} ${h + (defenceLabel ? 1.6 : 0)}`} role="img" aria-label={label} className="block w-full max-w-[36rem] border-2 border-ink bg-paper">
        <rect x={x0 - 0.6} y={y0} width={w + 1.2} height={h + 2} fill="var(--paper)" />
        <HalfCourtLines opacity={0.7} />
        <circle cx={10} cy={0.9} r={0.55} fill="var(--ink)" />
        <text x={11} y={1.4} fill="var(--ink)" style={SMALL}>
          {names.tw}
        </text>
        {defence &&
          DEFENCE[defence]!.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={0.55} fill="var(--paper)" stroke="var(--ink)" strokeWidth={0.22} />)}
        {(Object.keys(ATTACK) as (keyof typeof ATTACK)[]).map((k) => {
          const [x, y] = ATTACK[k];
          return (
            <g key={k}>
              <circle cx={x} cy={y} r={0.65} fill="var(--club)" stroke="var(--club-edge)" strokeWidth={0.12} />
              <text x={x} y={y + 2} textAnchor="middle" fill="var(--ink)" paintOrder="stroke" stroke="var(--paper)" strokeWidth={0.5} style={LABEL}>
                {names[k]}
              </text>
            </g>
          );
        })}
        {defenceLabel && (
          <text x={10} y={y0 + h + 1.1} textAnchor="middle" fill="var(--ink)" style={SMALL}>
            {defenceLabel}
          </text>
        )}
      </svg>
    </Figure>
  );
}

/** Goals against by position on the half court, as numbers in rings (an example, marked as such). */
export function ZoneCounts({ label, counts, names, caption }: { label: string; counts: Partial<Record<Exclude<Pos, "tw"> | "m7", number>>; names: Partial<Record<Exclude<Pos, "tw"> | "m7", string>>; caption?: ReactNode }) {
  const [x0, y0, w, h] = HALF_BOX;
  // spread for rings with numbers: the circle and the 7 m mark sit apart, the back court further out
  const at: Record<string, [number, number]> = { la: [1.6, 2.8], ra: [18.4, 2.8], kr: [8.2, 5.4], m7: [12.2, 7.6], rl: [4.4, 10.6], rm: [10, 12.4], rr: [15.6, 10.6] };
  const max = Math.max(1, ...Object.values(counts).map((v) => v ?? 0));
  return (
    <Figure caption={caption}>
      <svg viewBox={`${x0 - 0.6} ${y0} ${w + 1.2} ${h}`} role="img" aria-label={label} className="block w-full max-w-[36rem] border-2 border-ink bg-paper">
        <rect x={x0 - 0.6} y={y0} width={w + 1.2} height={h} fill="var(--paper)" />
        <HalfCourtLines opacity={0.6} />
        {Object.entries(counts).map(([k, v]) => {
          const [x, y] = at[k]!;
          const r = 0.9 + 1.3 * ((v ?? 0) / max);
          return (
            <g key={k}>
              <circle cx={x} cy={y} r={r} fill="var(--club)" fillOpacity={0.18} stroke="var(--club-line)" strokeWidth={0.18} />
              <text x={x} y={y + 0.75} textAnchor="middle" fill="var(--ink)" style={{ font: "800 italic 2.2px var(--font-display)" }}>
                {v}
              </text>
              <text x={x} y={y + r + 1.7} textAnchor="middle" fill="var(--ink)" paintOrder="stroke" stroke="var(--paper)" strokeWidth={0.45} style={SMALL}>
                {names[k as keyof typeof names]}
              </text>
            </g>
          );
        })}
      </svg>
    </Figure>
  );
}

/** One match on a line of 60 minutes: marks above (ours) and below (theirs), the break in the middle. */
export function MatchTimeline({
  label,
  above,
  below,
  aboveLabel,
  belowLabel,
  half,
  caption,
}: {
  label: string;
  above: number[];
  below: number[];
  aboveLabel: string;
  belowLabel: string;
  half: string;
  caption?: ReactNode;
}) {
  const X = (min: number) => 2 + (min / 60) * 56;
  return (
    <Figure caption={caption}>
      <svg viewBox="0 0 60 18" role="img" aria-label={label} className="block w-full border-2 border-ink">
        <rect width={60} height={18} fill="var(--paper)" />
        <path d="M2 9H58" stroke="var(--ink)" strokeWidth={0.25} />
        <path d={`M${X(30)} 3V15`} stroke="var(--ink-2)" strokeWidth={0.15} strokeDasharray="0.6 0.5" />
        <text x={X(30)} y={17.2} textAnchor="middle" fill="var(--ink-2)" style={SMALL}>
          {half}
        </text>
        {[0, 15, 45, 60].map((m) => (
          <text key={m} x={X(m)} y={17.2} textAnchor="middle" fill="var(--ink-2)" style={SMALL}>
            {m}
          </text>
        ))}
        {above.map((m, i) => (
          <rect key={`a${i}`} x={X(m) - 0.35} y={4.6} width={0.7} height={4.4} fill="var(--club)" />
        ))}
        {below.map((m, i) => (
          <rect key={`b${i}`} x={X(m) - 0.35} y={9} width={0.7} height={3.4} fill="var(--ink)" />
        ))}
        <text x={2} y={2.6} fill="var(--ink)" style={SMALL}>
          {aboveLabel}
        </text>
        <text x={58} y={14.4} textAnchor="end" fill="var(--ink)" style={SMALL}>
          {belowLabel}
        </text>
      </svg>
    </Figure>
  );
}

/** Numbered steps; each has an anchor (#schritt-1 …) that the HowTo markup points to. */
export function Steps({ items }: { items: { name: string; text: string }[] }) {
  return (
    <ol className="not-prose my-8 border-t-2 border-ink">
      {items.map((s, i) => (
        <li key={s.name} id={`schritt-${i + 1}`} className="grid scroll-mt-6 grid-cols-[3.25rem_minmax(0,1fr)] gap-x-4 border-b border-rule py-5">
          <span aria-hidden className="font-num text-[3rem] leading-[.85] text-club-text">
            {i + 1}
          </span>
          <div>
            <h3 className="font-slant text-[1.375rem] md:text-[1.5rem]">{s.name}</h3>
            <p className="mt-1 leading-[1.6]">{s.text}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

/** A quiet side note: a rule on the left, no box. */
export function Note({ children }: { children: ReactNode }) {
  return (
    <aside role="note" className="not-prose my-8 border-l-4 border-ink pl-4 leading-[1.6]">
      {children}
    </aside>
  );
}

/** A short checklist with the site's band marks (for «Das brauchst du», «Häufige Fehler»). */
export function Check({ items }: { items: string[] }) {
  return (
    <ul className="not-prose my-6">
      {items.map((x) => (
        <li key={x} className="flex gap-4 border-b border-rule py-3.5 leading-[1.55]">
          <i aria-hidden className="mark-band mt-[.5em] h-2.5 w-4 shrink-0" />
          <span>{x}</span>
        </li>
      ))}
    </ul>
  );
}
