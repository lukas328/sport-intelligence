/** What decided a match, from the head-to-head figures: the two biggest edges of the winner
 * (in a draw, of either side). Deterministic and only from real figures; null when nothing stands
 * out. Gaps are made comparable in percentage points: a turnover or a fast-break goal counts like
 * a few points of rate. */

export interface Side {
  shooting_pct: number | null;
  save_pct: number | null;
  turnovers: number;
  fast_break_goals: number;
  shots: number;
}
export type Edge = "saves" | "shooting" | "turnovers" | "fastBreaks";
export interface Decided {
  /** whose edges they are */
  side: "own" | "opponent";
  edges: Edge[];
}

const MIN_SHOTS = 10; // rates from fewer shots say nothing
const MIN_GAP = 8; // points

export function decided(own: Side, opp: Side, result: "won" | "lost" | "draw"): Decided | null {
  const enough = own.shots >= MIN_SHOTS && opp.shots >= MIN_SHOTS;
  const gap = (k: Edge, forOwn: boolean): number | null => {
    const [a, b] = forOwn ? [own, opp] : [opp, own];
    if (k === "saves") return enough && a.save_pct != null && b.save_pct != null ? (a.save_pct - b.save_pct) * 100 : null;
    if (k === "shooting") return enough && a.shooting_pct != null && b.shooting_pct != null ? (a.shooting_pct - b.shooting_pct) * 100 : null;
    if (k === "turnovers") return (b.turnovers - a.turnovers) * 4;
    return (a.fast_break_goals - b.fast_break_goals) * 5;
  };
  const pick = (forOwn: boolean) =>
    (["saves", "shooting", "turnovers", "fastBreaks"] as Edge[])
      .map((k) => [k, gap(k, forOwn)] as const)
      .filter((x): x is readonly [Edge, number] => x[1] != null && x[1] >= MIN_GAP)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 2)
      .map(([k]) => k);
  if (result === "draw") {
    const o = pick(true);
    const p = pick(false);
    if (!o.length && !p.length) return null;
    return o.length >= p.length ? { side: "own", edges: o } : { side: "opponent", edges: p };
  }
  const side = result === "won" ? "own" : "opponent";
  const edges = pick(side === "own");
  return edges.length ? { side, edges } : null;
}
