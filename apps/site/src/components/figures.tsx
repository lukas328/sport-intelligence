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

/**
 * The hall from above: the camera raised about nine metres behind the near sideline (a stand) at the middle line,
 * with a wide-angle lens (0.5x, about 120 degrees). Drawn to scale: both goals and goal areas are in
 * the picture, the two near corners are not. Labels sit outside the court.
 */
export function HallCamera({ label, camera, field, corner, caption }: { label: string; camera: string; field: string; corner?: string; caption?: ReactNode }) {
  // camera at (20, 29.5) in court metres: the near goal areas just fit; rays at 60 degrees either side of straight ahead
  const cx = 20;
  const cy = 29.5;
  const k = Math.tan((60 * Math.PI) / 180); // dx per dy
  const yAt = (x: number) => cy - Math.abs(x - cx) / k;
  return (
    <Figure caption={caption}>
      <svg viewBox="-6 -6 52 43" role="img" aria-label={label} className="block w-full border-2 border-ink">
        <rect x={-6} y={-6} width={52} height={43} fill="var(--paper)" />
        <path d={`M${cx} ${cy} L-6 ${yAt(-6).toFixed(2)} L-6 -6 L46 -6 L46 ${yAt(46).toFixed(2)} Z`} fill="var(--club)" fillOpacity={0.13} />
        <path d={`M-6 ${yAt(-6).toFixed(2)} L${cx} ${cy} L46 ${yAt(46).toFixed(2)}`} fill="none" stroke="var(--club-line)" strokeWidth={0.2} strokeDasharray="0.8 0.6" />
        <CourtLines line="var(--ink)" width={1.6} />
        {corner && (
          <g>
            <path d="M0 20l2.6 -2.6M0 17.4l2.6 2.6M40 20l-2.6 -2.6M40 17.4l-2.6 2.6" stroke="var(--loss)" strokeWidth={0.35} />
            <text x={1.3} y={23.2} textAnchor="middle" fill="var(--ink)" style={SMALL}>
              {corner}
            </text>
            <text x={38.7} y={23.2} textAnchor="middle" fill="var(--ink)" style={SMALL}>
              {corner}
            </text>
          </g>
        )}
        <rect x={18} y={cy} width={4} height={2.2} fill="var(--ink)" />
        <circle cx={20} cy={cy} r={0.7} fill="var(--paper)" />
        <text x={20} y={34.9} textAnchor="middle" fill="var(--ink)" style={LABEL}>
          {camera}
        </text>
        <text x={20} y={-2.6} textAnchor="middle" fill="var(--ink)" style={LABEL}>
          {field}
        </text>
      </svg>
    </Figure>
  );
}

/**
 * Two small views from the side, across the court: a low camera sees mostly the backs of the
 * nearest players, a high one sees over them to the far side.
 */
export function CameraSide({ label, high, low, caption }: { label: string; high: string; low: string; width?: string; caption?: ReactNode }) {
  const panel = (camH: number, tone: "low" | "high") => {
    const Y = (m: number) => 7 - m; // metres up, drawn upwards
    const camX = -2.5;
    const players = [3, 7.5, 12, 16.5];
    const line = tone === "high" ? "var(--club-line)" : "var(--ink-2)";
    return (
      <svg viewBox="-5 0 27 8.6" aria-hidden className="block w-full border-2 border-ink">
        <rect x={-5} y={0} width={27} height={8.6} fill="var(--paper)" />
        <path d={`M-5 ${Y(0)}H22`} stroke="var(--ink)" strokeWidth={0.1} />
        <path d={`M0 ${Y(0)}H20`} stroke="var(--ink)" strokeWidth={0.3} />
        {tone === "high" && <path d={`M-5 ${Y(0)}V${Y(camH - 0.6)}H-1.2V${Y(0)}Z`} fill="var(--rule)" />}
        {players.map((x) => (
          <rect key={x} x={x - 0.35} y={Y(1.9)} width={0.7} height={1.9} fill="var(--ink)" />
        ))}
        {/* sight lines: to the far sideline, and over the first player */}
        <path d={`M${camX} ${Y(camH)}L20 ${Y(0)}`} stroke={line} strokeWidth={0.14} strokeDasharray={tone === "low" ? "0.5 0.35" : undefined} />
        <path d={`M${camX} ${Y(camH)}L${players[0]! + 0.35} ${Y(1.9)}`} stroke={line} strokeWidth={0.1} opacity={0.6} />
        <rect x={camX - 0.7} y={Y(camH) - 0.4} width={1.4} height={0.8} fill={tone === "high" ? "var(--club)" : "var(--paper)"} stroke="var(--ink)" strokeWidth={0.08} />
      </svg>
    );
  };
  return (
    <figure role="img" aria-label={label} className="not-prose mx-0 my-8">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          {panel(1.5, "low")}
          <p className="mt-2 text-[1.0625rem]">{low}</p>
        </div>
        <div>
          {panel(4, "high")}
          <p className="mt-2 text-[1.0625rem]">{high}</p>
        </div>
      </div>
      {caption && <figcaption className="mt-3 text-[1.0625rem] text-ink-2">{caption}</figcaption>}
    </figure>
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
