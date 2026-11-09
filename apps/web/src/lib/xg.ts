/** xG is only worth showing when most shots on target have a known position: goals from the
 * official report or the score overlay have none. Below this share the figure is mostly guesswork. */
export const XG_MIN_COVERAGE = 0.7;

export interface XgBasis {
  xg: number;
  xg_shots: number;
  xg_coverage: number | null;
}

/** `shown` when the coverage carries the figure; otherwise how many shots on target have a
 * position (`n`) out of all of them (`of`), for the sentence that says why xG is missing. */
export function xgBasis(b: XgBasis): { shown: true } | { shown: false; n: number; of: number } | null {
  if (b.xg_coverage == null) return null; // no shots on target: nothing to say
  if (b.xg_coverage >= XG_MIN_COVERAGE) return { shown: true };
  const of = b.xg_coverage > 0 ? Math.round(b.xg_shots / b.xg_coverage) : null;
  return { shown: false, n: b.xg_shots, of: of ?? b.xg_shots };
}

export const xgShown = (b: Pick<XgBasis, "xg_coverage">) => b.xg_coverage != null && b.xg_coverage >= XG_MIN_COVERAGE;

/** The xG figure of one side, or "-" when too few of its shots have a position. */
export const xgLabel = (b: Pick<XgBasis, "xg" | "xg_coverage">) => (xgShown(b) ? b.xg.toFixed(1) : "-");
