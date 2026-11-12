import { goalArea } from "./geometry";

const NS = { vectorEffect: "non-scaling-stroke" } as const;

/** The half court in its own coordinates (goal at the top), for bundles, zones and tiles. */
export function HalfCourtLines({ ink = "var(--ink)", opacity = 0.38 }: { ink?: string; opacity?: number }) {
  return (
    <g opacity={opacity}>
      <g fill="none" stroke={ink} strokeWidth={1.2}>
        <path d="M0 0H20V20H0Z" {...NS} />
        <path d="M2.5 0 A6 6 0 0 0 8.5 6 L11.5 6 A6 6 0 0 0 17.5 0" {...NS} />
        <path d="M0.47 0 A9 9 0 0 0 8.5 9 L11.5 9 A9 9 0 0 0 19.53 0" strokeDasharray="4 3" {...NS} />
        <path d="M9.5 7H10.5M9.85 4H10.15" {...NS} />
      </g>
      <rect x={8.5} y={-0.7} width={3} height={0.7} fill={ink} />
    </g>
  );
}

/** The whole court, 40 x 20 m, for the tactics camera. */
export function CourtLines({ floor, area, line, width = 1.5 }: { floor?: string; area?: string; line: string; width?: number }) {
  return (
    <>
      {floor && <rect x={-3} y={-3} width={46} height={26} fill={floor} />}
      {area && (
        <>
          <path d={`${goalArea(6)} Z`} fill={area} />
          <path d={`${goalArea(6)} Z`} fill={area} transform="matrix(-1 0 0 1 40 0)" />
        </>
      )}
      <g fill="none" stroke={line} strokeWidth={width}>
        <rect x={0} y={0} width={40} height={20} {...NS} />
        <path d="M20 0V20" {...NS} />
        {[false, true].map((mirror) => (
          <g key={String(mirror)} transform={mirror ? "matrix(-1 0 0 1 40 0)" : undefined}>
            <path d={goalArea(6)} {...NS} />
            <path d={goalArea(9)} strokeDasharray="5 4" {...NS} />
            <path d="M7 9.5V10.5M4 9.85V10.15" {...NS} />
          </g>
        ))}
      </g>
      <rect x={-0.6} y={8.5} width={0.6} height={3} fill={line} />
      <rect x={40} y={8.5} width={0.6} height={3} fill={line} />
    </>
  );
}
