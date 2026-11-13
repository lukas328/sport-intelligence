import { CourtLines } from "@/components/anlauf/court";

/**
 * The hall from above: the court, the camera raised at the middle line on the long side, and what
 * it sees (the whole court with both goal areas).
 */
export function HallPlan({ label, camera, field }: { label: string; camera: string; field: string }) {
  return (
    <figure className="m-0">
      <svg viewBox="-4 -4 48 38" role="img" aria-label={label} className="block w-full">
        <rect x={-4} y={-4} width={48} height={38} fill="var(--paper)" />
        <path d="M20 27.5 L-2.5 -1.5 L42.5 -1.5 Z" fill="var(--club)" fillOpacity={0.14} stroke="var(--club-line)" strokeWidth={0.18} strokeDasharray="0.8 0.6" />
        <CourtLines line="var(--ink)" width={1.6} />
        <rect x={18} y={26.4} width={4} height={2.2} fill="var(--ink)" />
        <circle cx={20} cy={26.4} r={0.7} fill="var(--paper)" />
        <text x={20} y={31.8} textAnchor="middle" fill="var(--ink)" style={{ font: "700 2.1px var(--font-sans)" }}>
          {camera}
        </text>
        <text x={20} y={15.2} textAnchor="middle" fill="var(--ink)" paintOrder="stroke" stroke="var(--paper)" strokeWidth={0.8} style={{ font: "700 2.1px var(--font-sans)" }}>
          {field}
        </text>
      </svg>
    </figure>
  );
}
