/**
 * Kit colour comparison (addendum 01, 4.8). Same method and threshold as the API
 * (apps/api/src/handball_api/core/colors.py): CIE76 delta E in CIELAB (D65), similar below 25.
 */
export const SIMILAR_DELTA_E = 25;

export type TeamKitKey = "own" | "own_gk" | "opponent" | "opponent_gk";
/** The referee kit is optional (null: unknown); the analysis leaves it out when it is close to a
 * team's field kit. */
export type KitKey = TeamKitKey | "referee";
export type Kits = Record<TeamKitKey, string> & { referee: string | null };
export const KIT_PAIRS: [KitKey, KitKey][] = [
  ["own", "opponent"],
  ["own", "opponent_gk"],
  ["own_gk", "opponent"],
  ["own", "own_gk"],
  ["opponent", "opponent_gk"],
  ["own", "referee"],
  ["opponent", "referee"],
];

/** What the colour picker opens on while the referee kit is unknown: referees mostly wear yellow. */
export const REFEREE_PICK = "#facc15";

const lin = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const f = (t: number) => (t > (6 / 29) ** 3 ? Math.cbrt(t) : t / (3 * (6 / 29) ** 2) + 4 / 29);

export function hexToLab(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => lin(parseInt(h.slice(i, i + 2), 16) / 255)) as [number, number, number];
  const x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047;
  const y = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  const z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883;
  return [116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))];
}

export function deltaE(a: string, b: string): number {
  const la = hexToLab(a);
  const lb = hexToLab(b);
  return Math.hypot(la[0] - lb[0], la[1] - lb[1], la[2] - lb[2]);
}

/** Pairs of known kits whose colours are too similar (unknown kits are left out). */
export function kitWarnings(kits: Partial<Record<KitKey, string | null>>): [KitKey, KitKey][] {
  return KIT_PAIRS.filter(([a, b]) => {
    const x = kits[a];
    const y = kits[b];
    return !!x && !!y && deltaE(x, y) < SIMILAR_DELTA_E;
  });
}
